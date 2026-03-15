"""Edge-case tests: guard_report with None/missing fields."""

import unittest
from dataclasses import dataclass
from typing import Any, Dict

from vibelign.core.guard_report import combine_guard


@dataclass
class FakeDoctorReport:
    score: int = 0
    level: str = "GOOD"
    stats: Dict[str, Any] = None

    def __post_init__(self):
        if self.stats is None:
            self.stats = {}

    def to_dict(self):
        return {"score": self.score, "level": self.level, "stats": self.stats}


@dataclass
class FakeExplainReport:
    risk_level: str = "LOW"

    def to_dict(self):
        return {"risk_level": self.risk_level}


class GuardNoneFieldsTest(unittest.TestCase):
    """guard_report.combine_guard edge cases."""

    def test_good_doctor_low_risk_returns_good(self):
        result = combine_guard(FakeDoctorReport(score=0), FakeExplainReport("LOW"))
        self.assertEqual(result.overall_level, "GOOD")
        self.assertFalse(result.blocked)

    def test_high_risk_explain_blocks(self):
        result = combine_guard(FakeDoctorReport(score=0), FakeExplainReport("HIGH"))
        self.assertEqual(result.overall_level, "HIGH")
        self.assertTrue(result.blocked)

    def test_unknown_risk_level_treated_as_zero(self):
        """If risk_level is a typo like 'UNKNOWN', .get() returns 0 — should not crash."""
        result = combine_guard(FakeDoctorReport(score=0), FakeExplainReport("UNKNOWN"))
        self.assertEqual(result.overall_level, "GOOD")
        self.assertFalse(result.blocked)

    def test_none_risk_level_treated_as_zero(self):
        """risk_level=None should not crash."""
        result = combine_guard(FakeDoctorReport(score=0), FakeExplainReport(risk_level=None))
        self.assertIn(result.overall_level, {"GOOD", "WARNING", "HIGH"})

    def test_empty_stats_dict(self):
        result = combine_guard(FakeDoctorReport(score=5, stats={}), FakeExplainReport("LOW"))
        self.assertIsInstance(result.recommendations, list)
        self.assertTrue(len(result.recommendations) > 0)

    def test_stats_with_oversized_entry_files(self):
        result = combine_guard(
            FakeDoctorReport(score=5, stats={"oversized_entry_files": 2}),
            FakeExplainReport("LOW"),
        )
        self.assertTrue(
            any("진입 파일" in r for r in result.recommendations)
        )

    def test_stats_with_missing_anchors(self):
        result = combine_guard(
            FakeDoctorReport(score=3, stats={"missing_anchor_files": 5}),
            FakeExplainReport("MEDIUM"),
        )
        self.assertTrue(
            any("anchor" in r for r in result.recommendations)
        )

    def test_very_high_doctor_score_blocks(self):
        """score=20 + MEDIUM(3) = 23 >= 14 → HIGH."""
        result = combine_guard(FakeDoctorReport(score=20), FakeExplainReport("MEDIUM"))
        self.assertEqual(result.overall_level, "HIGH")
        self.assertTrue(result.blocked)

    def test_summary_contains_score(self):
        result = combine_guard(FakeDoctorReport(score=7), FakeExplainReport("LOW"))
        self.assertIn("7", result.summary)


if __name__ == "__main__":
    unittest.main()
