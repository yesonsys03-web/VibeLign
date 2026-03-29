import unittest

from vibelign.core.codespeak import build_codespeak, build_codespeak_result
from vibelign.core.request_normalizer import normalize_user_request


class CodeSpeakTest(unittest.TestCase):
    def test_progress_bar_request_maps_to_ui_codespeak(self):
        result = build_codespeak("add progress bar")
        self.assertEqual(result.codespeak, "ui.component.progress_bar.add")
        self.assertEqual(result.confidence, "high")
        intent_ir = result.intent_ir
        if intent_ir is None:
            self.fail("build_codespeak should populate intent_ir")
        self.assertEqual(intent_ir.operation, "add")
        self.assertEqual(intent_ir.to_patch_points()["operation"], "add")

    def test_unclear_request_generates_clarifying_questions(self):
        result = build_codespeak("do something")
        self.assertIn(result.confidence, {"low", "medium"})
        if result.confidence == "low":
            self.assertGreaterEqual(len(result.clarifying_questions), 1)

    def test_build_codespeak_result_keeps_codespeak_action_authoritative(self):
        result = build_codespeak_result(
            "progress bar를 상단 메뉴로 이동해줘",
            codespeak="ui.component.progress_bar.update",
            interpretation="progress bar를 업데이트하는 요청으로 해석했습니다.",
            confidence="medium",
            clarifying_questions=[],
        )
        self.assertIsNotNone(result)
        if result is None:
            self.fail("build_codespeak_result should return a codespeak result")
        self.assertEqual(result.codespeak, "ui.component.progress_bar.update")
        self.assertEqual(result.action, "update")
        intent_ir = result.intent_ir
        if intent_ir is None:
            self.fail("build_codespeak_result should populate intent_ir")
        self.assertEqual(intent_ir.action, "update")
        self.assertEqual(intent_ir.operation, "move")

    def test_build_codespeak_detects_multi_intent_and_clarifies(self):
        result = build_codespeak("로그인 버튼 색 바꿔줘 그리고 progress bar 추가해줘")
        self.assertEqual(result.confidence, "low")
        self.assertEqual(
            result.sub_intents,
            ["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
        )
        self.assertTrue(
            any("한 번에 한 가지 변경" in item for item in result.clarifying_questions)
        )

    def test_normalize_user_request_splits_numbered_newline_list(self):
        raw = "요청:\n1. 로그인 버튼 색 바꿔줘\n2. progress bar 추가해줘"
        _s, parts = normalize_user_request(raw)
        self.assertEqual(
            parts,
            ["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
        )

    def test_normalize_user_request_keeps_comma_phrase_single_intent(self):
        raw = "버튼을 빨강, 파랑 톤으로 바꿔줘"
        _s, parts = normalize_user_request(raw)
        self.assertEqual(len(parts), 1)

    def test_degree_adverbs_remain_in_patch_object_candidates(self):
        result = build_codespeak("크기를 동일하게 맞춰줘")
        self.assertIn("동일", result.patch_points.get("object", ""))


if __name__ == "__main__":
    unittest.main()
