import unittest

from pathlib import Path

from vibelign.core.project_scan import relpath_str
from vibelign.core.protected_files import is_protected, normalize_relpath
from vibelign.core.watch_engine import is_watchable_path


class CrossPlatformPathTest(unittest.TestCase):
    def test_normalize_relpath_uses_forward_slashes(self) -> None:
        self.assertEqual(normalize_relpath("src\\core\\main.py"), "src/core/main.py")

    def test_relpath_str_normalizes_windows_separators(self) -> None:
        root = Path("/repo")
        path = Path("/repo/src/core/main.py")
        self.assertEqual(relpath_str(root, path), "src/core/main.py")

    def test_protected_match_is_separator_agnostic(self) -> None:
        protected = {"src/core/main.py", "docs/readme.md"}
        self.assertTrue(is_protected("src\\core\\main.py", protected))
        self.assertTrue(is_protected("src/core/main.py", protected))

    def test_mixed_case_generated_dirs_are_excluded(self) -> None:
        class FakePath:
            parts: tuple[str, ...]
            name: str
            suffix: str

            def __init__(self, parts: tuple[str, ...], name: str, suffix: str) -> None:
                self.parts = parts
                self.name = name
                self.suffix = suffix

            def is_file(self) -> bool:
                return True

        self.assertFalse(
            is_watchable_path(
                FakePath(
                    ("C:", "Repo", "Node_Modules", "pkg", "index.js"), "index.js", ".js"
                )
            )
        )
        self.assertFalse(
            is_watchable_path(
                FakePath(("C:", "Repo", "DiSt", "bundle.js"), "bundle.js", ".js")
            )
        )


if __name__ == "__main__":
    _ = unittest.main()
