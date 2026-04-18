"""Unit tests for _apply_layer_routing (C2 part 2).

Covers the four gates and the boost/penalty arithmetic that flips
ranking when all gates pass. Uses a hand-built ProjectMapSnapshot
fixture — no sandbox, no subprocess.
"""
import unittest
from pathlib import Path

from vibelign.core.project_map import ProjectMapSnapshot


def _make_map(
    ui_modules=frozenset(),
    service_modules=frozenset(),
    core_modules=frozenset(),
    files=None,
):
    return ProjectMapSnapshot(
        schema_version=2,
        project_name="test",
        entry_files=frozenset(),
        ui_modules=ui_modules,
        core_modules=core_modules,
        service_modules=service_modules,
        large_files=frozenset(),
        file_count=0,
        generated_at=None,
        anchor_index={},
        tree=[],
        files=files or {},
    )


class LayerRoutingGateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path("/fake/root")
        self.auth = self.root / "api" / "auth.py"
        self.signup = self.root / "pages" / "signup.py"
        self.validators = self.root / "core" / "validators.py"

    def test_gate1_ui_top1_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py", "pages/login.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.signup, 10), (self.auth, 5)]
        result = _apply_layer_routing(
            candidates, ["추가", "검사"], pm, self.root
        )
        self.assertEqual(result, candidates)

    def test_gate2_mutate_verb_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["버그", "수정"], pm, self.root
        )
        self.assertEqual(result, candidates)

    def test_gate2_create_verb_fires(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["검사", "추가"], pm, self.root
        )
        self.assertNotEqual(result, candidates)
        self.assertEqual(result[0][0], self.signup)

    def test_gate3_no_ui_importer_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset(),
            service_modules=frozenset({"api/auth.py", "api/users.py"}),
            files={
                "api/auth.py": {"imported_by": ["api/users.py"]},
                "api/users.py": {"imported_by": []},
            },
        )
        users = self.root / "api" / "users.py"
        candidates = [(self.auth, 19), (users, 3)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        self.assertEqual(result, candidates)

    def test_gate4_zero_score_caller_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 0)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        self.assertEqual(result, candidates)

    def test_scoring_flips_ranking_with_expected_arithmetic(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        result_map = {path: score for path, score in result}
        self.assertEqual(result_map[self.signup], 2 + 18)  # BOOST
        self.assertEqual(result_map[self.auth], 19 - 3)    # PENALTY
        self.assertEqual(result[0][0], self.signup)


if __name__ == "__main__":
    unittest.main()
