import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vibelign.commands.vib_patch_cmd import (
    _build_contract,
    _render_markdown,
    run_vib_patch,
)


class VibPatchRenderTest(unittest.TestCase):
    def test_render_markdown_uses_friendly_korean_labels(self):
        markdown = _render_markdown(
            {
                "patch_plan": {
                    "interpretation": "로그인 보호 로직을 추가하는 요청으로 이해했습니다.",
                    "codespeak": "service.auth.login_guard.add",
                    "confidence": "low",
                    "target_file": "login_ui.py",
                    "target_anchor": "[먼저 앵커를 추가하세요]",
                    "rationale": ["경로에 login 키워드가 포함됨"],
                    "clarifying_questions": [],
                }
            },
            preview_text="def render_login():\n    return True\n",
        )
        self.assertIn("# VibeLign 패치 계획", markdown)
        self.assertIn("지금 상태:", markdown)
        self.assertIn("조금 더 알려주면 바로 도와줄 수 있어요", markdown)
        self.assertIn("먼저 이렇게 해보세요", markdown)
        self.assertIn("지금은 바로 수정하지 마세요.", markdown)
        self.assertIn("먼저 확인하면 좋은 질문", markdown)
        self.assertIn("정확히 어느 함수나 구역", markdown)
        self.assertIn("수정 대상 요약", markdown)
        self.assertIn("왜 이렇게 골랐는지", markdown)
        self.assertIn("미리 보기", markdown)
        self.assertIn("다음에 할 일", markdown)

    def test_run_vib_patch_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_ui.py").write_text(
                "def render_login():\n    return True\n", encoding="utf-8"
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "vibelign.commands.vib_patch_cmd.print_ai_response"
                ) as mocked:
                    run_vib_patch(
                        SimpleNamespace(
                            request=["add", "login", "guard"],
                            ai=False,
                            json=False,
                            preview=True,
                            write_report=False,
                        )
                    )
                    mocked.assert_called_once()
            finally:
                os.chdir(previous)

    def test_render_markdown_shows_run_now_guidance_for_ready_state(self):
        patch_plan = {
            "interpretation": "로그인 보호 로직을 고치는 요청으로 이해했습니다.",
            "codespeak": "service.auth.login_guard.fix",
            "confidence": "high",
            "target_file": "login_ui.py",
            "target_anchor": "LOGIN_UI_LOGIN_GUARD",
            "rationale": ["경로에 login 키워드가 포함됨"],
            "clarifying_questions": [],
        }
        markdown = _render_markdown(
            {"patch_plan": patch_plan, "contract": _build_contract(patch_plan)}
        )
        self.assertIn("지금 바로 진행할 수 있어요", markdown)
        self.assertIn("이제 이렇게 진행하면 돼요", markdown)
        self.assertIn("지금은 바로 AI에게 전달해도 괜찮아요.", markdown)


if __name__ == "__main__":
    unittest.main()
