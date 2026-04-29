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
    call_rust_engine,
    create_checkpoint_with_rust,
    find_rust_engine,
    list_checkpoints_with_rust,
    prune_checkpoints_with_rust,
    restore_checkpoint_with_rust,
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

    def test_list_checkpoints_with_rust_returns_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(
                engine,
                '{"status":"ok","result":"listed","checkpoints":[{"checkpoint_id":"cp1",'
                + '"created_at":"2026-04-29T00:00:00Z","message":"hello",'
                + '"file_count":1,"total_size_bytes":9,"pinned":false}]}',
            )
            _write_hash(engine)

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertIsNone(warning)
            self.assertIsNotNone(checkpoints)
            assert checkpoints is not None
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(checkpoints[0].checkpoint_id, "cp1")

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

    def test_rust_checkpoint_engine_does_not_fallback_on_integrity_failure(self):
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
                with self.assertRaises(RuntimeError):
                    _ = engine.create_checkpoint(root, "integrity")

            self.assertFalse((root / ".vibelign" / "checkpoints").exists())

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

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
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

            with patch.dict(os.environ, {"VIBELIGN_ENGINE_PATH": str(engine)}, clear=False):
                result = compare_checkpoint_create(root, "shadow qa")

            self.assertTrue(result.enabled)
            self.assertFalse(result.matched)
            self.assertTrue(result.mismatches)


if __name__ == "__main__":
    _ = unittest.main()
