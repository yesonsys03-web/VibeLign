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


class MeasureAndDiffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from vibelign.commands.bench_fixtures import prepare_patch_sandbox

        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = prepare_patch_sandbox(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_measure_returns_full_result_dict(self):
        """_measure_patch_accuracy returns per-scenario metrics for both modes."""
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        self.assertIn("scenarios", result)
        self.assertIn("totals", result)
        for sid in [
            "change_error_msg",
            "add_email_domain_check",
            "fix_login_lock_bug",
            "add_bio_length_limit",
            "add_password_change",
        ]:
            self.assertIn(sid, result["scenarios"], f"missing scenario {sid}")
            for mode in ("det", "ai"):
                self.assertIn(mode, result["scenarios"][sid])
                entry = result["scenarios"][sid][mode]
                self.assertIn("files_ok", entry)
                self.assertIn("anchor_ok", entry)
                self.assertIn("recall_at_3", entry)
                self.assertIsInstance(entry["files_ok"], bool)

    def test_add_password_change_anchor_ok_is_none(self):
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        self.assertIsNone(
            result["scenarios"]["add_password_change"]["det"]["anchor_ok"]
        )
        self.assertIsNone(
            result["scenarios"]["add_password_change"]["ai"]["anchor_ok"]
        )

    def test_totals_string_format(self):
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        det_totals = result["totals"]["det"]
        self.assertRegex(det_totals["files_ok"], r"^\d+/13$")
        self.assertRegex(det_totals["anchor_ok"], r"^\d+/12$")
        self.assertRegex(det_totals["recall_at_3"], r"^\d+/13$")


class BaselineDiffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = {
            "scenarios": {
                "change_error_msg": {
                    "det": {"files_ok": True, "anchor_ok": True, "recall_at_3": True},
                    "ai":  {"files_ok": True, "anchor_ok": True, "recall_at_3": True},
                },
            },
            "totals": {
                "det": {"files_ok": "1/1", "anchor_ok": "1/1", "recall_at_3": "1/1"},
                "ai":  {"files_ok": "1/1", "anchor_ok": "1/1", "recall_at_3": "1/1"},
            },
        }

    def test_no_diff_when_identical(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        current = json.loads(json.dumps(self.baseline))
        diff = _diff_against_baseline(current, self.baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(diff["improvements"], [])

    def test_regression_detected(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        current = json.loads(json.dumps(self.baseline))
        current["scenarios"]["change_error_msg"]["det"]["files_ok"] = False
        diff = _diff_against_baseline(current, self.baseline)
        self.assertEqual(len(diff["regressions"]), 1)
        self.assertEqual(
            diff["regressions"][0],
            {
                "scenario": "change_error_msg",
                "mode": "det",
                "metric": "files_ok",
                "was": True,
                "now": False,
            },
        )
        self.assertEqual(diff["improvements"], [])

    def test_improvement_detected(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        baseline = json.loads(json.dumps(self.baseline))
        baseline["scenarios"]["change_error_msg"]["ai"]["recall_at_3"] = False
        current = json.loads(json.dumps(self.baseline))
        diff = _diff_against_baseline(current, baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(len(diff["improvements"]), 1)

    def test_null_anchor_ok_treated_as_na_not_regression(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        baseline = {
            "scenarios": {
                "add_password_change": {
                    "det": {"files_ok": False, "anchor_ok": None, "recall_at_3": True},
                    "ai":  {"files_ok": False, "anchor_ok": None, "recall_at_3": True},
                },
            },
            "totals": {
                "det": {"files_ok": "0/1", "anchor_ok": "0/0", "recall_at_3": "1/1"},
                "ai":  {"files_ok": "0/1", "anchor_ok": "0/0", "recall_at_3": "1/1"},
            },
        }
        current = json.loads(json.dumps(baseline))
        diff = _diff_against_baseline(current, baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(diff["improvements"], [])


class ExitCodeTest(unittest.TestCase):
    """End-to-end (in-process) exit-code semantics for _run_patch_accuracy."""

    @classmethod
    def setUpClass(cls) -> None:
        # Ensure baseline exists for the clean-run test.
        from vibelign.commands.vib_bench_cmd import PATCH_BASELINE_PATH

        cls.baseline_path = PATCH_BASELINE_PATH
        cls._backup = (
            PATCH_BASELINE_PATH.read_text(encoding="utf-8")
            if PATCH_BASELINE_PATH.exists()
            else None
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._backup is not None:
            cls.baseline_path.write_text(cls._backup, encoding="utf-8")

    def test_clean_run_exits_zero(self):
        from vibelign.commands.vib_bench_cmd import _run_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            # First run with --update-baseline to establish a matching baseline.
            code_update = _run_patch_accuracy(
                update_baseline=True, as_json=True
            )
            # Second run without --update-baseline should be clean.
            code_clean = _run_patch_accuracy(
                update_baseline=False, as_json=True
            )

        self.assertEqual(code_update, 0)
        self.assertEqual(code_clean, 0)

    def test_regression_exits_one(self):
        from vibelign.commands.vib_bench_cmd import (
            PATCH_BASELINE_PATH,
            _run_patch_accuracy,
        )

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            # Seed a known-good baseline.
            _ = _run_patch_accuracy(update_baseline=True, as_json=True)
            # Corrupt the baseline: force every metric to True so every
            # failing scenario becomes a regression.
            poisoned = json.loads(
                PATCH_BASELINE_PATH.read_text(encoding="utf-8")
            )
            for sid in poisoned["scenarios"]:
                for mode in ("det", "ai"):
                    for metric in ("files_ok", "anchor_ok", "recall_at_3"):
                        if poisoned["scenarios"][sid][mode][metric] is not None:
                            poisoned["scenarios"][sid][mode][metric] = True
            PATCH_BASELINE_PATH.write_text(
                json.dumps(poisoned, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            code = _run_patch_accuracy(update_baseline=False, as_json=True)

        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
