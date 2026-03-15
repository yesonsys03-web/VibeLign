import os
import unittest
import importlib
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vibelign.commands.vib_guard_cmd import run_vib_guard


_render_markdown = importlib.import_module(
    "vibelign.commands.vib_guard_cmd"
)._render_markdown


class VibGuardRenderTest(unittest.TestCase):
    def test_render_markdown_contains_status_and_next_steps(self):
        markdown = _render_markdown(
            {
                "status": "warn",
                "strict": False,
                "project_score": 68,
                "project_status": "Caution",
                "change_risk_level": "MEDIUM",
                "summary": "구조 위험이 조금 있습니다.",
                "recommendations": ["vib anchor --suggest", "vib guard --strict"],
                "protected_violations": [],
                "explain": {
                    "files": [{"path": "app.py", "status": "modified", "kind": "logic"}]
                },
            }
        )
        self.assertIn("전체 상태: 주의", markdown)
        self.assertIn("먼저 한 번 더 확인하는 게 좋아요", markdown)
        self.assertIn("## 다음에 하면 좋은 일", markdown)
        self.assertIn("구조 위험이 조금 있습니다.", markdown)
        self.assertIn("`app.py`", markdown)

    def test_run_vib_guard_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "vibelign.commands.vib_guard_cmd.print_ai_response"
                ) as mocked:
                    run_vib_guard(
                        SimpleNamespace(
                            json=False,
                            strict=False,
                            since_minutes=120,
                            write_report=False,
                        )
                    )
                    mocked.assert_called_once()
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
