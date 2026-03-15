"""Edge-case tests: change_explainer with various git scenarios."""

import tempfile
import unittest
from pathlib import Path

from vibelign.core.change_explainer import (
    explain_from_git,
    explain_file_from_git,
    explain_from_mtime,
    explain_file_from_mtime,
    risk_from_items,
    classify_path,
    _parse_unified_diff,
    ChangeItem,
)


class NoGitRepoTest(unittest.TestCase):
    """change_explainer when git is not available."""

    def test_explain_from_git_no_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = explain_from_git(Path(tmp))
        self.assertIsNone(result)

    def test_explain_file_from_git_no_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = explain_file_from_git(Path(tmp), "main.py")
        self.assertIsNone(result)


class MtimeFallbackTest(unittest.TestCase):
    """change_explainer mtime-based fallback."""

    def test_explain_from_mtime_no_recent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = explain_from_mtime(Path(tmp), since_minutes=120)
        self.assertEqual(result.risk_level, "LOW")
        self.assertEqual(result.source, "mtime")
        self.assertEqual(result.files, [])

    def test_explain_file_from_mtime_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = explain_file_from_mtime(Path(tmp), "nonexistent.py")
        self.assertEqual(result.risk_level, "MEDIUM")
        self.assertIn("찾을 수 없", result.summary)

    def test_explain_file_from_mtime_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.py"
            f.write_text("print('hi')\n")
            result = explain_file_from_mtime(Path(tmp), "test.py", since_minutes=9999)
        self.assertEqual(result.source, "mtime")
        self.assertIn("test.py", result.summary)


class DiffParsingTest(unittest.TestCase):
    """_parse_unified_diff edge cases."""

    def test_empty_diff(self):
        result = _parse_unified_diff("")
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["sections"], [])

    def test_only_context_lines(self):
        diff = " line1\n line2\n line3\n"
        result = _parse_unified_diff(diff)
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])

    def test_adds_and_removes(self):
        diff = "+new line\n-old line\n"
        result = _parse_unified_diff(diff)
        self.assertEqual(result["added"], ["new line"])
        self.assertEqual(result["removed"], ["old line"])

    def test_hunk_header_extracts_section(self):
        diff = "@@ -1,5 +1,5 @@ def my_function():\n+new\n"
        result = _parse_unified_diff(diff)
        self.assertIn("def my_function():", result["sections"])

    def test_ignores_file_headers(self):
        diff = "--- a/file.py\n+++ b/file.py\n+added\n"
        result = _parse_unified_diff(diff)
        self.assertEqual(result["added"], ["added"])
        self.assertEqual(result["removed"], [])


class RiskScoringTest(unittest.TestCase):
    """risk_from_items edge cases."""

    def test_empty_items(self):
        self.assertEqual(risk_from_items([]), "LOW")

    def test_single_general_item(self):
        items = [ChangeItem("readme.md", "modified", "docs")]
        self.assertEqual(risk_from_items(items), "LOW")

    def test_entry_file_modified(self):
        items = [ChangeItem("main.py", "modified", "entry file")]
        result = risk_from_items(items)
        self.assertIn(result, {"LOW", "MEDIUM"})

    def test_many_general_items_get_count_bonus(self):
        """10 general items: score=0 each + len>=8 bonus(+3) = 3 → LOW."""
        items = [ChangeItem(f"file{i}.py", "modified", "general") for i in range(10)]
        result = risk_from_items(items)
        self.assertIn(result, {"LOW", "MEDIUM"})

    def test_many_logic_items_is_high_risk(self):
        """10 logic items: score=2 each (20) + len>=8 (+3) = 23 → HIGH."""
        items = [ChangeItem(f"svc{i}.py", "modified", "logic") for i in range(10)]
        self.assertEqual(risk_from_items(items), "HIGH")

    def test_deleted_entry_file_is_medium(self):
        """entry file(3) + deleted(+3) = 6 → MEDIUM (>=4 but <8)."""
        items = [ChangeItem("main.py", "deleted", "entry file")]
        self.assertEqual(risk_from_items(items), "MEDIUM")

    def test_multiple_deleted_entry_files_is_high(self):
        items = [
            ChangeItem("main.py", "deleted", "entry file"),
            ChangeItem("app.py", "deleted", "entry file"),
        ]
        self.assertEqual(risk_from_items(items), "HIGH")


class ClassifyPathTest(unittest.TestCase):
    """classify_path edge cases."""

    def test_main_py(self):
        self.assertEqual(classify_path("main.py"), "entry file")

    def test_subdirectory_main_py(self):
        self.assertEqual(classify_path("src/main.py"), "entry file")

    def test_test_file(self):
        self.assertEqual(classify_path("tests/test_foo.py"), "test")

    def test_markdown(self):
        self.assertEqual(classify_path("README.md"), "docs")

    def test_general_python(self):
        self.assertEqual(classify_path("foo.py"), "general")

    def test_worker_file(self):
        self.assertEqual(classify_path("backup_worker.py"), "logic")


if __name__ == "__main__":
    unittest.main()
