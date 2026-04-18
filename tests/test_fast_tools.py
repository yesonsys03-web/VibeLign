import subprocess
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.core import fast_tools


class FastToolsTest(unittest.TestCase):
    def test_find_source_files_fd_uses_utf8_and_handles_stdout(self):
        completed = subprocess.CompletedProcess(
            args=["fd"],
            returncode=0,
            stdout="src/ko-파일.py\nsrc/app.ts\n",
            stderr="",
        )

        with patch.object(fast_tools, "_FD", "fd"):
            with patch(
                "vibelign.core.fast_tools.subprocess.run", return_value=completed
            ) as run:
                result = fast_tools.find_source_files_fd(Path("/tmp/project"))

        self.assertEqual(result, [Path("src/ko-파일.py"), Path("src/app.ts")])
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")
        self.assertTrue(run.call_args.kwargs["text"])

        cmd = cast(list[str], run.call_args.args[0])
        for excluded in ("target", "env", ".mypy_cache", ".sisyphus"):
            self.assertIn("--exclude", cmd)
            self.assertIn(excluded, cmd)
        self.assertIn("-e", cmd)
        self.assertIn("py", cmd)
        self.assertIn("tsx", cmd)

    def test_find_source_files_fd_returns_empty_on_decode_error(self):
        with patch.object(fast_tools, "_FD", "fd"):
            with patch(
                "vibelign.core.fast_tools.subprocess.run",
                side_effect=UnicodeDecodeError("cp949", b"\xec", 0, 1, "bad decode"),
            ):
                result = fast_tools.find_source_files_fd(Path("/tmp/project"))

        self.assertEqual(result, [])

    def test_grep_anchors_rg_handles_missing_stdout(self):
        completed = subprocess.CompletedProcess(
            args=["rg"],
            returncode=0,
            stdout=None,
            stderr="",
        )

        with patch.object(fast_tools, "_RG", "rg"):
            with patch(
                "vibelign.core.fast_tools.subprocess.run", return_value=completed
            ):
                result = fast_tools.grep_anchors_rg(Path("/tmp/project"))

        self.assertEqual(result, {})

    def test_grep_anchors_rg_uses_shared_scan_globs(self):
        completed = subprocess.CompletedProcess(
            args=["rg"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(fast_tools, "_RG", "rg"):
            with patch(
                "vibelign.core.fast_tools.subprocess.run", return_value=completed
            ) as run:
                _ = fast_tools.grep_anchors_rg(Path("/tmp/project"))

        cmd = cast(list[str], run.call_args.args[0])
        for ignored in (".vibelign", "target", "build", "dist", "node_modules"):
            self.assertIn("--glob", cmd)
            self.assertIn(f"!{ignored}/**", cmd)


if __name__ == "__main__":
    _ = unittest.main()
