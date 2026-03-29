import tempfile
import unittest
from pathlib import Path

from vibelign.core.patch_validation import (
    MIN_SEARCH_BLOCK_LINES,
    err_strict_search_too_short,
    search_block_meets_min_lines,
)
from vibelign.core.local_checkpoints import list_checkpoints
from vibelign.core.strict_patch import apply_strict_patch


class PatchValidationStrictTest(unittest.TestCase):
    def test_search_block_meets_min_lines_counts_physical_lines(self):
        self.assertFalse(search_block_meets_min_lines("a\nb"))
        self.assertTrue(search_block_meets_min_lines("a\nb\nc"))

    def test_apply_strict_patch_rejects_short_search_even_if_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "tiny.py"
            target.write_text(
                "# === ANCHOR: TINY_START ===\n# === ANCHOR: TINY_END ===\n",
                encoding="utf-8",
            )
            search = "# === ANCHOR: TINY_START ===\n# === ANCHOR: TINY_END ===\n"
            self.assertLess(len(search.splitlines()), MIN_SEARCH_BLOCK_LINES)
            result = apply_strict_patch(
                root,
                {
                    "operations": [
                        {
                            "target_file": "tiny.py",
                            "target_anchor": "TINY",
                            "search": search,
                            "replace": search,
                        }
                    ]
                },
            )
            self.assertFalse(result["ok"])
            self.assertIn(
                err_strict_search_too_short(len(search.splitlines())),
                str(result["error"]),
            )

    def test_apply_strict_patch_dry_run_validates_without_write_or_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = (
                "# === ANCHOR: M_START ===\n"
                "def f():\n"
                "    return 1\n"
                "# === ANCHOR: M_END ===\n"
            )
            target = root / "m.py"
            target.write_text(content, encoding="utf-8")
            search = (
                "# === ANCHOR: M_START ===\n"
                "def f():\n"
                "    return 1\n"
                "# === ANCHOR: M_END ===\n"
            )
            replace = (
                "# === ANCHOR: M_START ===\n"
                "def f():\n"
                "    return 2\n"
                "# === ANCHOR: M_END ===\n"
            )
            result = apply_strict_patch(
                root,
                {
                    "operations": [
                        {
                            "target_file": "m.py",
                            "target_anchor": "M",
                            "search": search,
                            "replace": replace,
                        }
                    ]
                },
                dry_run=True,
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result.get("dry_run"))
            self.assertIsNone(result.get("checkpoint_id"))
            self.assertEqual(target.read_text(encoding="utf-8"), content)
            self.assertEqual(len(list_checkpoints(root)), 0)


if __name__ == "__main__":
    unittest.main()
