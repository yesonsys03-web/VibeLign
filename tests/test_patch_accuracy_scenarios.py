import json
import tempfile
import unittest
from pathlib import Path

from vibelign.commands.bench_fixtures import (
    PINNED_INTENTS as _PINNED_INTENTS,
    prepare_patch_sandbox as _prepare_sandbox,
)
from vibelign.core.patch_suggester import suggest_patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = REPO_ROOT / "tests" / "benchmark" / "scenarios.json"


# Backwards-compat aliases retained in case anything else imports them.
__all__ = ["_PINNED_INTENTS", "_prepare_sandbox"]


class PatchAccuracyScenarioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = _prepare_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = {s["id"]: s for s in json.load(fh)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _run(self, scenario_id: str, *, use_ai: bool = False):
        sc = self.scenarios[scenario_id]
        return suggest_patch(self.sandbox, sc["request"], use_ai=use_ai)

    def test_change_error_msg_selects_handle_login(self):
        result = self._run("change_error_msg")
        self.assertEqual(result.target_file, "pages/login.py")
        self.assertEqual(result.target_anchor, "LOGIN_HANDLE_LOGIN")

    def test_fix_login_lock_bug_selects_auth_login_user(self):
        result = self._run("fix_login_lock_bug")
        self.assertEqual(result.target_file, "api/auth.py")
        self.assertEqual(result.target_anchor, "AUTH_LOGIN_USER")

    def test_add_bio_length_limit_selects_profile_update(self):
        result = self._run("add_bio_length_limit")
        self.assertEqual(result.target_file, "pages/profile.py")
        self.assertEqual(result.target_anchor, "PROFILE_HANDLE_PROFILE_UPDATE")

    def test_add_email_domain_check_routes_to_signup_page(self):
        """C2 regression guard: layer routing must flip auth→signup.

        Without C2, score_candidates ranks api/auth.py top1 via the
        AUTH_REGISTER_USER anchor match. C2's layer-routing post-processor
        promotes pages/signup.py (a ui-layer caller of auth) because:
          - top1 (api/auth.py) is classified as "service" (not "ui")
          - request verb is CREATE ("검사 추가")
          - pages/signup.py is in api/auth.py's imported_by and ui-classified
          - pages/signup.py has positive base score from path-token match

        The anchor-level resolution inside signup.py is a separate problem
        (C2 is a file-routing fix, not an anchor-picker fix), so we only
        assert that target_anchor is *some* SIGNUP-family anchor.
        """
        result = self._run("add_email_domain_check")
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")

    def test_add_email_domain_check_ai_mode_also_routes_to_signup(self):
        """C6 deference passes det result through when confidence is high."""
        result = self._run("add_email_domain_check", use_ai=True)
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")

    # --- Scenario expansion (2026-04-12) ---

    def test_reduce_max_login_attempts_selects_config(self):
        result = self._run("reduce_max_login_attempts")
        self.assertEqual(result.target_file, "config.py")
        self.assertEqual(result.target_anchor, "CONFIG")

    def test_add_special_char_requirement_selects_validators(self):
        result = self._run("add_special_char_requirement")
        self.assertEqual(result.target_file, "core/validators.py")
        self.assertEqual(result.target_anchor, "VALIDATORS_VALIDATE_PASSWORD")

    def test_remove_password_confirm_selects_signup(self):
        result = self._run("remove_password_confirm")
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")

    def test_hide_email_in_profile_selects_users_api(self):
        result = self._run("hide_email_in_profile")
        self.assertEqual(result.target_file, "api/users.py")
        self.assertEqual(result.target_anchor, "USERS_GET_USER_PROFILE")

    def test_change_server_port_selects_app(self):
        result = self._run("change_server_port")
        self.assertEqual(result.target_file, "app.py")
        self.assertEqual(result.target_anchor, "APP_MAIN")

    def test_change_signup_button_label_selects_render_form(self):
        result = self._run("change_signup_button_label")
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_RENDER_SIGNUP_FORM")

    def test_add_login_form_placeholder_kr_selects_render_form(self):
        result = self._run("add_login_form_placeholder_kr")
        self.assertEqual(result.target_file, "pages/login.py")
        self.assertEqual(result.target_anchor, "LOGIN_RENDER_LOGIN_FORM")

    def test_add_email_to_editable_fields_selects_render_profile(self):
        result = self._run("add_email_to_editable_fields")
        self.assertEqual(result.target_file, "pages/profile.py")
        self.assertEqual(result.target_anchor, "PROFILE_RENDER_PROFILE")


class TestAIDeference(unittest.TestCase):
    """`--ai` (use_ai=True) must NOT override a high-confidence deterministic pick.

    C1 (verb-aware scoring) pushes the correct anchor to top-1 with `high`
    confidence on `add_bio_length_limit`. The pre-C6 code called
    `_ai_select_file` unconditionally when `use_ai=True`, and the AI then
    routed the request to `core/validators.py` (a validation utility), undoing
    C1's gain. C6 adds a deference rule: when deterministic confidence is
    `high`, the AI selector is skipped entirely.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = _prepare_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = {s["id"]: s for s in json.load(fh)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_high_confidence_deterministic_result_is_preserved_under_ai(self):
        """With use_ai=True, a high-confidence deterministic pick must survive.

        Guarantee via mock: if the deference rule works, `_ai_select_file`
        is NEVER invoked on this scenario. We make the mock raise on call —
        any invocation fails the test.
        """
        from unittest.mock import patch as mock_patch

        sc = self.scenarios["add_bio_length_limit"]

        def _fail_if_called(*args, **kwargs):
            raise AssertionError(
                "_ai_select_file was called despite high-confidence deterministic pick"
            )

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            side_effect=_fail_if_called,
        ):
            result = suggest_patch(self.sandbox, sc["request"], use_ai=True)

        self.assertEqual(result.target_file, "pages/profile.py")
        self.assertEqual(result.target_anchor, "PROFILE_HANDLE_PROFILE_UPDATE")
        self.assertEqual(result.confidence, "high")

    def test_low_confidence_still_invokes_ai_when_flag_set(self):
        """Low-confidence path must still call the AI selector.

        The deference rule only applies to `high` confidence. This guards
        against an over-broad fix that turns `--ai` into a no-op. With
        pinned intents `fix_login_lock_bug` is the only scenario whose
        deterministic run produces `low` confidence.
        """
        from unittest.mock import patch as mock_patch

        sc = self.scenarios["fix_login_lock_bug"]
        precheck = suggest_patch(self.sandbox, sc["request"], use_ai=False)
        self.assertEqual(
            precheck.confidence, "low",
            "test premise broken: fix_login_lock_bug must be low confidence "
            "under the pinned-intent sandbox for this guard to be meaningful",
        )

        called = {"count": 0}

        def _record(*args, **kwargs):
            called["count"] += 1
            return None  # let suggest_patch fall back to deterministic pick

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            side_effect=_record,
        ):
            _ = suggest_patch(self.sandbox, sc["request"], use_ai=True)

        self.assertGreaterEqual(
            called["count"], 1,
            "AI selector must be called on low-confidence `fix_login_lock_bug`",
        )


if __name__ == "__main__":
    unittest.main()
