import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.git_hooks import (
    install_pre_commit_secret_hook,
    uninstall_pre_commit_secret_hook,
)


_HOOK_MARKER = "# vibelign: secrets-pre-commit v1"


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


if __name__ == "__main__":
    _ = unittest.main()
