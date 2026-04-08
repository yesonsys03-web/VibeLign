import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.patch_cmd import run_patch


class PatchCmdWrapperTest(unittest.TestCase):
    def test_run_patch_json_uses_shared_builder_output(self) -> None:
        with patch(
            "vibelign.commands.patch_cmd.build_legacy_patch_suggestion",
            return_value={
                "request": "fix login",
                "target_file": "login.py",
                "target_anchor": "LOGIN_FORM",
                "confidence": "high",
                "rationale": ["picked login form"],
            },
        ) as mocked:
            with patch("vibelign.commands.patch_cmd.print") as printer:
                run_patch(Namespace(request=["fix", "login"], json=True))

        mocked.assert_called_once()
        rendered = json.loads(printer.call_args.args[0])
        self.assertEqual(rendered["target_file"], "login.py")
        self.assertEqual(rendered["target_anchor"], "LOGIN_FORM")

    def test_run_patch_text_writes_legacy_request_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(Path, "cwd", return_value=root):
                with patch(
                    "vibelign.commands.patch_cmd.build_legacy_patch_suggestion",
                    return_value={
                        "request": "fix login",
                        "target_file": "login.py",
                        "target_anchor": "LOGIN_FORM",
                        "confidence": "medium",
                        "rationale": ["picked login form"],
                    },
                ):
                    run_patch(Namespace(request=["fix", "login"], json=False))

            artifact = (root / "VIBELIGN_PATCH_REQUEST.md").read_text(encoding="utf-8")
            self.assertIn("login.py", artifact)
            self.assertIn("LOGIN_FORM", artifact)
            self.assertIn("picked login form", artifact)


if __name__ == "__main__":
    _ = unittest.main()
