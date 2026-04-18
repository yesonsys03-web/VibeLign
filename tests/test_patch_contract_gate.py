import unittest
from vibelign.patch.patch_contract_helpers import patch_status


class TestPatchStatusGateRelax(unittest.TestCase):
    def test_low_confidence_without_codespeak_returns_needs_clarification(self):
        result = patch_status("low", "ok", "ok", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_low_confidence_with_codespeak_returns_ready(self):
        result = patch_status("low", "ok", "ok", codespeak_generated=True)
        self.assertEqual(result, "READY")

    def test_high_confidence_returns_ready_regardless(self):
        result = patch_status("high", "ok", "ok", codespeak_generated=False)
        self.assertEqual(result, "READY")

    def test_file_not_ok_still_refused(self):
        result = patch_status("low", "missing", "ok", codespeak_generated=True)
        self.assertEqual(result, "REFUSED")

    def test_low_confidence_missing_anchor_without_codespeak(self):
        result = patch_status("low", "ok", "missing", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_low_confidence_missing_anchor_with_codespeak(self):
        """anchor가 missing이면 codespeak 여부와 무관하게 NEEDS_CLARIFICATION."""
        result = patch_status("low", "ok", "missing", codespeak_generated=True)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_medium_confidence_suggested_anchor_without_codespeak(self):
        result = patch_status("medium", "ok", "suggested", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")


from vibelign.patch.patch_contract_helpers import build_contract


class TestBuildContractCodespeakGate(unittest.TestCase):
    def _make_patch_plan(self, confidence="high", codespeak_generated=False):
        return {
            "target_file": "ok:pages/login.py",
            "target_anchor": "ok:LOGIN_HANDLE_LOGIN",
            "codespeak": "ui.component.login.fix",
            "confidence": confidence,
            "request": "로그인 에러 수정",
            "interpretation": "로그인 에러를 수정한다",
            "patch_points": {"operation": "update"},
            "clarifying_questions": [],
            "sub_intents": [],
            "codespeak_generated": codespeak_generated,
        }

    def test_build_contract_low_confidence_with_codespeak_is_ready(self):
        plan = self._make_patch_plan(confidence="low", codespeak_generated=True)
        contract = build_contract(plan)
        self.assertEqual(contract["status"], "READY")

    def test_build_contract_low_confidence_without_codespeak_is_needs_clarification(self):
        plan = self._make_patch_plan(confidence="low", codespeak_generated=False)
        contract = build_contract(plan)
        self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")


if __name__ == "__main__":
    unittest.main()
