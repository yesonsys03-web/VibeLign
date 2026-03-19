import tempfile
import unittest
import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.core import local_checkpoints
from vibelign.core.local_checkpoints import (
    CheckpointSummary,
    RetentionPolicy,
    create_checkpoint,
    get_last_restore_error,
    has_changes_since_checkpoint,
    list_checkpoints,
    prune_checkpoints,
    restore_checkpoint,
)


class LocalCheckpointsTest(unittest.TestCase):
    def test_create_checkpoint_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')\n", encoding="utf-8")
            summary = create_checkpoint(root, "first checkpoint")
            self.assertIsNotNone(summary)
            checkpoints = list_checkpoints(root)
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(checkpoints[0].message, "first checkpoint")

    def test_restore_checkpoint_reverts_file_and_removes_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("print('v1')\n", encoding="utf-8")
            first_raw = create_checkpoint(root, "first checkpoint")
            self.assertIsNotNone(first_raw)
            first = cast(CheckpointSummary, first_raw)
            target.write_text("print('v2')\n", encoding="utf-8")
            extra = root / "temp.txt"
            extra.write_text("temp\n", encoding="utf-8")
            second_raw = create_checkpoint(root, "second checkpoint")
            self.assertIsNotNone(second_raw)
            self.assertTrue(restore_checkpoint(root, first.checkpoint_id))
            self.assertEqual(target.read_text(encoding="utf-8"), "print('v1')\n")
            self.assertFalse(extra.exists())

    def test_create_checkpoint_skips_when_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')\n", encoding="utf-8")
            self.assertIsNotNone(create_checkpoint(root, "first checkpoint"))
            self.assertIsNone(create_checkpoint(root, "unchanged checkpoint"))

    def test_has_changes_since_checkpoint_detects_workspace_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("print('v1')\n", encoding="utf-8")
            first_raw = create_checkpoint(root, "first checkpoint")
            self.assertIsNotNone(first_raw)
            first = cast(CheckpointSummary, first_raw)
            self.assertFalse(has_changes_since_checkpoint(root, first.checkpoint_id))
            target.write_text("print('v2')\n", encoding="utf-8")
            self.assertTrue(has_changes_since_checkpoint(root, first.checkpoint_id))

    def test_prune_checkpoints_keeps_latest_and_removes_old_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            for index in range(4):
                target.write_text(f"print('v{index}')\n", encoding="utf-8")
                self.assertIsNotNone(create_checkpoint(root, f"cp {index}"))
            policy = RetentionPolicy(
                keep_latest=2,
                keep_daily_days=0,
                keep_weekly_weeks=0,
                max_total_size_bytes=10**9,
                max_age_days=999,
                min_keep=1,
            )
            result = prune_checkpoints(root, policy=policy)
            self.assertGreaterEqual(result["count"], 2)
            self.assertLessEqual(len(list_checkpoints(root)), 2)

    def test_prune_checkpoints_removes_old_checkpoint_even_under_count_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoints_dir = root / ".vibelign" / "checkpoints"
            old_dir = checkpoints_dir / "20000101T000000000000Z"
            files_dir = old_dir / "files"
            files_dir.mkdir(parents=True)
            (files_dir / "app.py").write_text("print('old')\n", encoding="utf-8")
            (old_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "20000101T000000000000Z",
                        "created_at": "20000101T000000000000Z",
                        "message": "old checkpoint",
                        "pinned": False,
                        "file_count": 1,
                        "total_size_bytes": 12,
                        "files": [{"path": "app.py", "sha256": "x", "size": 12}],
                    }
                ),
                encoding="utf-8",
            )
            result = prune_checkpoints(
                root,
                policy=RetentionPolicy(
                    keep_latest=30,
                    keep_daily_days=0,
                    keep_weekly_weeks=0,
                    max_total_size_bytes=10**9,
                    max_age_days=1,
                    min_keep=0,
                ),
            )
            self.assertEqual(result["count"], 1)
            self.assertFalse(old_dir.exists())

    def test_create_checkpoint_skips_file_missing_during_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stable = root / "app.py"
            transient = root / "VK8MCISF.DOCX"
            stable.write_text("print('v1')\n", encoding="utf-8")
            transient.write_text("temp\n", encoding="utf-8")

            original_sha256 = local_checkpoints._sha256

            def flaky_sha256(path: Path) -> str:
                if path.name == "VK8MCISF.DOCX":
                    raise FileNotFoundError(path)
                return original_sha256(path)

            with patch(
                "vibelign.core.local_checkpoints._sha256", side_effect=flaky_sha256
            ):
                summary = create_checkpoint(root, "hash race")

            self.assertIsNotNone(summary)
            checkpoints = list_checkpoints(root)
            self.assertEqual(len(checkpoints), 1)
            manifest_path = (
                root
                / ".vibelign"
                / "checkpoints"
                / checkpoints[0].checkpoint_id
                / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual([item["path"] for item in manifest["files"]], ["app.py"])

    def test_create_checkpoint_skips_file_missing_during_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stable = root / "app.py"
            transient = root / "VK8MCISF.DOCX"
            stable.write_text("print('v1')\n", encoding="utf-8")
            transient.write_text("temp\n", encoding="utf-8")

            original_copy2 = local_checkpoints.shutil.copy2

            def flaky_copy2(src: Path, dst: Path) -> None:
                if src.name == "VK8MCISF.DOCX":
                    raise FileNotFoundError(src)
                original_copy2(src, dst)

            with patch(
                "vibelign.core.local_checkpoints.shutil.copy2", side_effect=flaky_copy2
            ):
                summary = create_checkpoint(root, "copy race")

            self.assertIsNotNone(summary)
            checkpoints = list_checkpoints(root)
            self.assertEqual(len(checkpoints), 1)
            manifest_path = (
                root
                / ".vibelign"
                / "checkpoints"
                / checkpoints[0].checkpoint_id
                / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual([item["path"] for item in manifest["files"]], ["app.py"])

    def test_restore_checkpoint_rejects_invalid_checkpoint_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(restore_checkpoint(root, "../../evil"))
            self.assertEqual(
                get_last_restore_error(),
                "체크포인트 이름이 이상해요. 다시 골라주세요.",
            )

    def test_restore_checkpoint_rejects_manifest_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint_id = "20260319T000000000000Z"
            snapshot_dir = root / ".vibelign" / "checkpoints" / checkpoint_id
            files_dir = snapshot_dir / "files"
            files_dir.mkdir(parents=True)
            (snapshot_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": checkpoint_id,
                        "created_at": checkpoint_id,
                        "message": "bad checkpoint",
                        "pinned": False,
                        "file_count": 1,
                        "total_size_bytes": 1,
                        "files": [
                            {
                                "path": "../../outside.txt",
                                "sha256": "x",
                                "size": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse(restore_checkpoint(root, checkpoint_id))
            self.assertEqual(
                get_last_restore_error(),
                "체크포인트 안에 위험한 파일 경로가 있어요.",
            )

    def test_create_checkpoint_rejects_invalid_generated_checkpoint_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')\n", encoding="utf-8")

            with patch(
                "vibelign.core.local_checkpoints._extract_tag",
                return_value="../../evil",
            ):
                summary = create_checkpoint(root, "bad tag")

            self.assertIsNone(summary)
            self.assertEqual(list_checkpoints(root), [])

    def test_create_checkpoint_rejects_unsafe_snapshot_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')\n", encoding="utf-8")

            with patch(
                "vibelign.core.local_checkpoints._current_file_map",
                return_value={
                    "../../outside.txt": {
                        "path": "../../outside.txt",
                        "sha256": "x",
                        "size": 1,
                    }
                },
            ):
                summary = create_checkpoint(root, "bad file path")

            self.assertIsNone(summary)
            checkpoints_dir = root / ".vibelign" / "checkpoints"
            if checkpoints_dir.exists():
                self.assertEqual(list(checkpoints_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
