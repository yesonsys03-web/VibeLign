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
