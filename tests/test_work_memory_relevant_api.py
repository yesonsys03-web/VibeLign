import tempfile
import unittest
from pathlib import Path
from vibelign.core.work_memory import add_relevant_file, load_work_memory


class AddRelevantFileTest(unittest.TestCase):
    def test_appends_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "vibelign/core/work_memory.py", "core narrative store")
            state = load_work_memory(wm)
            self.assertEqual(
                state["relevant_files"][-1],
                {"path": "vibelign/core/work_memory.py", "why": "core narrative store"},
            )

    def test_dedups_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "a.py", "first")
            add_relevant_file(wm, "a.py", "updated")
            state = load_work_memory(wm)
            self.assertEqual(len(state["relevant_files"]), 1)
            self.assertEqual(state["relevant_files"][0]["why"], "updated")

    def test_skips_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "/absolute/path", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])

    def test_skips_excluded_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, ".omc/state/x.json", "skip")
            add_relevant_file(wm, ".vibelign/work_memory.json", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])

    def test_skips_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "../escape", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])
