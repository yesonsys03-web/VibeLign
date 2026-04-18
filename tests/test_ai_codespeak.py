import unittest
import importlib
from typing import cast
from unittest.mock import patch

from vibelign.core.codespeak import build_codespeak


_ai_codespeak = importlib.import_module("vibelign.core.ai_codespeak")
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
        self.assertEqual(cast(str, parsed["codespeak"]), "ui.component.progress_bar.add")

    def test_parse_codespeak_text_extracts_optional_patch_points(self):
        text = (
            '{"codespeak":"ui.component.progress_bar.add","interpretation":"ok",'
            '"confidence":"high","clarifying_questions":[],'
            '"patch_points":{"destination":"상단 메뉴","source":"progress bar"}}'
        )
        parsed = _parse_codespeak_text(text)
        self.assertIsNotNone(parsed)
        pp = parsed.get("patch_points") if parsed else None
        self.assertIsInstance(pp, dict)
        self.assertEqual(cast(dict[str, str], pp)["destination"], "상단 메뉴")

    def test_invalid_ai_codespeak_v0_is_rejected(self):
        rule_result = build_codespeak("add progress bar")
        with patch(
            "vibelign.core.ai_explain.generate_text_with_ai",
            return_value=(
                '{"codespeak":"UI.component.progress_bar.add","interpretation":"ok","confidence":"high","clarifying_questions":[]}',
                True,
            ),
        ):
            result = _ai_codespeak.enhance_codespeak_with_ai(
                "add progress bar", rule_result, quiet=True
            )
        self.assertIsNone(result)

    def test_prompt_includes_allowed_action_vocabulary(self):
        rule_result = build_codespeak("add progress bar")
        prompt = build_codespeak_ai_prompt("add progress bar", rule_result)
        for action in ("add", "remove", "update", "move", "fix", "apply", "split"):
            self.assertIn(action, prompt)

    def test_ai_codespeak_with_unknown_action_is_rejected(self):
        """AI가 ACTION_MAP에 없는 action(예: persistence_enable)을 생성하면 None 을 반환해야 한다."""
        rule_result = build_codespeak("클로드 훅 유지되지 않아. 수정해줘.")
        with patch(
            "vibelign.core.ai_explain.generate_text_with_ai",
            return_value=(
                '{"codespeak":"ui.component.hook.persistence_enable",'
                '"interpretation":"ok","confidence":"high","clarifying_questions":[]}',
                True,
            ),
        ):
            result = _ai_codespeak.enhance_codespeak_with_ai(
                "클로드 훅 유지되지 않아. 수정해줘.",
                rule_result,
                quiet=True,
            )
        self.assertIsNone(result)

    def test_ai_enhancement_rebuilds_patch_points_and_intent_ir(self):
        rule_result = build_codespeak("add progress bar")
        with patch(
            "vibelign.core.ai_explain.generate_text_with_ai",
            return_value=(
                '{"codespeak":"ui.component.progress_bar.move","interpretation":"progress bar를 다른 위치로 이동하는 요청으로 해석했습니다.","confidence":"high","clarifying_questions":[]}',
                True,
            ),
        ):
            result = _ai_codespeak.enhance_codespeak_with_ai(
                "progress bar를 상단 메뉴로 이동해줘", rule_result, quiet=True
            )
        self.assertIsNotNone(result)
        if result is None:
            self.fail("enhance_codespeak_with_ai should return an enhanced result")
        self.assertEqual(result.patch_points["operation"], "move")
        self.assertIn("상단 메뉴", result.patch_points["destination"])
        intent_ir = result.intent_ir
        if intent_ir is None:
            self.fail("AI-enhanced result should preserve rebuilt intent_ir")
        self.assertEqual(intent_ir.operation, "move")
        self.assertEqual(intent_ir.destination, result.patch_points["destination"])


if __name__ == "__main__":
    unittest.main()
