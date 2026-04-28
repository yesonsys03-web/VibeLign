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
