"""Unit test for score_candidates: prove behavior-preserving extraction.

score_candidates should return the same file ordering that suggest_patch
uses internally. The guarantee we check: suggest_patch's target_file
appears as score_candidates' top-1 (same ranking loop, same inputs).

Note: suggest_patch invokes `_ai_select_file` whenever deterministic
confidence is "low" — even under `use_ai=False`. To compare raw ranking
cleanly, we mock `_ai_select_file` to return None, letting the
deterministic top-1 flow through untouched.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

from vibelign.commands.bench_fixtures import prepare_patch_sandbox
from vibelign.core.patch_suggester import score_candidates, suggest_patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = REPO_ROOT / "tests" / "benchmark" / "scenarios.json"


class ScoreCandidatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = prepare_patch_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = json.load(fh)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_top1_matches_suggest_patch_target_file(self):
        for sc in self.scenarios:
            with self.subTest(scenario=sc["id"]):
                candidates = score_candidates(self.sandbox, sc["request"])
                self.assertGreater(len(candidates), 0)
                top1_path, _top1_score = candidates[0]
                top1_rel = str(top1_path.relative_to(self.sandbox)).replace("\\", "/")

                with mock_patch(
                    "vibelign.core.patch_suggester._ai_select_file",
                    return_value=None,
                ):
                    det_result = suggest_patch(
                        self.sandbox, sc["request"], use_ai=False
                    )
                self.assertEqual(
                    top1_rel,
                    det_result.target_file,
                    f"score_candidates top-1 ({top1_rel}) must match "
                    f"suggest_patch target_file ({det_result.target_file}) "
                    f"for scenario {sc['id']}",
                )

    def test_scores_are_monotonically_non_increasing(self):
        sc = self.scenarios[0]
        candidates = score_candidates(self.sandbox, sc["request"])
        scores = [score for _path, score in candidates]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(
                scores[i],
                scores[i + 1],
                f"score_candidates must be sorted descending: "
                f"index {i}={scores[i]} < {i+1}={scores[i+1]}",
            )


if __name__ == "__main__":
    unittest.main()
