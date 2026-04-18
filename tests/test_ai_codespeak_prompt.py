import unittest
from vibelign.core.ai_codespeak import build_codespeak_ai_prompt
from vibelign.core.codespeak import build_codespeak


class TestAICodespeakPromptWithTargeting(unittest.TestCase):
    def test_prompt_contains_file_and_anchor_when_provided(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
            target_file="pages/login.py",
            target_anchor="LOGIN_RENDER_LOGIN_ERROR",
            target_confidence="high",
            target_rationale=["login 키워드 매칭", "render_error 앵커 매칭"],
        )
        self.assertIn("pages/login.py", prompt)
        self.assertIn("LOGIN_RENDER_LOGIN_ERROR", prompt)
        self.assertNotIn("규칙 기반 해석", prompt)

    def test_prompt_falls_back_without_targeting(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
        )
        self.assertIn("규칙 기반 해석", prompt)
        self.assertNotIn("patch_suggester", prompt)

    def test_prompt_includes_rationale(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
            target_file="pages/login.py",
            target_anchor="LOGIN_RENDER_LOGIN_ERROR",
            target_confidence="high",
            target_rationale=["login 키워드 매칭"],
        )
        self.assertIn("login 키워드 매칭", prompt)


if __name__ == "__main__":
    unittest.main()
