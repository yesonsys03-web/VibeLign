import hashlib
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.core.checkpoint_engine.rust_engine import (
    _binary_name,
    _candidate_paths,
    apply_retention_with_rust,
    call_rust_engine_daemon,
    call_rust_engine,
    create_checkpoint_with_rust,
    diff_checkpoints_with_rust,
    find_rust_engine,
    healthcheck_rust_engine_daemon,
    inspect_backup_db_with_rust,
    list_checkpoints_with_rust,
    preview_restore_with_rust,
    prune_checkpoints_with_rust,
    restore_checkpoint_with_rust,
    restore_files_with_rust,
    restore_suggestions_with_rust,
    RustEngineResult,
    shutdown_rust_engine_daemon,
)
from vibelign.core.checkpoint_engine.rust_engine import daemon_client as daemon_client_module
from vibelign.core.checkpoint_engine.rust_engine.discovery import RustEngineAvailability
from vibelign.core.checkpoint_engine.auto_backup import (
    create_post_commit_backup,
    set_auto_backup_enabled,
)
from vibelign.core.checkpoint_engine.rust_checkpoint_engine import RustCheckpointEngine
from vibelign.core.checkpoint_engine.router import list_checkpoints
from vibelign.core import local_checkpoints
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


def _serve_one_daemon_response(root: Path, response_for_request):
    meta_dir = root / ".vibelign"
    meta_dir.mkdir(parents=True, exist_ok=True)
    sock_path = meta_dir / "engine.sock"
    ready = threading.Event()
    captured: dict[str, object] = {}

    def run_server() -> None:
        if sock_path.exists():
            sock_path.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(sock_path))
            server.listen(1)
            ready.set()
            connection, _ = server.accept()
            with connection:
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                request = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
                captured["request"] = request
                response = response_for_request(request)
                connection.sendall(json.dumps(response).encode("utf-8") + b"\n")
        if sock_path.exists():
            sock_path.unlink()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    if not ready.wait(timeout=2):
        raise RuntimeError("daemon test server did not start")
    return thread, captured


class CheckpointRustEngineTest(unittest.TestCase):
    def test_rust_engine_lists_legacy_python_checkpoints_when_db_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('legacy')\n", encoding="utf-8")
            legacy = local_checkpoints.create_checkpoint(root, "legacy checkpoint")
            self.assertIsNotNone(legacy)

            with patch(
                "vibelign.core.checkpoint_engine.rust_checkpoint_engine.list_checkpoints_with_rust",
                return_value=([], None),
            ):
                checkpoints = RustCheckpointEngine().list_checkpoints(root)

            self.assertEqual([item.checkpoint_id for item in checkpoints], [legacy.checkpoint_id])

    def test_rust_engine_restores_legacy_python_checkpoint_when_db_misses_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("print('legacy')\n", encoding="utf-8")
            legacy = local_checkpoints.create_checkpoint(root, "legacy checkpoint")
            self.assertIsNotNone(legacy)
            target.write_text("print('changed')\n", encoding="utf-8")

            with patch(
                "vibelign.core.checkpoint_engine.rust_checkpoint_engine.restore_checkpoint_with_rust",
                return_value=(False, "CHECKPOINT_RESTORE_FAILED: checkpoint database missing"),
            ):
                restored = RustCheckpointEngine().restore_checkpoint(root, legacy.checkpoint_id)

            self.assertTrue(restored)
            self.assertEqual(target.read_text(encoding="utf-8"), "print('legacy')\n")

    def test_missing_binary_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[root / "missing"],
            ):
                availability = find_rust_engine(root)

            self.assertFalse(availability.available)
            self.assertEqual(availability.reason, "rust engine binary missing")
            self.assertEqual(availability.code, "RUST_ENGINE_UNAVAILABLE")

    def test_integrity_manifest_missing_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / "vibelign-engine"
            _write_fake_engine(engine, '{"status":"ok","result":"engine_info"}')
            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[engine],
            ):
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

    def test_pyinstaller_bundled_engine_candidate_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_root = Path(tmp) / "_internal"
            engine = bundle_root / "vibelign" / "_bundled" / _binary_name()

            with patch.dict(os.environ, {}, clear=True), patch.object(
                sys, "_MEIPASS", str(bundle_root), create=True
            ):
                candidates = _candidate_paths(Path(tmp))

            self.assertIn(engine, candidates)

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

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix socket daemon transport required")
    def test_call_rust_engine_daemon_unwraps_ok_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread, captured = _serve_one_daemon_response(
                root,
                lambda request: {
                    "request_id": request["request_id"],
                    "status": "ok",
                    "result": "handled",
                    "payload": {"status": "ok", "result": "engine_info"},
                },
            )

            result = call_rust_engine_daemon(root, {"command": "engine_info"})
            thread.join(timeout=2)

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["result"], "engine_info")
            self.assertEqual(cast(dict[str, object], captured["request"])["payload"], {"command": "engine_info"})

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix socket daemon transport required")
    def test_call_rust_engine_daemon_reports_daemon_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread, _ = _serve_one_daemon_response(
                root,
                lambda request: {
                    "request_id": request["request_id"],
                    "status": "error",
                    "code": "DAEMON_ROOT_MISMATCH",
                    "message": "bad root",
                },
            )

            result = call_rust_engine_daemon(root, {"command": "checkpoint_list", "root": str(root)})
            thread.join(timeout=2)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "DAEMON_ROOT_MISMATCH")
            self.assertEqual(result.error_message, "bad root")

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix socket daemon transport required")
    def test_call_rust_engine_daemon_rejects_request_id_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread, _ = _serve_one_daemon_response(
                root,
                lambda _request: {
                    "request_id": "wrong-request",
                    "status": "ok",
                    "result": "handled",
                    "payload": {"status": "ok", "result": "engine_info"},
                },
            )

            result = call_rust_engine_daemon(root, {"command": "engine_info"})
            thread.join(timeout=2)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "RUST_ENGINE_DAEMON_REQUEST_MISMATCH")

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix socket daemon transport required")
    def test_shutdown_rust_engine_daemon_accepts_control_response_without_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread, captured = _serve_one_daemon_response(
                root,
                lambda request: {
                    "request_id": request["request_id"],
                    "status": "ok",
                    "result": "shutdown",
                    "payload": None,
                },
            )

            result = shutdown_rust_engine_daemon(root)
            thread.join(timeout=2)

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["result"], "shutdown")
            self.assertEqual(cast(dict[str, object], captured["request"])["payload"], {"command": "shutdown"})

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix socket daemon transport required")
    def test_healthcheck_reports_running_daemon(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread, _ = _serve_one_daemon_response(
                root,
                lambda request: {
                    "request_id": request["request_id"],
                    "status": "ok",
                    "result": "handled",
                    "payload": {"status": "ok", "result": "engine_info"},
                },
            )

            result = healthcheck_rust_engine_daemon(root)
            thread.join(timeout=2)

            self.assertTrue(result.ok)

    def test_is_rust_engine_daemon_running_wraps_healthcheck(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module,
            "healthcheck_rust_engine_daemon",
            return_value=RustEngineResult(
                ok=True,
                payload={"status": "ok", "result": "engine_info"},
            ),
        ):
            self.assertTrue(daemon_client_module.is_rust_engine_daemon_running(Path(tmp)))

    def test_daemon_log_rotation_keeps_three_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / ".vibelign" / "engine.log"
            log_path.parent.mkdir()
            log_path.write_bytes(b"current")
            log_path.with_name("engine.log.1").write_bytes(b"one")
            log_path.with_name("engine.log.2").write_bytes(b"two")
            log_path.with_name("engine.log.3").write_bytes(b"three")

            daemon_client_module._rotate_daemon_log(log_path, max_bytes=1, backups=3)

            self.assertFalse(log_path.exists())
            self.assertEqual(log_path.with_name("engine.log.1").read_bytes(), b"current")
            self.assertEqual(log_path.with_name("engine.log.2").read_bytes(), b"one")
            self.assertEqual(log_path.with_name("engine.log.3").read_bytes(), b"two")

    def test_call_rust_engine_daemon_missing_socket_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = call_rust_engine_daemon(Path(tmp), {"command": "engine_info"})

            self.assertFalse(result.ok)
            self.assertIn(
                result.error_code,
                {"RUST_ENGINE_DAEMON_UNAVAILABLE", "RUST_ENGINE_DAEMON_UNSUPPORTED"},
            )

    def test_daemon_client_reports_unsupported_transport_consistently(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module,
            "_daemon_transport_supported",
            return_value=False,
        ), patch.object(daemon_client_module.socket, "socket") as socket_factory, patch.object(
            daemon_client_module.subprocess, "Popen"
        ) as popen:
            root = Path(tmp)
            results = [
                call_rust_engine_daemon(root, {"command": "engine_info"}, start_if_missing=True),
                healthcheck_rust_engine_daemon(root),
                shutdown_rust_engine_daemon(root),
                daemon_client_module.start_rust_engine_daemon(root),
            ]

        self.assertTrue(all(not result.ok for result in results))
        self.assertEqual(
            {result.error_code for result in results},
            {"RUST_ENGINE_DAEMON_UNSUPPORTED"},
        )
        self.assertTrue(
            all("Windows named pipe" in (result.error_message or "") for result in results)
        )
        socket_factory.assert_not_called()
        popen.assert_not_called()

    def test_call_rust_engine_daemon_does_not_spawn_by_default(self):
        unavailable = RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_UNAVAILABLE",
            error_message="missing socket",
        )
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module, "_send_daemon_request", return_value=unavailable
        ) as send, patch.object(
            daemon_client_module, "start_rust_engine_daemon"
        ) as start:
            result = call_rust_engine_daemon(Path(tmp), {"command": "engine_info"})

        self.assertEqual(result.error_code, "RUST_ENGINE_DAEMON_UNAVAILABLE")
        self.assertEqual(send.call_count, 2)
        start.assert_not_called()

    def test_call_rust_engine_daemon_retries_dropped_connection_once(self):
        unavailable = RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_UNAVAILABLE",
            error_message="dropped connection",
        )
        ok = RustEngineResult(
            ok=True,
            payload={"status": "ok", "result": "engine_info"},
        )
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module,
            "_send_daemon_request",
            side_effect=[unavailable, ok],
        ) as send, patch.object(
            daemon_client_module, "start_rust_engine_daemon"
        ) as start:
            result = call_rust_engine_daemon(Path(tmp), {"command": "engine_info"})

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["result"], "engine_info")
        self.assertEqual(send.call_count, 2)
        start.assert_not_called()

    def test_call_rust_engine_daemon_start_if_missing_retries_once(self):
        unavailable = RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_UNAVAILABLE",
            error_message="missing socket",
        )
        started = RustEngineResult(
            ok=True,
            payload={"status": "ok", "result": "daemon_started"},
        )
        ok = RustEngineResult(
            ok=True,
            payload={"status": "ok", "result": "engine_info"},
        )
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module,
            "_send_daemon_request",
            side_effect=[unavailable, unavailable, ok],
        ) as send, patch.object(
            daemon_client_module, "start_rust_engine_daemon", return_value=started
        ) as start:
            result = call_rust_engine_daemon(
                Path(tmp), {"command": "engine_info"}, start_if_missing=True
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["result"], "engine_info")
        self.assertEqual(send.call_count, 3)
        start.assert_called_once()

    def test_start_rust_engine_daemon_reports_missing_binary(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module,
            "find_rust_engine",
            return_value=RustEngineAvailability(
                False, None, "rust engine binary missing", "RUST_ENGINE_UNAVAILABLE"
            ),
        ):
            result = daemon_client_module.start_rust_engine_daemon(Path(tmp))

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "RUST_ENGINE_UNAVAILABLE")

    def test_start_rust_engine_daemon_skips_spawn_when_healthcheck_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            daemon_client_module, "is_rust_engine_daemon_running", return_value=True
        ) as healthcheck, patch.object(
            daemon_client_module.subprocess, "Popen"
        ) as popen:
            result = daemon_client_module.start_rust_engine_daemon(Path(tmp))

        self.assertTrue(result.ok)
        healthcheck.assert_called_once()
        popen.assert_not_called()

    def test_start_rust_engine_daemon_accepts_other_process_winning_race(self):
        class ExitedProcess:
            def poll(self) -> int:
                return 1

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "engine.sock").write_text("ready\n", encoding="utf-8")
            (meta_dir / "engine.pid").write_text("12345\n", encoding="utf-8")
            binary = root / "vibelign-engine"
            with patch.object(
                daemon_client_module,
                "find_rust_engine",
                return_value=RustEngineAvailability(True, binary),
            ), patch.object(
                daemon_client_module.subprocess, "Popen", return_value=ExitedProcess()
            ):
                result = daemon_client_module.start_rust_engine_daemon(root)

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["result"], "daemon_started")

    def test_rust_wrappers_default_to_oneshot_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_DAEMON": ""}, clear=False), patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon"
            ) as daemon_call, patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=RustEngineResult(
                    ok=True,
                    payload={"status": "ok", "result": "listed", "checkpoints": []},
                ),
            ) as oneshot_call:
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertEqual(checkpoints, [])
            self.assertIsNone(warning)
            daemon_call.assert_not_called()
            oneshot_call.assert_called_once()

    def test_rust_wrappers_use_daemon_when_opted_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
                return_value=RustEngineResult(
                    ok=True,
                    payload={"status": "ok", "result": "listed", "checkpoints": []},
                ),
            ) as daemon_call, patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine"
            ) as oneshot_call:
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertEqual(checkpoints, [])
            self.assertIsNone(warning)
            daemon_call.assert_called_once()
            self.assertTrue(daemon_call.call_args.kwargs["start_if_missing"])
            oneshot_call.assert_not_called()

    def test_rust_wrappers_fallback_to_oneshot_when_daemon_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
                return_value=RustEngineResult(
                    ok=False,
                    payload={},
                    error_code="RUST_ENGINE_DAEMON_UNAVAILABLE",
                    error_message="missing socket",
                ),
            ) as daemon_call, patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=RustEngineResult(
                    ok=True,
                    payload={"status": "ok", "result": "listed", "checkpoints": []},
                ),
            ) as oneshot_call:
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertEqual(checkpoints, [])
            self.assertIsNone(warning)
            daemon_call.assert_called_once()
            oneshot_call.assert_called_once()

    def test_rust_wrappers_do_not_hide_daemon_request_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
                return_value=RustEngineResult(
                    ok=False,
                    payload={},
                    error_code="RUST_ENGINE_DAEMON_REQUEST_MISMATCH",
                    error_message="wrong request_id",
                ),
            ) as daemon_call, patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine"
            ) as oneshot_call:
                checkpoints, warning = list_checkpoints_with_rust(root)

            self.assertIsNone(checkpoints)
            self.assertIn("RUST_ENGINE_DAEMON_REQUEST_MISMATCH", warning or "")
            daemon_call.assert_called_once()
            oneshot_call.assert_not_called()

    def test_backup_db_viewer_request_shape(self):
        from vibelign.core.checkpoint_engine.requests import (
            backup_db_viewer_inspect_request,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(
                backup_db_viewer_inspect_request(root),
                {"command": "backup_db_viewer_inspect", "root": str(root)},
            )

    def test_backup_db_maintenance_request_shape(self):
        from vibelign.core.checkpoint_engine.requests import backup_db_maintenance_request

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(
                backup_db_maintenance_request(root, apply=False),
                {"command": "backup_db_maintenance", "root": str(root), "apply": False},
            )
            self.assertEqual(
                backup_db_maintenance_request(root, apply=True),
                {"command": "backup_db_maintenance", "root": str(root), "apply": True},
            )

    def test_scan_project_with_rust_calls_project_scan_transport(self):
        from vibelign.core.checkpoint_engine.rust_engine import scan_project_with_rust

        payload = {
            "status": "ok",
            "result": "project_scan",
            "files": [
                {
                    "path": "main.py",
                    "category": "entry",
                    "imports": ["services.api_client"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=RustEngineResult(ok=True, payload=payload),
            ) as engine_call:
                report, warning = scan_project_with_rust(root)

        self.assertIsNone(warning)
        self.assertEqual(report, payload)
        engine_call.assert_called_once_with(root, {"command": "project_scan", "root": str(root)}, timeout_seconds=30)

    def test_parse_backup_db_viewer_inspect_response(self):
        from vibelign.core.checkpoint_engine.responses import (
            parse_backup_db_viewer_inspect,
        )
        from vibelign.core.checkpoint_engine.rust_engine import RustEngineResult

        payload = {
            "status": "ok",
            "result": "backup_db_viewer_inspect",
            "db_exists": True,
            "checkpoint_count": 1,
            "checkpoints": [{"checkpoint_id": "cp-1", "display_name": "backup"}],
        }

        parsed, warning = parse_backup_db_viewer_inspect(
            RustEngineResult(ok=True, payload=payload)
        )

        self.assertIsNone(warning)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertTrue(parsed["db_exists"])
        self.assertEqual(parsed["checkpoint_count"], 1)
        self.assertEqual(cast(list[dict[str, object]], parsed["checkpoints"])[0]["checkpoint_id"], "cp-1")

    def test_inspect_backup_db_with_rust_calls_engine(self):
        from vibelign.core.checkpoint_engine.rust_engine import RustEngineResult

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=RustEngineResult(
                    ok=True,
                    payload={
                        "status": "ok",
                        "result": "backup_db_viewer_inspect",
                        "db_exists": False,
                        "checkpoint_count": 0,
                        "checkpoints": [],
                    },
                ),
            ) as mocked_call:
                report, warning = inspect_backup_db_with_rust(root)

            self.assertIsNone(warning)
            self.assertIsNotNone(report)
            assert report is not None
            self.assertEqual(
                mocked_call.call_args.args[1],
                {"command": "backup_db_viewer_inspect", "root": str(root)},
            )
            self.assertEqual(mocked_call.call_args.kwargs["timeout_seconds"], 90)
            self.assertFalse(report["db_exists"])

    def test_maintain_backup_db_with_rust_calls_engine(self):
        from vibelign.core.checkpoint_engine.rust_engine import (
            RustEngineResult,
            maintain_backup_db_with_rust,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "status": "ok",
                "result": "backup_db_maintenance",
                "mode": "dry_run",
                "db_exists": True,
                "planned_action": "noop",
            }
            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine",
                return_value=RustEngineResult(ok=True, payload=payload),
            ) as mocked_call:
                report, warning = maintain_backup_db_with_rust(root, apply=False)

            self.assertIsNone(warning)
            self.assertEqual(report, payload)
            self.assertEqual(
                mocked_call.call_args.args[1],
                {"command": "backup_db_maintenance", "root": str(root), "apply": False},
            )
            self.assertEqual(mocked_call.call_args.kwargs["timeout_seconds"], 90)

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
                "vibelign.core.checkpoint_engine.auto_backup.create_checkpoint",
                return_value=None,
            ) as mocked_create:
                result = create_post_commit_backup(root, "abc1234", "feat: demo\n")

            self.assertEqual(result.status, "no_changes")
            _, args, kwargs = mocked_create.mock_calls[0]
            self.assertEqual(args, (root, "vibelign: auto backup after commit abc1234"))
            self.assertEqual(kwargs["trigger"], "post_commit")
            self.assertEqual(kwargs["git_commit_sha"], "abc1234")
            self.assertEqual(kwargs["git_commit_message"], "feat: demo")

    def test_post_commit_auto_backup_respects_db_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            set_auto_backup_enabled(root, False)
            with patch(
                "vibelign.core.checkpoint_engine.auto_backup.create_checkpoint"
            ) as mocked_create:
                result = create_post_commit_backup(root, "abc1234", "feat: demo")

            self.assertEqual(result.status, "disabled")
            mocked_create.assert_not_called()

    def test_post_commit_auto_backup_falls_back_when_rust_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[],
            ):
                result = create_post_commit_backup(root, "abc1234", "feat: demo")

                self.assertEqual(result.status, "created")
                checkpoints = list_checkpoints(root)
                self.assertGreaterEqual(len(checkpoints), 1)
                self.assertEqual(checkpoints[0].trigger, "post_commit")
                self.assertEqual(checkpoints[0].git_commit_message, "feat: demo")

                state = json.loads((root / ".vibelign" / "state.json").read_text())
                self.assertEqual(state["engine_used"], "python")
                self.assertIn("RUST_ENGINE_UNAVAILABLE", state["last_fallback_reason"])

    def test_python_checkpoint_preserves_post_commit_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")

            summary = local_checkpoints.create_checkpoint(
                root,
                "vibelign: auto backup after commit abc1234",
                trigger="post_commit",
                git_commit_sha="abc1234",
                git_commit_message="feat: demo",
            )

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary.trigger, "post_commit")
            self.assertEqual(summary.git_commit_message, "feat: demo")

            manifest = json.loads(
                (
                    root
                    / ".vibelign"
                    / "checkpoints"
                    / summary.checkpoint_id
                    / "manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["trigger"], "post_commit")
            self.assertEqual(manifest["git_commit_sha"], "abc1234")
            self.assertEqual(manifest["git_commit_message"], "feat: demo")

            listed = local_checkpoints.list_checkpoints(root)
            self.assertEqual(listed[0].trigger, "post_commit")
            self.assertEqual(listed[0].git_commit_message, "feat: demo")

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

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[],
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

    def test_rust_checkpoint_engine_required_mode_rejects_python_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ,
                {"VIBELIGN_REQUIRE_RUST_CHECKPOINT": "1"},
                clear=False,
            ), patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[],
            ):
                with self.assertRaisesRegex(RuntimeError, "RUST_ENGINE_UNAVAILABLE"):
                    _ = engine.create_checkpoint(root, "must use rust")

            self.assertFalse((root / ".vibelign" / "checkpoints").exists())

    def test_rust_checkpoint_engine_disable_flag_wins_over_daemon_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print(1)\n", encoding="utf-8")
            engine = RustCheckpointEngine()

            with patch.dict(
                os.environ,
                {
                    "VIBELIGN_DISABLE_RUST_CHECKPOINT": "1",
                    "VIBELIGN_ENGINE_DAEMON": "1",
                },
                clear=False,
            ), patch(
                "vibelign.core.checkpoint_engine.rust_checkpoint_engine.create_checkpoint_with_rust"
            ) as create_with_rust:
                summary = engine.create_checkpoint(root, "python only")

            self.assertIsNotNone(summary)
            create_with_rust.assert_not_called()

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

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[engine_path],
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

            with patch(
                "vibelign.core.checkpoint_engine.rust_engine.discovery._candidate_paths",
                return_value=[engine_path],
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
