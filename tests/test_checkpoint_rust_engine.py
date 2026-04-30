import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.core.checkpoint_engine.rust_engine import (
    apply_retention_with_rust,
    call_rust_engine,
    create_checkpoint_with_rust,
    diff_checkpoints_with_rust,
    find_rust_engine,
    list_checkpoints_with_rust,
    preview_restore_with_rust,
    prune_checkpoints_with_rust,
    restore_checkpoint_with_rust,
    restore_files_with_rust,
    restore_suggestions_with_rust,
)
from vibelign.core.checkpoint_engine.auto_backup import (
    create_post_commit_backup,
    set_auto_backup_enabled,
)
from vibelign.core.checkpoint_engine.rust_checkpoint_engine import RustCheckpointEngine
from vibelign.core.checkpoint_engine.shadow_runner import (
    compare_checkpoint_create,
    prepare_shadow_run,
)


def _write_fake_engine(path: Path, stdout: str) -> None:
    _ = path.write_text(f"#!/bin/sh\nprintf '%s' '{stdout}'\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_hash(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    _ = path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )


class CheckpointRustEngineTest(unittest.TestCase):
    def test_missing_binary_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(root / "missing")}, clear=False):
                availability = find_rust_engine(root)

            self.assertFalse(availability.available)
            self.assertEqual(availability.reason, "rust engine binary missing")
            self.assertEqual(availability.code, "RUST_ENGINE_UNAVAILABLE")

    def test_integrity_manifest_missing_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(engine, '{"status":"ok","result":"engine_info"}')
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                availability = find_rust_engine(root)

            self.assertFalse(availability.available)
            self.assertEqual(availability.reason, "integrity manifest missing")
            self.assertEqual(availability.code, "RUST_ENGINE_INTEGRITY_FAILED")

    def test_integrity_failure_skips_to_next_valid_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            broken_engine = root / "broken-engine"
            valid_engine = root / "vibelign-core" / "target" / "debug" / "vibelign-engine"
            valid_engine.parent.mkdir(parents=True)
            _write_fake_engine(broken_engine, '{"status":"ok","result":"engine_info"}')
            _ = broken_engine.with_suffix(broken_engine.suffix + ".sha256").write_text(
                "0  broken-engine\n", encoding="utf-8"
            )
            _write_fake_engine(valid_engine, '{"status":"ok","result":"engine_info"}')
            _write_hash(valid_engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(broken_engine)}, clear=False):
                availability = find_rust_engine(root)

            self.assertTrue(availability.available)
            self.assertEqual(availability.binary_path, valid_engine)

    def test_call_rust_engine_parses_ok_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(engine, '{"status":"ok","result":"engine_info"}')
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result = call_rust_engine(root, {"command": "engine_info"})

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["result"], "engine_info")

    def test_create_checkpoint_with_rust_returns_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"created","checkpoint_id":"cp1",'
                + '"created_at":"2026-04-29T00:00:00Z","message":"hello",'
                + '"file_count":1,"total_size_bytes":9}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                summary, warning = create_checkpoint_with_rust(root, "hello")

            self.assertIsNone(warning)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary.checkpoint_id, "cp1")
            self.assertEqual(summary.file_count, 1)

    def test_create_checkpoint_with_rust_passes_optional_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=type(
                    "Result",
                    (),
                    {
                        "ok": True,
                        "payload": {
                            "status": "ok",
                            "result": "no_changes",
                        },
                    },
                )(),
            ) as mocked_call:
                summary, warning = create_checkpoint_with_rust(
                    root,
                    "hello",
                    trigger="post_commit",
                    git_commit_sha="abc1234",
                    git_commit_message="feat: demo",
                )

            self.assertIsNone(summary)
            self.assertIsNone(warning)
            request = mocked_call.call_args.args[1]
            self.assertEqual(request["trigger"], "post_commit")
            self.assertEqual(request["git_commit_sha"], "abc1234")
            self.assertEqual(request["git_commit_message"], "feat: demo")

    def test_create_checkpoint_with_rust_uses_backup_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=type(
                    "Result",
                    (),
                    {"ok": True, "payload": {"status": "ok", "result": "no_changes"}},
                )(),
            ) as mocked_call:
                _ = create_checkpoint_with_rust(root, "hello")

            self.assertEqual(mocked_call.call_args.kwargs["timeout_seconds"], 90)

    def test_post_commit_auto_backup_passes_commit_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.auto_backup.create_checkpoint_with_rust",
                return_value=(None, None),
            ) as mocked_create:
                result = create_post_commit_backup(root, "abc1234", "feat: demo\n")

            self.assertEqual(result.status, "no_changes")
            _, _, kwargs = mocked_create.mock_calls[0]
            self.assertEqual(kwargs["trigger"], "post_commit")
            self.assertEqual(kwargs["git_commit_sha"], "abc1234")
            self.assertEqual(kwargs["git_commit_message"], "feat: demo")

    def test_post_commit_auto_backup_respects_db_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            set_auto_backup_enabled(root, False)
            with patch(
                "vibelign.core.checkpoint_engine.auto_backup.create_checkpoint_with_rust"
            ) as mocked_create:
                result = create_post_commit_backup(root, "abc1234", "feat: demo")

            self.assertEqual(result.status, "disabled")
            mocked_create.assert_not_called()

    def test_list_checkpoints_with_rust_returns_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"listed","checkpoints":[{"checkpoint_id":"cp1",'
                + '"created_at":"2026-04-29T00:00:00Z","message":"hello",'
                + '"file_count":1,"total_size_bytes":9,"pinned":false,"trigger":"post_commit",'
                + '"git_commit_message":"feat: demo","files":[{"relative_path":"app.py","size":9}]}]}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertIsNone(warning)
            self.assertIsNotNone(checkpoints)
            assert checkpoints is not None
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(checkpoints[0].checkpoint_id, "cp1")
            self.assertEqual(checkpoints[0].trigger, "post_commit")
            self.assertEqual(checkpoints[0].git_commit_message, "feat: demo")
            self.assertEqual(checkpoints[0].files[0].path, "app.py")
            self.assertEqual(checkpoints[0].files[0].size_bytes, 9)

    def test_restore_checkpoint_with_rust_returns_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"restored","checkpoint_id":"cp1"}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                ok, warning = restore_checkpoint_with_rust(root, "cp1")

            self.assertTrue(ok)
            self.assertIsNone(warning)

    def test_prune_checkpoints_with_rust_returns_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"pruned","pruned_count":2,"pruned_bytes":42}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result, warning = prune_checkpoints_with_rust(root, keep_latest=1)

            self.assertIsNone(warning)
            self.assertEqual(result, {"count": 2, "bytes": 42})

    def test_apply_retention_with_rust_returns_cleanup_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"retention_applied","pruned_count":1,'
                + '"planned_count":1,"planned_bytes":99,"reclaimed_bytes":42,'
                + '"partial_failure":false}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result, warning = apply_retention_with_rust(root)

            self.assertIsNone(warning)
            self.assertEqual(
                result,
                {
                    "count": 1,
                    "planned_count": 1,
                    "planned_bytes": 99,
                    "reclaimed_bytes": 42,
                    "partial_failure": False,
                },
            )

    def test_diff_checkpoints_with_rust_returns_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"diffed","diff":{"added":[],"modified":[],"deleted":[],"summary":{"added_count":0}}}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result, warning = diff_checkpoints_with_rust(root, "from", "to")

            self.assertIsNone(warning)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIn("summary", result)

    def test_preview_restore_with_rust_passes_selected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=type(
                    "Result",
                    (),
                    {
                        "ok": True,
                        "payload": {
                            "status": "ok",
                            "result": "previewed",
                            "preview": {"checkpoint_id": "cp1", "selected_files": []},
                        },
                    },
                )(),
            ) as mocked_call:
                result, warning = preview_restore_with_rust(root, "cp1", ["app.py"])

            self.assertIsNone(warning)
            self.assertEqual(result, {"checkpoint_id": "cp1", "selected_files": []})
            request = mocked_call.call_args.args[1]
            self.assertEqual(request["command"], "checkpoint_restore_files_preview")
            self.assertEqual(request["relative_paths"], ["app.py"])

    def test_restore_files_with_rust_returns_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"restored_files","restored_count":2}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                count, warning = restore_files_with_rust(root, "cp1", ["a.txt", "b.txt"])

            self.assertIsNone(warning)
            self.assertEqual(count, 2)

    def test_restore_suggestions_with_rust_returns_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"suggested","suggestions":[{"relative_path":"app.py","reason_code":"missing_now"}],"legacy_notice":null}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result, warning = restore_suggestions_with_rust(root, "cp1")

            self.assertIsNone(warning)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(
                result["suggestions"],
                [{"relative_path": "app.py", "reason_code": "missing_now"}],
            )

    def test_create_checkpoint_with_rust_distinguishes_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(engine, '{"status":"ok","result":"no_changes"}')
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                summary, warning = create_checkpoint_with_rust(root, "hello")

            self.assertIsNone(summary)
            self.assertIsNone(warning)

    def test_create_checkpoint_with_rust_rejects_malformed_created_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(engine, '{"status":"ok","result":"created"}')
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                summary, warning = create_checkpoint_with_rust(root, "hello")

            self.assertIsNone(summary)
            self.assertEqual(
                warning, "RUST_ENGINE_PROTOCOL_ERROR: created response missing checkpoint_id"
            )

    def test_rust_checkpoint_engine_falls_back_and_records_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(root / "missing")}, clear=False
            ):
                summary = engine.create_checkpoint(root, "fallback")

            self.assertIsNotNone(summary)
            state = cast(
                dict[str, object],
                json.loads(
                    (root / ".vibelign" / "state.json").read_text(encoding="utf-8")
                ),
            )
            self.assertEqual(state["engine_used"], "python")
            self.assertEqual(
                state["last_fallback_reason"],
                "RUST_ENGINE_UNAVAILABLE: rust engine binary missing",
            )

    def test_rust_checkpoint_engine_falls_back_on_integrity_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine_path = root / "vibelign-engine"
            _write_fake_engine(engine_path, '{"status":"ok","result":"engine_info"}')
            _ = engine_path.with_suffix(engine_path.suffix + ".sha256").write_text(
                "0  vibelign-engine\n", encoding="utf-8"
            )
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(engine_path)}, clear=False
            ):
                summary = engine.create_checkpoint(root, "integrity")

            self.assertIsNotNone(summary)
            state = cast(
                dict[str, object],
                json.loads(
                    (root / ".vibelign" / "state.json").read_text(encoding="utf-8")
                ),
            )
            self.assertEqual(state["engine_used"], "python")
            self.assertEqual(
                state["last_fallback_reason"],
                "RUST_ENGINE_INTEGRITY_FAILED: integrity check failed",
            )

    def test_rust_checkpoint_list_falls_back_on_integrity_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine_path = root / "vibelign-engine"
            _write_fake_engine(engine_path, '{"status":"ok","result":"engine_info"}')
            _ = engine_path.with_suffix(engine_path.suffix + ".sha256").write_text(
                "0  vibelign-engine\n", encoding="utf-8"
            )
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(engine_path)}, clear=False
            ):
                checkpoints = engine.list_checkpoints(root)

            self.assertEqual(checkpoints, [])
            state = cast(
                dict[str, object],
                json.loads(
                    (root / ".vibelign" / "state.json").read_text(encoding="utf-8")
                ),
            )
            self.assertEqual(state["engine_used"], "python")
            self.assertEqual(
                state["last_fallback_reason"],
                "RUST_ENGINE_INTEGRITY_FAILED: integrity check failed",
            )

    def test_rust_checkpoint_engine_records_no_changes_as_rust(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine_path = root / "vibelign-engine"
            _write_fake_engine(engine_path, '{"status":"ok","result":"no_changes"}')
            _write_hash(engine_path)
            state_dir = root / ".vibelign"
            state_dir.mkdir()
            _ = (state_dir / "state.json").write_text(
                '{"engine_used":"python","last_fallback_reason":"old"}\n',
                encoding="utf-8",
            )
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(engine_path)}, clear=False
            ):
                summary = engine.create_checkpoint(root, "unchanged")

            self.assertIsNone(summary)
            state = cast(
                dict[str, object],
                json.loads((state_dir / "state.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(state["engine_used"], "rust")
            self.assertNotIn("last_fallback_reason", state)

    def test_rust_checkpoint_engine_uses_rust_summary_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine_path = root / "vibelign-engine"
            _write_fake_engine(
                engine_path,
                '{"status":"ok","result":"created","checkpoint_id":"cp1",'
                + '"created_at":"2026-04-29T00:00:00Z","message":"hello",'
                + '"file_count":1,"total_size_bytes":9}',
            )
            _write_hash(engine_path)
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(engine_path)}, clear=False
            ):
                summary = engine.create_checkpoint(root, "hello")

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary.checkpoint_id, "cp1")
            state = cast(
                dict[str, object],
                json.loads(
                    (root / ".vibelign" / "state.json").read_text(encoding="utf-8")
                ),
            )
            self.assertEqual(state["engine_used"], "rust")

    def test_rust_checkpoint_engine_warns_when_state_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = RustCheckpointEngine()
            stderr: list[str] = []

            def _capture_write(text: str) -> int:
                stderr.append(text)
                return len(text)

            original_write_text = Path.write_text

            def _write_text_maybe_fail(path: Path, *args, **kwargs):
                if path.name == "state.json":
                    raise OSError("state read-only")
                return original_write_text(path, *args, **kwargs)

            with patch.dict(
                os.environ, {"VIBELIGN_ENGINE_PATH": str(root / "missing")}, clear=False
            ), patch(
                "pathlib.Path.write_text", autospec=True, side_effect=_write_text_maybe_fail
            ), patch(
                "sys.stderr.write", side_effect=_capture_write
            ):
                summary = engine.create_checkpoint(root, "fallback")

            self.assertIsNotNone(summary)
            self.assertTrue(
                any("checkpoint engine state write failed" in item for item in stderr),
                f"state write warning expected; got: {stderr}",
            )

    def test_shadow_runner_uses_unavailable_result_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(root / "missing")}, clear=False):
                result = prepare_shadow_run(root, "engine_info")

            self.assertFalse(result.enabled)
            self.assertFalse((root / ".vibelign").exists())

    def test_compare_checkpoint_create_matches_rust_file_keys(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as bin_tmp:
            root = Path(tmp)
            bin_dir = Path(bin_tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = bin_dir / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"created","file_count":1,'
                + '"total_size_bytes":9,"files":[{"relative_path":"app.py","size":9}]}',
            )
            _write_hash(engine)

            with patch.dict(
                os.environ,
                {"VIBELIGN_ENGINE_PATH": str(engine), "VIBELIGN_SHADOW_COMPARE": "1"},
                clear=False,
            ):
                result = compare_checkpoint_create(root, "shadow qa")

            self.assertTrue(result.enabled)
            self.assertTrue(result.matched)
            self.assertEqual(result.mismatches, [])
            self.assertFalse((root / ".vibelign").exists())

    def test_compare_checkpoint_create_reports_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as bin_tmp:
            root = Path(tmp)
            bin_dir = Path(bin_tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = bin_dir / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"created","file_count":1,'
                + '"total_size_bytes":10,"files":[{"relative_path":"app.py","size":10}]}',
            )
            _write_hash(engine)

            with patch.dict(
                os.environ,
                {"VIBELIGN_ENGINE_PATH": str(engine), "VIBELIGN_SHADOW_COMPARE": "1"},
                clear=False,
            ):
                result = compare_checkpoint_create(root, "shadow qa")

            self.assertTrue(result.enabled)
            self.assertFalse(result.matched)
            self.assertTrue(result.mismatches)


if __name__ == "__main__":
    _ = unittest.main()
