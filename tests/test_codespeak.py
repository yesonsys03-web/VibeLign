import unittest

from vibeguard.core.codespeak import build_codespeak


class CodeSpeakTest(unittest.TestCase):
    def test_progress_bar_request_maps_to_ui_codespeak(self):
        result = build_codespeak("add progress bar")
        self.assertEqual(result.codespeak, "ui.component.progress_bar.add")
        self.assertEqual(result.confidence, "high")

    def test_unclear_request_generates_clarifying_questions(self):
        result = build_codespeak("do something")
        self.assertIn(result.confidence, {"low", "medium"})
        if result.confidence == "low":
            self.assertGreaterEqual(len(result.clarifying_questions), 1)


if __name__ == "__main__":
    unittest.main()
