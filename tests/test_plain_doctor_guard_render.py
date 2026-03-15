import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vibelign.commands.guard_cmd import _render_markdown as render_guard_markdown
from vibelign.commands.doctor_cmd import run_doctor
from vibelign.commands.guard_cmd import run_guard


class PlainDoctorGuardRenderTest(unittest.TestCase):
    def test_guard_markdown_uses_friendly_labels(self):
        class Report:
            overall_level = "GOOD"
            blocked = False
            doctor_level = "GOOD"
            doctor_score = 0
            change_risk_level = "LOW"
            summary = "지금은 큰 문제가 없어 보여요."
            recommendations = ["다음 소규모 수정으로 넘어가도 됩니다."]
            doctor = {"issues": []}
            explain = {"files": []}

        markdown = render_guard_markdown(Report())
        self.assertIn("## 다음에 하면 좋은 일", markdown)
        self.assertIn("지금 멈춰야 하나요?", markdown)
        self.assertIn("최근에 바뀐 파일이 없습니다.", markdown)

    def test_run_doctor_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.doctor_cmd.print_ai_response") as mocked:
                    run_doctor(SimpleNamespace(json=False, strict=False))
                    mocked.assert_called_once()
                    rendered = mocked.call_args[0][0]
                    self.assertIn("## 2. 한눈에 보는 숫자", rendered)
                    self.assertIn("안전 구역 표시가 없는 파일 수", rendered)
            finally:
                os.chdir(previous)

    def test_run_guard_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.guard_cmd.print_ai_response") as mocked:
                    run_guard(
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
