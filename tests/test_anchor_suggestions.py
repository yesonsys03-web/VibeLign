import tempfile
import unittest
from pathlib import Path

from vibelign.core.anchor_tools import recommend_anchor_targets, suggest_anchor_names
from vibelign.core.project_map import ProjectMapSnapshot


class AnchorSuggestionsTest(unittest.TestCase):
    def test_python_symbols_become_suggested_anchor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(
                "class LoginService:\n    pass\n\ndef render_progress_bar():\n    return True\n",
                encoding="utf-8",
            )
            names = suggest_anchor_names(path)
            self.assertIn("LOGINSERVICE", names)
            self.assertIn("RENDER_PROGRESS_BAR", names)

    def test_recommend_anchor_targets_prioritizes_entry_and_large_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "main.py"
            ui = root / "login_ui.py"
            entry.write_text(
                "\n".join("x=1" for _ in range(320)) + "\n", encoding="utf-8"
            )
            ui.write_text(
                "def render_login():\n    return True\n\nclass LoginPanel:\n    pass\n",
                encoding="utf-8",
            )
            project_map = ProjectMapSnapshot(
                schema_version=1,
                project_name=root.name,
                entry_files=frozenset({"main.py"}),
                ui_modules=frozenset({"login_ui.py"}),
                core_modules=frozenset(),
                service_modules=frozenset(),
                large_files=frozenset({"main.py"}),
                file_count=2,
                generated_at="2026-03-15T00:00:00Z",
            )

            recommendations = recommend_anchor_targets(root, project_map=project_map)

            self.assertEqual(recommendations[0]["path"], "main.py")
            self.assertTrue(
                any("파일이 커서" in reason for reason in recommendations[0]["reasons"])
            )
            self.assertTrue(
                any(
                    "프로젝트 시작점" in reason
                    for reason in recommendations[0]["reasons"]
                )
            )


if __name__ == "__main__":
    unittest.main()
