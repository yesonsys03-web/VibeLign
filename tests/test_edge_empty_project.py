"""Edge-case tests: empty project / no source files scenarios."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.codespeak import build_codespeak, tokenize_request
from vibelign.core.doctor_v2 import analyze_project_v2, _anchor_coverage
from vibelign.core.patch_suggester import suggest_patch, tokenize


class EmptyProjectDoctorTest(unittest.TestCase):
    """doctor_v2 with zero source files."""

    def test_anchor_coverage_returns_100_for_empty_project(self):
        with patch("vibelign.core.doctor_v2.iter_source_files", return_value=[]):
            result = _anchor_coverage(Path("/fake"))
        self.assertEqual(result, 100)

    def test_analyze_empty_project_returns_safe_status(self):
        """Empty project should not crash and should produce a valid report."""
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_project_v2(Path(tmp))
            self.assertIsInstance(report.project_score, int)
            self.assertIn(report.status, {"Safe", "Good", "Caution", "Risky", "High Risk"})
            self.assertIsInstance(report.issues, list)
            self.assertIsInstance(report.recommended_actions, list)


class EmptyProjectPatchTest(unittest.TestCase):
    """patch_suggester with zero source files."""

    def test_suggest_patch_no_source_files(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            result = suggest_patch(Path(tmp), "add progress bar")
        self.assertEqual(result.target_file, "[소스 파일 없음]")
        self.assertEqual(result.confidence, "low")

    def test_suggest_patch_empty_request(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "hello.py"
            p.write_text("print('hi')\n")
            result = suggest_patch(Path(tmp), "")
        self.assertEqual(result.confidence, "low")
        self.assertIsInstance(result.target_file, str)


class EmptyRequestCodeSpeakTest(unittest.TestCase):
    """codespeak with empty or special-character-only requests."""

    def test_empty_request_returns_low_confidence(self):
        result = build_codespeak("")
        self.assertEqual(result.confidence, "low")
        self.assertIsInstance(result.codespeak, str)
        self.assertTrue(len(result.clarifying_questions) > 0)

    def test_special_chars_only_returns_low_confidence(self):
        result = build_codespeak("!@#$%^&*()")
        self.assertEqual(result.confidence, "low")

    def test_tokenize_empty_string(self):
        self.assertEqual(tokenize_request(""), [])

    def test_tokenize_special_chars(self):
        self.assertEqual(tokenize_request("!@#$%"), [])

    def test_korean_only_request_returns_low_confidence(self):
        """Korean-only text has no Latin tokens, so confidence should be low."""
        result = build_codespeak("진행 표시바 추가해줘")
        self.assertEqual(result.confidence, "low")
        self.assertTrue(len(result.clarifying_questions) > 0)

    def test_patch_tokenize_empty(self):
        self.assertEqual(tokenize(""), [])

    def test_patch_tokenize_special(self):
        self.assertEqual(tokenize("!!!"), [])


if __name__ == "__main__":
    unittest.main()
