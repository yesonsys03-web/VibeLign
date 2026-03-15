import os
import unittest
from types import SimpleNamespace
import tempfile
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_explain_cmd import _render_markdown, run_vib_explain


class VibExplainRenderTest(unittest.TestCase):
    def test_render_markdown_uses_three_section_structure(self):
        markdown = _render_markdown(
            {
                "source": "git",
                "risk_level": "LOW",
                "what_changed": ["login.py 수정"],
                "why_it_matters": ["로그인 흐름이 달라질 수 있습니다."],
                "what_to_do_next": "다음으로 vib guard 를 실행하세요.",
                "files": [{"path": "login.py", "status": "modified", "kind": "logic"}],
                "summary": "최근 파일 변경이 있습니다.",
            }
        )
        self.assertIn("## 1. 한 줄 요약", markdown)
        self.assertIn("## 2. 변경된 내용", markdown)
        self.assertIn("## 3. 왜 중요한가", markdown)
        self.assertIn("## 4. 다음 할 일", markdown)
        self.assertIn("위험 수준: 낮음", markdown)

    def test_run_vib_explain_uses_rich_renderer_for_plain_text_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                with patch(
                    "vibelign.commands.vib_explain_cmd.print_ai_response"
                ) as mocked:
                    os.chdir(root)
                    run_vib_explain(
                        SimpleNamespace(
                            file=None,
                            json=False,
                            ai=False,
                            write_report=False,
                            since_minutes=120,
                        )
                    )
                    mocked.assert_called_once()
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
