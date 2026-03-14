import unittest
import importlib

from vibeguard.core.codespeak import build_codespeak


_ai_codespeak = importlib.import_module("vibeguard.core.ai_codespeak")
_parse_codespeak_text = _ai_codespeak._parse_codespeak_text
build_codespeak_ai_prompt = _ai_codespeak.build_codespeak_ai_prompt


class AiCodeSpeakTest(unittest.TestCase):
    def test_prompt_preserves_codespeak_contract(self):
        rule_result = build_codespeak("add progress bar")
        prompt = build_codespeak_ai_prompt("add progress bar", rule_result)
        self.assertIn("layer.target.subject.action", prompt)
        self.assertIn("ui.component.progress_bar.add", prompt)

    def test_parse_codespeak_text_extracts_json_object(self):
        text = 'before {"codespeak":"ui.component.progress_bar.add","interpretation":"ok","confidence":"high","clarifying_questions":[]} after'
        parsed = _parse_codespeak_text(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["codespeak"], "ui.component.progress_bar.add")


if __name__ == "__main__":
    unittest.main()
