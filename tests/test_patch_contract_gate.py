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


if __name__ == "__main__":
    unittest.main()
