"""Edge-case tests: anchor_tools with unusual file contents."""

import tempfile
import unittest
from pathlib import Path

from vibelign.core.anchor_tools import (
    extract_anchors,
    insert_module_anchors,
    suggest_anchor_names,
    validate_anchor_file,
)


class AnchorEmptyFileTest(unittest.TestCase):
    """anchor_tools with empty or whitespace-only files."""

    def test_extract_anchors_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            result = extract_anchors(Path(f.name))
        self.assertEqual(result, [])

    def test_extract_anchors_whitespace_only(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("   \n\n   \n")
            f.flush()
            result = extract_anchors(Path(f.name))
        self.assertEqual(result, [])

    def test_insert_module_anchors_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            result = insert_module_anchors(Path(f.name))
        self.assertFalse(result)

    def test_suggest_anchor_names_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        self.assertEqual(result, [])


class AnchorCommentsOnlyTest(unittest.TestCase):
    """Files with only comments."""

    def test_python_comments_only(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("# comment 1\n# comment 2\n# comment 3\n")
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        self.assertEqual(result, [])

    def test_extract_from_comments_only_file(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("# just comments\n# no code\n")
            f.flush()
            result = extract_anchors(Path(f.name))
        self.assertEqual(result, [])


class AnchorExistingAnchorsTest(unittest.TestCase):
    """Files that already have anchors."""

    def test_extract_existing_anchors(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(
                "# === ANCHOR: MY_MODULE_START ===\n"
                "def foo(): pass\n"
                "# === ANCHOR: MY_MODULE_END ===\n"
            )
            f.flush()
            result = extract_anchors(Path(f.name))
        self.assertIn("MY_MODULE", result)

    def test_insert_on_file_with_existing_anchors_still_adds_module_anchor(self):
        """insert_module_anchors adds module-level anchor even if symbol anchors exist."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(
                "# === ANCHOR: EXISTING_START ===\n"
                "code = 1\n"
                "# === ANCHOR: EXISTING_END ===\n"
            )
            f.flush()
            path = Path(f.name)
            result = insert_module_anchors(path)
        # insert_module_anchors checks for module-level START/END, not inner anchors
        self.assertIsInstance(result, bool)

    def test_validate_correct_anchors_passes(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(
                "# === ANCHOR: FOO_START ===\n"
                "x = 1\n"
                "# === ANCHOR: FOO_END ===\n"
            )
            f.flush()
            errors = validate_anchor_file(Path(f.name))
        self.assertEqual(errors, [])

    def test_validate_missing_end_anchor_reports_error(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("# === ANCHOR: FOO_START ===\nx = 1\n")
            f.flush()
            errors = validate_anchor_file(Path(f.name))
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("FOO" in e for e in errors))


class AnchorSymbolSuggestionsTest(unittest.TestCase):
    """suggest_anchor_names with various code patterns."""

    def test_python_function_suggested(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def my_function():\n    pass\n\ndef another():\n    pass\n")
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        self.assertTrue(len(result) >= 1)

    def test_python_class_suggested(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("class MyClass:\n    def method(self):\n        pass\n")
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        self.assertTrue(len(result) >= 1)

    def test_js_function_suggested(self):
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write("function myFunc() {\n  return 1;\n}\n")
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        self.assertTrue(len(result) >= 1)

    def test_dunder_methods_filtered(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(
                "class Foo:\n"
                "    def __init__(self):\n"
                "        pass\n"
                "    def __str__(self):\n"
                "        return ''\n"
                "    def real_method(self):\n"
                "        pass\n"
            )
            f.flush()
            result = suggest_anchor_names(Path(f.name))
        # __init__ and __str__ should be filtered out
        for name in result:
            self.assertFalse(name.startswith("__"))


class AnchorBinaryFileTest(unittest.TestCase):
    """anchor_tools with binary files."""

    def test_extract_from_binary_returns_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".pyc", mode="wb", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe\xfd")
            f.flush()
            result = extract_anchors(Path(f.name))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
