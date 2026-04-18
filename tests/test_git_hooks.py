import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.git_hooks import (
    install_pre_commit_secret_hook,
    uninstall_pre_commit_secret_hook,
)


_HOOK_MARKER = "# vibelign: pre-commit-enforcement v2"


class GitHooksTest(unittest.TestCase):
    def test_install_writes_vibelign_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "installed")
            hook_text = (hooks_dir / "pre-commit").read_text(encoding="utf-8")
            self.assertIn(_HOOK_MARKER, hook_text)
            self.assertIn("vib secrets --staged", hook_text)
            self.assertIn("vib guard --strict", hook_text)

    def test_install_prefers_current_vib_path_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                with patch(
                    "vibelign.core.git_hooks.shutil.which", return_value="/tmp/vib"
                ):
                    result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "installed")
            hook_text = (hooks_dir / "pre-commit").read_text(encoding="utf-8")
            self.assertIn('"/tmp/vib" secrets --staged', hook_text)
            self.assertIn("vib guard --strict", hook_text)

    def test_install_uses_refactored_module_fallback_when_vib_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                with patch("vibelign.core.git_hooks.shutil.which", return_value=None):
                    with patch("vibelign.core.git_hooks.sys.executable", "/tmp/python"):
                        result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "installed")
            hook_text = (hooks_dir / "pre-commit").read_text(encoding="utf-8")
            self.assertIn(
                '"/tmp/python" -m vibelign.cli.vib_cli secrets --staged',
                hook_text,
            )
            self.assertIn(
                '"/tmp/python" -m vibelign.cli.vib_cli guard --strict',
                hook_text,
            )

    def test_install_does_not_overwrite_foreign_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "pre-commit"
            _ = hook_path.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "existing-hook")
            self.assertNotIn(_HOOK_MARKER, hook_path.read_text(encoding="utf-8"))

    def test_uninstall_removes_only_vibelign_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "pre-commit"
            _ = hook_path.write_text(f"#!/bin/sh\n{_HOOK_MARKER}\n", encoding="utf-8")
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                result = uninstall_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "removed")
            self.assertFalse(hook_path.exists())

    def _write_fake_command(self, path: Path, script: str) -> None:
        _ = path.write_text(script, encoding="utf-8")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_hook_stops_on_secret_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            bin_dir = root / "bin"
            hooks_dir.mkdir(parents=True)
            bin_dir.mkdir(parents=True)
            log_path = root / "calls.log"
            self._write_fake_command(
                bin_dir / "vib",
                "#!/bin/sh\n"
                f'printf "%s\\n" "$*" >> "{log_path}"\n'
                'if [ "$1" = "secrets" ]; then\n'
                "  exit 9\n"
                "fi\n"
                "exit 0\n",
            )
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                with patch("vibelign.core.git_hooks.shutil.which", return_value=None):
                    with patch("vibelign.core.git_hooks.sys.executable", None):
                        result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "installed")
            hook_path = hooks_dir / "pre-commit"
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)
            proc = subprocess.run(
                [str(hook_path)], cwd=root, env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 9)
            calls = log_path.read_text(encoding="utf-8")
            self.assertIn("secrets --staged", calls)
            self.assertNotIn("guard --strict", calls)

    def test_hook_returns_guard_failure_after_secret_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            bin_dir = root / "bin"
            hooks_dir.mkdir(parents=True)
            bin_dir.mkdir(parents=True)
            log_path = root / "calls.log"
            self._write_fake_command(
                bin_dir / "vib",
                "#!/bin/sh\n"
                f'printf "%s\\n" "$*" >> "{log_path}"\n'
                'if [ "$1" = "guard" ]; then\n'
                "  exit 7\n"
                "fi\n"
                "exit 0\n",
            )
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                with patch("vibelign.core.git_hooks.shutil.which", return_value=None):
                    with patch("vibelign.core.git_hooks.sys.executable", None):
                        _ = install_pre_commit_secret_hook(root)
            hook_path = hooks_dir / "pre-commit"
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)
            proc = subprocess.run(
                [str(hook_path)], cwd=root, env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 7)
            calls = log_path.read_text(encoding="utf-8")
            self.assertIn("secrets --staged", calls)
            self.assertIn("guard --strict", calls)

    def test_hook_uses_vibelign_fallback_for_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            bin_dir = root / "bin"
            hooks_dir.mkdir(parents=True)
            bin_dir.mkdir(parents=True)
            log_path = root / "calls.log"
            self._write_fake_command(
                bin_dir / "vibelign",
                f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log_path}"\nexit 0\n',
            )
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                with patch("vibelign.core.git_hooks.shutil.which", return_value=None):
                    with patch("vibelign.core.git_hooks.sys.executable", None):
                        _ = install_pre_commit_secret_hook(root)
            hook_path = hooks_dir / "pre-commit"
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)
            proc = subprocess.run(
                [str(hook_path)], cwd=root, env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 0)
            calls = log_path.read_text(encoding="utf-8")
            self.assertIn("secrets --staged", calls)
            self.assertIn("guard --strict", calls)

    def test_git_hook_remains_strict_even_when_claude_hook_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            _ = (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: false\n", encoding="utf-8"
            )
            with patch("vibelign.core.git_hooks.get_hooks_dir", return_value=hooks_dir):
                result = install_pre_commit_secret_hook(root)
            self.assertEqual(result.status, "installed")
            hook_text = (hooks_dir / "pre-commit").read_text(encoding="utf-8")
            self.assertIn("vib guard --strict", hook_text)


if __name__ == "__main__":
    _ = unittest.main()
