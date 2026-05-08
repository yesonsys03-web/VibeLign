import json
import multiprocessing
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from vibelign.core import error_log
from vibelign.core.error_log import record_cli_error, record_gui_error, resolve_vib_version


def _write_gui_errors_for_process(root_text: str, start: int, count: int) -> None:
    root = Path(root_text)
    for index in range(start, start + count):
        record_gui_error(root, {"source": "window.onerror", "message": f"process-message-{index}"})


class ErrorLogTest(unittest.TestCase):
    def test_record_cli_error_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            try:
                raise ValueError("API 키가 없습니다")
            except ValueError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib", "doctor"])

            files = list((root / ".vibelign" / "logs").glob("cli-error-*.jsonl"))
            self.assertEqual(1, len(files))
            raw = files[0].read_text(encoding="utf-8")
            record = json.loads(raw)
            self.assertEqual("ValueError", record["error_class"])
            self.assertIn("API 키가 없습니다", raw)

    def test_redacts_token_prefix_before_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            try:
                raise RuntimeError("token sk-ant-abc123456789 leaked")
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib"])

            raw = next((root / ".vibelign" / "logs").glob("cli-error-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn("sk-ant-abc123456789", raw)
            self.assertIn("[secret-token]", raw)

    def test_redacts_windows_broad_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            try:
                raise RuntimeError(r"failed at D:\dev\client\secret.py")
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib"])

            raw = next((root / ".vibelign" / "logs").glob("cli-error-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn(r"D:\dev\client\secret.py", raw)
            self.assertIn("[local-path]", raw)

    def test_redacts_private_ip_and_internal_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            try:
                raise RuntimeError("backend api.internal failed at 192.168.0.12")
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib"])

            raw = next((root / ".vibelign" / "logs").glob("cli-error-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn("api.internal", raw)
            self.assertNotIn("192.168.0.12", raw)
            self.assertIn("[internal-host]", raw)
            self.assertIn("[private-ip]", raw)

    def test_config_local_log_false_disables_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg = root / ".vibelign"
            vg.mkdir()
            (vg / "config.yaml").write_text("error_reporting:\n  local_log: false\n", encoding="utf-8")
            try:
                raise RuntimeError("off")
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib"])
            self.assertFalse((vg / "logs").exists())

    def test_traceback_lines_are_preserved_as_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()

            def fail_inside() -> None:
                raise RuntimeError("nested failure")

            try:
                fail_inside()
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib", "doctor"])

            raw = next((root / ".vibelign" / "logs").glob("cli-error-*.jsonl")).read_text(encoding="utf-8")
            record = json.loads(raw)
            self.assertIsInstance(record["traceback_redacted"], list)
            self.assertGreaterEqual(len(record["traceback_redacted"]), 3)
            self.assertTrue(any("fail_inside" in line for line in record["traceback_redacted"]))

    def test_long_line_truncates_to_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            try:
                raise RuntimeError("x" * 20_000)
            except RuntimeError as exc:
                record_cli_error(root, (type(exc), exc, exc.__traceback__), ["vib"])

            raw = next((root / ".vibelign" / "logs").glob("cli-error-*.jsonl")).read_bytes()
            self.assertLessEqual(len(raw), error_log.LOG_LINE_LIMIT)
            self.assertIsInstance(json.loads(raw.decode("utf-8")), dict)

    def test_non_string_heavy_record_truncates_to_valid_jsonl(self) -> None:
        record = {
            "ts": "2026-05-06T00:00:00.000Z",
            "source": "window.onerror",
            "message_redacted": "boom",
            "numbers": list(range(20_000)),
            "redaction": {"secret_hits": 0, "privacy_hits": 0, "summarized_fields": 0},
        }

        raw = error_log._json_line(record).encode("utf-8")

        self.assertLessEqual(len(raw), error_log.LOG_LINE_LIMIT)
        parsed = json.loads(raw.decode("utf-8"))
        self.assertTrue(parsed["truncated"])
        self.assertNotIn("numbers", parsed)

    def test_utc_rotation_suffix_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            with patch.object(error_log, "MAX_LINES_PER_FILE", 1):
                record_gui_error(root, {"source": "window.onerror", "message": "first"})
                record_gui_error(root, {"source": "window.onerror", "message": "second"})

            names = sorted(path.name for path in (root / ".vibelign" / "logs").glob("gui-error-*.jsonl"))
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            self.assertEqual(names, [f"gui-error-{today}-2.jsonl", f"gui-error-{today}.jsonl"])

    def test_30day_retention_sweep_deletes_old_suffix_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / ".vibelign" / "logs"
            logs.mkdir(parents=True)
            old_date = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y%m%d")
            old = logs / f"cli-error-{old_date}-2.jsonl"
            old.write_text("{}\n", encoding="utf-8")

            record_gui_error(root, {"source": "window.onerror", "message": "new"})

            self.assertFalse(old.exists())

    def test_jsonl_uses_lf_without_crlf_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            record_gui_error(root, {"source": "window.onerror", "message": "API 키가 없습니다"})

            raw = next((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")).read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertIn("API 키가 없습니다".encode("utf-8"), raw)

    def test_writer_failure_is_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            with patch("vibelign.core.error_log._append_jsonl", side_effect=OSError("disk full")):
                record_gui_error(root, {"source": "window.onerror", "message": "boom"})

            self.assertFalse(list((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")))

    def test_threaded_writers_produce_parseable_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            import threading

            threads = [
                threading.Thread(
                    target=record_gui_error,
                    args=(root, {"source": "window.onerror", "message": f"message-{idx}"}),
                )
                for idx in range(12)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            raw_lines = next((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")).read_text(encoding="utf-8").splitlines()
            self.assertEqual(12, len(raw_lines))
            self.assertTrue(all(json.loads(line)["source"] == "window.onerror" for line in raw_lines))

    def test_process_writers_produce_parseable_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            processes = [
                multiprocessing.Process(
                    target=_write_gui_errors_for_process,
                    args=(str(root), index * 10, 10),
                )
                for index in range(4)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)

            raw_lines = next((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")).read_text(encoding="utf-8").splitlines()
            self.assertEqual(40, len(raw_lines))
            messages = {json.loads(line)["message_redacted"] for line in raw_lines}
            self.assertIn("process-message-0", messages)
            self.assertIn("process-message-39", messages)

    def test_record_gui_error_writes_redacted_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            record_gui_error(root, {"source": "window.onerror", "message": "ghp_abcdef123456", "url": "file:///C:/Projects/app/main.js"})

            raw = next((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn("ghp_abcdef123456", raw)
            self.assertNotIn("C:/Projects/app/main.js", raw)
            self.assertEqual("window.onerror", json.loads(raw)["source"])

    def test_vib_version_fallback_chain(self) -> None:
        self.assertTrue(resolve_vib_version())


if __name__ == "__main__":
    unittest.main()
