import unittest
import importlib


build_explain_ai_prompt = importlib.import_module(
    "vibeguard.core.ai_explain"
).build_explain_ai_prompt


class AiExplainPromptTest(unittest.TestCase):
    def test_prompt_uses_beginner_friendly_four_sections(self):
        prompt = build_explain_ai_prompt(
            {
                "source": "git",
                "risk_level": "LOW",
                "summary": "최근 변경이 있습니다.",
                "what_changed": ["login.py 수정"],
                "why_it_matters": ["로그인 흐름이 달라질 수 있습니다."],
                "what_to_do_next": "vib guard 를 실행하세요.",
                "files": [{"path": "login.py", "status": "modified", "kind": "logic"}],
            }
        )
        self.assertIn("## 1. 한 줄 요약", prompt)
        self.assertIn("## 4. 다음 할 일", prompt)
        self.assertIn("중학생도 이해할 수 있는 쉬운 말", prompt)

    def test_prompt_tolerates_partial_file_entries(self):
        prompt = build_explain_ai_prompt(
            {
                "source": "git",
                "risk_level": "LOW",
                "summary": "최근 변경이 있습니다.",
                "what_changed": [],
                "why_it_matters": [],
                "what_to_do_next": "확인하세요.",
                "files": [{"path": "login.py"}, "bad-item"],
            }
        )
        self.assertIn("login.py", prompt)


if __name__ == "__main__":
    unittest.main()
