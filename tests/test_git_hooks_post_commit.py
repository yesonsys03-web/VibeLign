import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.internal_post_commit_cmd import run_internal_post_commit
from vibelign.core.git_hooks import (
    install_post_commit_record_hook,
    uninstall_post_commit_record_hook,
)


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)


class PostCommitHookTest(unittest.TestCase):
    def test_installs_hook_with_marker_and_exec_bit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            result = install_post_commit_record_hook(root)
            self.assertEqual(result.status, "installed")
            hook = root / ".git" / "hooks" / "post-commit"
            self.assertTrue(hook.exists())
            self.assertTrue(os.access(hook, os.X_OK))
            content = hook.read_text()
            self.assertIn("# vibelign: post-commit-record v4", content)
            self.assertIn("# vibelign: post-commit-record-end", content)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            r1 = install_post_commit_record_hook(root)
            r2 = install_post_commit_record_hook(root)
            self.assertEqual(r1.status, "installed")
            self.assertEqual(r2.status, "already-installed")

    def test_returns_not_git_when_no_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = install_post_commit_record_hook(Path(tmp))
            self.assertEqual(r.status, "not-git")

    def test_prepends_to_existing_hook_so_runs_before_existing_exit(self):
        """기존 hook 끝에 exit 가 있어도 vibelign 블록이 먼저 실행되어야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook_path = root / ".git" / "hooks" / "post-commit"
            hook_path.write_text("#!/bin/sh\necho 'user hook'\nexit 0\n")
            hook_path.chmod(0o755)

            install_post_commit_record_hook(root)
            content = hook_path.read_text()
            # 셔뱅은 위 1줄, 그 직후 vibelign 블록, 그 다음 기존 사용자 hook
            lines = content.splitlines()
            shebang_idx = next(i for i, l in enumerate(lines) if l.startswith("#!"))
            vib_start_idx = next(i for i, l in enumerate(lines) if "post-commit-record v4" in l)
            user_idx = next(i for i, l in enumerate(lines) if "user hook" in l)
            self.assertLess(shebang_idx, vib_start_idx)
            self.assertLess(vib_start_idx, user_idx)

    def test_upgrades_old_hook_block_to_v4(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook = root / ".git" / "hooks" / "post-commit"
            hook.write_text(
                "#!/bin/sh\n"
                "# vibelign: post-commit-record v1\n"
                "old command\n"
                "# vibelign: post-commit-record-end\n"
                "echo user hook\n",
                encoding="utf-8",
            )
            hook.chmod(0o700)

            result = install_post_commit_record_hook(root)
            content = hook.read_text(encoding="utf-8")

            self.assertEqual(result.status, "updated")
            self.assertIn("# vibelign: post-commit-record v4", content)
            self.assertNotIn("old command", content)
            self.assertIn("echo user hook", content)
            self.assertEqual(stat.S_IMODE(hook.stat().st_mode), 0o700)

    def test_preserves_crlf_when_updating_existing_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook = root / ".git" / "hooks" / "post-commit"
            hook.write_bytes(b"#!/bin/sh\r\necho user hook\r\n")
            hook.chmod(0o755)

            install_post_commit_record_hook(root)

            content = hook.read_bytes()
            self.assertIn(b"# vibelign: post-commit-record v4\r\n", content)
            self.assertNotIn(b"# vibelign: post-commit-record v4\nsha=", content)

    def test_uninstall_preserves_existing_user_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook = root / ".git" / "hooks" / "post-commit"
            hook.write_text("#!/bin/sh\necho 'user hook'\nexit 0\n")
            hook.chmod(0o755)

            install_post_commit_record_hook(root)
            uninstall_post_commit_record_hook(root)
            content = hook.read_text()

            # User content preserved
            self.assertIn("user hook", content)
            self.assertNotIn("post-commit-record v4", content)

            # CRITICAL: shebang must be on its own first line, NOT fused with next line
            lines = content.splitlines()
            self.assertEqual(lines[0], "#!/bin/sh",
                f"shebang corrupted: first line is '{lines[0]}'")

            # CRITICAL: hook must be syntactically valid shell
            result = subprocess.run(
                ["sh", "-n", str(hook)],
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0,
                f"sh -n failed: {result.stderr.decode()}")

    def test_uninstall_removes_file_when_only_vibelign_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            install_post_commit_record_hook(root)
            uninstall_post_commit_record_hook(root)
            self.assertFalse((root / ".git" / "hooks" / "post-commit").exists())

    def test_hook_contains_python_module_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            install_post_commit_record_hook(root)
            content = (root / ".git" / "hooks" / "post-commit").read_text()
            self.assertIn("VIBELIGN_REQUIRE_RUST_CHECKPOINT=1", content)
            self.assertIn("uv run python -m vibelign.cli.vib_cli _internal_post_commit", content)
            self.assertIn("python -m vibelign.cli.vib_cli _internal_post_commit", content)
            self.assertIn("py -3 -m vibelign.cli.vib_cli _internal_post_commit", content)
            self.assertIn("python3 -m vibelign.cli.vib_cli _internal_post_commit", content)
            self.assertLess(
                content.index("uv run python -m vibelign.cli.vib_cli _internal_post_commit"),
                content.index("vib _internal_post_commit"),
            )

    def test_hook_contains_absolute_path_fallbacks_at_top(self):
        """install 시점 shutil.which('vib') / sys.executable 이 hook 상단에 박힌다.

        Why: GUI commit tool (Sourcetree, VS Code 등) 이 launchd PATH 만 상속해
        ~/.local/bin 이 빠지면 `command -v vib` 가 false → 자동 백업 누락. 절대
        경로 분기가 PATH 분기보다 먼저 와야 회귀를 막을 수 있다.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            with patch(
                "vibelign.core.git_hooks.shutil.which",
                side_effect=lambda name: {
                    "vib": "/fake/abs/vib",
                    "vibelign": "/fake/abs/vibelign",
                }.get(name),
            ):
                with patch(
                    "vibelign.core.git_hooks.sys.executable", "/fake/abs/python3"
                ):
                    install_post_commit_record_hook(root)
            content = (root / ".git" / "hooks" / "post-commit").read_text()
            self.assertIn('[ -x "/fake/abs/vib" ]', content)
            self.assertIn('[ -x "/fake/abs/vibelign" ]', content)
            self.assertIn('[ -x "/fake/abs/python3" ]', content)
            # 절대 경로 분기가 PATH 기반 fallback (command -v ...) 보다 먼저 와야 한다.
            self.assertLess(
                content.index('[ -x "/fake/abs/vib" ]'),
                content.index("command -v uv"),
            )

    def test_internal_post_commit_records_once_and_runs_auto_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("sys.stdin.read", return_value="feat: demo"):
                with patch(
                    "vibelign.commands.internal_post_commit_cmd.record_commit_message"
                ) as record:
                    with patch(
                        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup"
                    ) as backup:
                        run_internal_post_commit(type("Args", (), {"sha": "abc1234"})(), root=root)

            record.assert_called_once_with(root, "abc1234", "feat: demo")
            backup.assert_called_once_with(root, "abc1234", "feat: demo")
