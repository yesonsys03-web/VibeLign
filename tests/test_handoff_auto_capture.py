import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import load_work_memory


class InternalRecordCommitCLITest(unittest.TestCase):
    def _run_cli(self, args, stdin_text):
        """argparse 진입점 직접 호출 (subprocess 없이)."""
        from vibelign.cli.vib_cli import main as vib_main
        original_cwd = Path.cwd()
        try:
            with patch("sys.stdin", io.StringIO(stdin_text)):
                rc = vib_main(args)
        finally:
            pass
        return rc

    def test_records_commit_from_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            MetaPaths(root).ensure_vibelign_dirs()
            with patch("os.getcwd", return_value=str(root)):
                # subcommand 만 인자, message 는 stdin 으로
                from vibelign.commands.internal_record_commit_cmd import (
                    run_internal_record_commit,
                )
                from argparse import Namespace
                with patch("sys.stdin", io.StringIO("feat: hello\n\nbody\n한글 ✨")):
                    run_internal_record_commit(Namespace(sha="abc1234"), root=root)

            state = load_work_memory(MetaPaths(root).work_memory_path)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "commit")
            self.assertIn("feat: hello", event["message"])
            self.assertEqual(state["decisions"], [])

    def test_records_commit_from_default_cwd(self):
        """Production path: hook -> argparse -> lazy_command -> runner without explicit root.
        The function falls back to Path.cwd(), which respects os.getcwd patching."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            MetaPaths(root).ensure_vibelign_dirs()
            from vibelign.commands.internal_record_commit_cmd import (
                run_internal_record_commit,
            )
            from argparse import Namespace
            with patch("os.getcwd", return_value=str(root)):
                with patch("sys.stdin", io.StringIO("feat: default cwd path")):
                    run_internal_record_commit(Namespace(sha="abc1234"))  # no root=

            state = load_work_memory(MetaPaths(root).work_memory_path)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "commit")
            self.assertIn("default cwd", event["message"])

    def test_swallows_stdin_read_failure(self):
        """Hook must never break user's git commit even if stdin read fails."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            MetaPaths(root).ensure_vibelign_dirs()
            from vibelign.commands.internal_record_commit_cmd import (
                run_internal_record_commit,
            )
            from argparse import Namespace

            class BrokenStdin:
                def read(self):
                    raise OSError("pipe closed")

            with patch("sys.stdin", BrokenStdin()):
                # Should not raise -- the function swallows the error
                run_internal_record_commit(Namespace(sha="abc1234"), root=root)

            # No event recorded since stdin failed
            state = load_work_memory(MetaPaths(root).work_memory_path)
            self.assertEqual(state["recent_events"], [])


class EndToEndTest(unittest.TestCase):
    def _git_repo(self, root: Path) -> None:
        import subprocess
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@v.local"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)

    def test_commit_does_not_pollute_active_intent(self):
        import subprocess
        from vibelign.core.git_hooks import install_post_commit_record_hook
        from vibelign.core.work_memory import build_transfer_summary

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git_repo(root)
            MetaPaths(root).ensure_vibelign_dirs()
            install_post_commit_record_hook(root)

            (root / "README.md").write_text("hi\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore(gui): Tauri 앱 번들을 2.0.35로 정렬"],
                cwd=root, check=True, capture_output=True,
            )

            wm = MetaPaths(root).work_memory_path
            state = load_work_memory(wm)
            self.assertEqual(state["decisions"], [],
                "commit 은 decisions 에 들어가면 안 된다 — active_intent 오염")
            self.assertTrue(
                any(e.get("kind") == "commit" for e in state["recent_events"]),
                "commit 은 recent_events 에 있어야 한다",
            )

            # Explicit decision 기록
            from vibelign.core.work_memory import add_decision
            add_decision(wm, "1-B 옵션 채택: 통일성 우선")

            summary = build_transfer_summary(wm)
            self.assertEqual(summary["active_intent"], "1-B 옵션 채택: 통일성 우선",
                "active_intent 는 명시 decision 이어야 함, commit msg 가 아님")

    def test_multiline_korean_commit_message(self):
        import subprocess
        from vibelign.core.git_hooks import install_post_commit_record_hook

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git_repo(root)
            MetaPaths(root).ensure_vibelign_dirs()
            install_post_commit_record_hook(root)

            (root / "f.txt").write_text("x")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            msg = "feat: 한글 ✨\n\n본문 line 1\n본문 line 2"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=root, check=True, capture_output=True,
            )

            state = load_work_memory(MetaPaths(root).work_memory_path)
            commit_event = next(
                e for e in state["recent_events"] if e.get("kind") == "commit"
            )
            self.assertIn("한글 ✨", commit_event["message"])
