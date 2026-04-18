import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.project_scan import (
    classify_file,
    iter_project_files,
    iter_source_files,
)


class ProjectScanTest(unittest.TestCase):
    def test_iter_project_files_excludes_generated_and_non_scan_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "target").mkdir()
            _ = (root / "target" / "bundle.js").write_text("bundle\n", encoding="utf-8")
            (root / "docs").mkdir()
            _ = (root / "docs" / "guide.md").write_text("docs\n", encoding="utf-8")
            (root / "tests").mkdir()
            _ = (root / "tests" / "test_app.py").write_text("pass\n", encoding="utf-8")
            (root / ".vibelign").mkdir()
            _ = (root / ".vibelign" / "project_map.json").write_text(
                "{}\n", encoding="utf-8"
            )

            files = {
                path.relative_to(root).as_posix() for path in iter_project_files(root)
            }

        self.assertEqual(files, {"src/app.py"})

    def test_iter_source_files_uses_shared_source_extensions_without_fd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            _ = (root / "src" / "notes.txt").write_text("notes\n", encoding="utf-8")

            with patch("vibelign.core.fast_tools.has_fd", return_value=False):
                files = {
                    path.relative_to(root).as_posix()
                    for path in iter_source_files(root)
                }

        self.assertEqual(files, {"src/app.py"})

    def test_classify_file_uses_shared_core_entry_policy(self):
        self.assertEqual(
            classify_file(Path("vibelign/vib_cli.py"), "vibelign/vib_cli.py"),
            "entry",
        )
        self.assertEqual(
            classify_file(Path("vibelign/mcp_server.py"), "vibelign/mcp_server.py"),
            "entry",
        )


if __name__ == "__main__":
    unittest.main()
