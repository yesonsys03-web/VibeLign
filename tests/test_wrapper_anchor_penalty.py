"""Unit tests for wrapper anchor detection and penalty (C3).

Covers _is_wrapper_anchor detection logic and the scoring effect
of _WRAPPER_ANCHOR_PENALTY in choose_anchor.
"""
import unittest


class IsWrapperAnchorTest(unittest.TestCase):
    def test_single_token_prefix_of_all_siblings_is_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        self.assertTrue(_is_wrapper_anchor("SIGNUP", anchors))

    def test_multi_token_anchor_is_not_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        self.assertFalse(_is_wrapper_anchor("SIGNUP_HANDLE_SIGNUP", anchors))

    def test_single_anchor_file_has_no_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["CONFIG"]
        self.assertFalse(_is_wrapper_anchor("CONFIG", anchors))

    def test_single_token_not_in_all_siblings_is_not_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["AUTH", "AUTH_LOGIN_USER", "HELPERS_HASH"]
        self.assertFalse(_is_wrapper_anchor("AUTH", anchors))


class WrapperAnchorScoringTest(unittest.TestCase):
    def test_wrapper_penalty_lets_leaf_win_over_wrapper(self):
        """The exact add_email_domain_check scenario.

        Without C3, SIGNUP (score 0) beats SIGNUP_HANDLE_SIGNUP (score -4).
        With C3, SIGNUP gets -5 penalty → -5, so SIGNUP_HANDLE_SIGNUP (-4) wins.
        """
        from vibelign.core.patch_suggester import choose_anchor, tokenize

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        request = "회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가"
        tokens = tokenize(request)
        chosen, _ = choose_anchor(anchors, tokens, None)
        self.assertEqual(chosen, "SIGNUP_HANDLE_SIGNUP")

    def test_wrapper_penalty_does_not_regress_verb_match_winner(self):
        """change_error_msg: LOGIN_HANDLE_LOGIN (+5) must still beat LOGIN (-5)."""
        from vibelign.core.patch_suggester import choose_anchor, tokenize

        anchors = ["LOGIN", "LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN", "LOGIN_RENDER_LOGIN_ERROR"]
        request = "로그인 에러 메시지 변경 — 사용자 경험 개선"
        tokens = tokenize(request)
        chosen, _ = choose_anchor(anchors, tokens, None)
        self.assertEqual(chosen, "LOGIN_HANDLE_LOGIN")


if __name__ == "__main__":
    unittest.main()
