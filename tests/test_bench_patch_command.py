"""In-process unit tests for `vib bench --patch` runner internals.

We mock `_ai_select_file` so tests never hit the network. The real
end-to-end smoke (actual `vib bench --patch` invocation) is done
manually in Task 8 of the plan and is not part of the automated suite.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

from vibelign.commands.vib_bench_cmd import (
    _compute_files_ok,
    _compute_anchor_ok,
    _compute_recall_at_3,
)


class MetricHelpersTest(unittest.TestCase):
    def test_files_ok_matches_any_correct_file(self):
        self.assertTrue(_compute_files_ok("pages/login.py", ["pages/login.py"]))
        self.assertTrue(
            _compute_files_ok(
                "api/auth.py", ["api/auth.py", "pages/profile.py"]
            )
        )

    def test_files_ok_rejects_wrong_file(self):
        self.assertFalse(
            _compute_files_ok("core/validators.py", ["pages/login.py"])
        )

    def test_anchor_ok_returns_none_when_scenario_has_no_anchor(self):
        self.assertIsNone(_compute_anchor_ok("ANY_ANCHOR", None))

    def test_anchor_ok_true_on_match(self):
        self.assertTrue(
            _compute_anchor_ok("LOGIN_HANDLE_LOGIN", "LOGIN_HANDLE_LOGIN")
        )

    def test_anchor_ok_false_on_mismatch(self):
        self.assertFalse(
            _compute_anchor_ok("LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN")
        )

    def test_recall_at_3_true_when_correct_in_top3(self):
        # candidates is list[tuple[str, int]] of relpath -> score,
        # already sorted descending.
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
            ("core/database.py", 4),
        ]
        self.assertTrue(_compute_recall_at_3(candidates, ["api/auth.py"]))
        self.assertTrue(_compute_recall_at_3(candidates, ["pages/login.py"]))

    def test_recall_at_3_false_when_correct_below_top3(self):
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
            ("core/database.py", 4),
            ("core/validators.py", 2),
        ]
        self.assertFalse(_compute_recall_at_3(candidates, ["core/validators.py"]))

    def test_recall_at_3_true_if_any_correct_file_in_top3(self):
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
        ]
        self.assertTrue(
            _compute_recall_at_3(
                candidates, ["core/validators.py", "pages/login.py"]
            )
        )


if __name__ == "__main__":
    unittest.main()
