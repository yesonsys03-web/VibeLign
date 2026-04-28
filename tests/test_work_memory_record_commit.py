import tempfile
import unittest
from pathlib import Path
from vibelign.core.work_memory import record_commit, load_work_memory


class RecordCommitTest(unittest.TestCase):
    def test_appends_commit_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234deadbeef", "feat(mcp): new tool")
            state = load_work_memory(wm)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "commit")
            self.assertEqual(event["message"], "feat(mcp): new tool")
            self.assertIn("abc1234", event["path"])

    def test_does_not_touch_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "chore: bump 2.0.35")
            state = load_work_memory(wm)
            self.assertEqual(state["decisions"], [])

    def test_handles_multiline_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            msg = "feat: x\n\nbody line\nbody line 2\n\n한글 ✨"
            record_commit(wm, "abc1234", msg)
            event = load_work_memory(wm)["recent_events"][-1]
            # truncate 후에도 첫 줄과 한글 보존
            self.assertIn("feat: x", event["message"])

    def test_skips_blank_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "")
            self.assertEqual(load_work_memory(wm)["recent_events"], [])


class RecordCheckpointTest(unittest.TestCase):
    def test_appends_checkpoint_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            from vibelign.core.work_memory import record_checkpoint
            record_checkpoint(wm, "v2.0.35 작업 전 안전 저장")

            state = load_work_memory(wm)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "checkpoint")
            self.assertEqual(event["path"], "checkpoint")
            self.assertIn("v2.0.35", event["message"])
            self.assertEqual(state["decisions"], [])
            self.assertEqual(state["relevant_files"], [])

    def test_skips_blank_checkpoint_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            from vibelign.core.work_memory import record_checkpoint
            record_checkpoint(wm, "")
            self.assertEqual(load_work_memory(wm)["recent_events"], [])


class BuildTransferSummaryFilterTest(unittest.TestCase):
    def test_commit_path_excluded_from_changed_files(self):
        from vibelign.core.work_memory import (
            record_commit, build_transfer_summary, add_relevant_file,
        )
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "feat: x")
            add_relevant_file(wm, "vibelign/core/work_memory.py", "real file")
            summary = build_transfer_summary(wm)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertIn("vibelign/core/work_memory.py", summary["changed_files"])
            self.assertNotIn("git/abc1234", summary["changed_files"])

    def test_checkpoint_path_excluded_from_changed_files(self):
        from vibelign.core.work_memory import (
            record_checkpoint, build_transfer_summary, add_relevant_file,
        )
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_checkpoint(wm, "v2.0.35 안전 저장")
            add_relevant_file(wm, "vibelign/core/git_hooks.py", "real file")
            summary = build_transfer_summary(wm)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertIn("vibelign/core/git_hooks.py", summary["changed_files"])
            self.assertNotIn("checkpoint", summary["changed_files"])

    def test_synthetic_paths_still_appear_in_recent_events_and_change_details(self):
        """sentinel filter 는 changed_files 만 적용. 다른 출력 칸 보존 확인."""
        from vibelign.core.work_memory import (
            record_commit, build_transfer_summary,
        )
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "feat(mcp): new tool")
            summary = build_transfer_summary(wm)
            self.assertIsNotNone(summary)
            assert summary is not None
            # change_details 는 commit 이벤트를 포함해야 함
            self.assertTrue(
                any("git/abc1234" in line or "feat(mcp)" in line
                    for line in summary["change_details"]),
                f"change_details should contain commit event: {summary['change_details']}",
            )
