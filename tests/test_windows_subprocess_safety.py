import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable, cast
from unittest.mock import patch

from vibelign.commands import init_cmd
from vibelign.core import change_explainer


class InitCommandSubprocessSafetyTest(unittest.TestCase):
    def test_run_text_subprocess_uses_utf8_replace(self):
        completed = subprocess.CompletedProcess(
            args=["cmd"], returncode=0, stdout="ok", stderr=""
        )
        run_text_subprocess = cast(
            Callable[..., subprocess.CompletedProcess[str]],
            getattr(init_cmd, "_run_text_subprocess"),
        )

        with patch(
            "vibelign.commands.init_cmd.subprocess.run", return_value=completed
        ) as run:
            result = run_text_subprocess(["demo", "arg"], timeout=15)

        self.assertIs(result, completed)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")
        self.assertTrue(run.call_args.kwargs["text"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)

    def test_check_pip_uses_safe_text_runner(self):
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="", stderr=""
        )
        check_pip = cast(Callable[[], bool], getattr(init_cmd, "_check_pip"))

        with patch("vibelign.commands.init_cmd.shutil.which", side_effect=[None, None]):
            with patch(
                "vibelign.commands.init_cmd._run_text_subprocess",
                return_value=completed,
            ) as run:
                self.assertTrue(check_pip())

        self.assertEqual(
            run.call_args.args[0],
            [sys.executable, "-m", "ensurepip", "--upgrade"],
        )

    def test_reinstall_uses_safe_text_runner(self):
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="installed", stderr=""
        )
        reinstall = cast(Callable[..., bool], getattr(init_cmd, "_reinstall"))

        with patch("vibelign.commands.init_cmd._find_source_root", return_value=None):
            with patch(
                "vibelign.commands.init_cmd._run_text_subprocess",
                return_value=completed,
            ) as run:
                self.assertTrue(reinstall(use_uv=False, force=False))

        self.assertEqual(run.call_args.kwargs["timeout"], 120)

    def test_check_uv_uses_windows_powershell_with_safe_runner(self):
        completed = subprocess.CompletedProcess(
            args=["powershell"], returncode=0, stdout="installed", stderr=""
        )
        check_uv = cast(Callable[[], bool], getattr(init_cmd, "_check_uv"))
        uv_install_cmd = cast(dict[str, str], getattr(init_cmd, "_UV_INSTALL_CMD"))[
            "Windows"
        ]

        with patch("vibelign.commands.init_cmd.shutil.which", side_effect=[None, True]):
            with patch("builtins.input", return_value="y"):
                with patch(
                    "vibelign.commands.init_cmd.platform.system", return_value="Windows"
                ):
                    with patch(
                        "vibelign.commands.init_cmd._run_text_subprocess",
                        return_value=completed,
                    ) as run:
                        self.assertTrue(check_uv())

        self.assertEqual(run.call_args.args[0], uv_install_cmd)
        self.assertTrue(run.call_args.kwargs["shell"])


class ChangeExplainerSubprocessSafetyTest(unittest.TestCase):
    def test_run_git_uses_utf8_replace(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="M test.py\n", stderr=""
        )
        run_git = cast(
            Callable[[Path, list[str]], tuple[bool, str]],
            getattr(change_explainer, "_run_git"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.change_explainer.subprocess.run", return_value=completed
            ) as run:
                ok, out = run_git(root, ["status", "--porcelain", "--", "."])

        self.assertTrue(ok)
        self.assertEqual(out, "M test.py\n")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")
        self.assertTrue(run.call_args.kwargs["text"])


if __name__ == "__main__":
    _ = unittest.main()
