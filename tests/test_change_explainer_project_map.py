import json
import os
import tempfile
import unittest
from pathlib import Path

from vibelign.core.change_explainer import explain_file_from_mtime


class ChangeExplainerProjectMapTest(unittest.TestCase):
    def test_explain_uses_project_map_kind_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "worker.py"
            target.write_text("def login():\n    return True\n", encoding="utf-8")
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_name": root.name,
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": [],
                        "service_modules": ["worker.py"],
                        "large_files": [],
                        "file_count": 1,
                        "generated_at": "2026-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                report = explain_file_from_mtime(root, "worker.py", since_minutes=120)
            finally:
                os.chdir(previous)

            self.assertEqual(report.files[0]["kind"], "service")

    def test_explain_falls_back_when_project_map_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "worker.py"
            target.write_text("def login():\n    return True\n", encoding="utf-8")
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "project_map.json").write_text(
                '{"schema_version": 999, "project_name": "broken"}\n',
                encoding="utf-8",
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                report = explain_file_from_mtime(root, "worker.py", since_minutes=120)
            finally:
                os.chdir(previous)

            self.assertEqual(report.files[0]["kind"], "logic")


if __name__ == "__main__":
    unittest.main()
