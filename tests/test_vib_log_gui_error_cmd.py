import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_log_gui_error_cmd import run_vib_log_gui_error


class VibLogGuiErrorCommandTest(unittest.TestCase):
    def test_stdin_batch_writes_gui_jsonl_with_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            payload = [
                {
                    "source": "window.onerror",
                    "message": "token ghp_abcdef123456 leaked",
                    "stack": r"at D:\dev\client\app.tsx",
                    "url": "file:///C:/Projects/app/index.html",
                }
            ]

            with patch("sys.stdin", io.StringIO(json.dumps(payload))):
                run_vib_log_gui_error(Namespace(batch=True, root=str(root)))

            raw = next((root / ".vibelign" / "logs").glob("gui-error-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn("ghp_abcdef123456", raw)
            self.assertNotIn(r"D:\dev\client\app.tsx", raw)
            self.assertNotIn("C:/Projects/app/index.html", raw)
            self.assertEqual("window.onerror", json.loads(raw)["source"])


if __name__ == "__main__":
    unittest.main()
