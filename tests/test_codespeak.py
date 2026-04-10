import tempfile
import unittest
from pathlib import Path

from vibelign.core.codespeak import (
    _subject_from_anchor,
    build_codespeak,
    build_codespeak_result,
)
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

    def test_fix_imperative_overrides_other_action_words(self):
        """'수정해줘'로 끝나는 요청은 이전에 등장한 다른 action 단어(enable 등)를
        덮어 action=fix 가 돼야 한다."""
        result = build_codespeak(
            "클로드 훅 enable 시키고 다른 메뉴 갔다 오면 유지되지 않아. 수정해줘."
        )
        self.assertEqual(result.action, "fix")

    def test_fix_imperative_variants(self):
        for request in ("버튼 고쳐줘", "레이아웃 고쳐", "please fix the layout"):
            with self.subTest(request=request):
                result = build_codespeak(request)
                self.assertEqual(result.action, "fix")

    def test_subject_from_anchor_strips_boundaries(self):
        self.assertEqual(
            _subject_from_anchor("CLAUDE_HOOK_TOGGLE_START"),
            "claude_hook_toggle",
        )
        self.assertEqual(
            _subject_from_anchor("CLAUDE_HOOK_TOGGLE_END"),
            "claude_hook_toggle",
        )
        self.assertEqual(
            _subject_from_anchor("CLAUDE_HOOK_TOGGLE"),
            "claude_hook_toggle",
        )

    def test_build_codespeak_uses_anchor_derived_english_subject(self):
        """target_anchor 가 있으면 _ko_to_slug 단어장 없이 영문 subject 를 유도해야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / "vibelign-gui" / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "ClaudeHookToggle.tsx").write_text(
                "// === ANCHOR: CLAUDE_HOOK_TOGGLE_START ===\n"
                "export default function ClaudeHookToggle() {\n"
                "  return <div>claude hook toggle</div>;\n"
                "}\n"
                "// === ANCHOR: CLAUDE_HOOK_TOGGLE_END ===\n",
                encoding="utf-8",
            )
            result = build_codespeak(
                "클로드 훅 유지되지 않아. 수정해줘.", root=root
            )
        # 단어장에 없는 한글 토큰이 subject 에 남으면 안 된다.
        self.assertNotRegex(result.subject, r"[가-힣]")
        # anchor 가 잡혔다면 anchor-derived subject 를 써야 한다.
        if result.target_anchor and result.target_anchor != "[먼저 앵커를 추가하세요]":
            self.assertEqual(result.subject, "claude_hook_toggle")
        # codespeak 전체에도 한글이 남아 있으면 안 된다.
        self.assertNotRegex(result.codespeak, r"[가-힣]")


if __name__ == "__main__":
    unittest.main()
