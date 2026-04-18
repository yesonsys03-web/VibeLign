"""Edge-case tests: patch_suggester and codespeak with unusual inputs."""

import tempfile
import unittest
from pathlib import Path

from vibelign.core.codespeak import (
    build_codespeak,
    parse_codespeak_v0,
    is_valid_codespeak_v0,
)
from vibelign.core.patch_suggester import (
    suggest_patch,
    score_path,
    choose_anchor,
    choose_suggested_anchor,
    resolve_target_for_role,
)


class CodeSpeakParsingTest(unittest.TestCase):
    """parse_codespeak_v0 edge cases."""

    def test_valid_codespeak(self):
        result = parse_codespeak_v0("ui.component.progress_bar.add")
        self.assertIsNotNone(result)
        parsed = result
        if parsed is None:
            self.fail("parse_codespeak_v0 should return a parsed mapping")
        self.assertEqual(parsed["layer"], "ui")
        self.assertEqual(parsed["action"], "add")

    def test_invalid_format_missing_parts(self):
        self.assertIsNone(parse_codespeak_v0("ui.component.add"))

    def test_empty_string(self):
        self.assertIsNone(parse_codespeak_v0(""))

    def test_spaces_around(self):
        result = parse_codespeak_v0("  ui.component.foo.add  ")
        self.assertIsNotNone(result)

    def test_uppercase_rejected(self):
        self.assertIsNone(parse_codespeak_v0("UI.Component.Foo.Add"))

    def test_numbers_allowed(self):
        result = parse_codespeak_v0("ui.v2.progress_bar.add")
        self.assertIsNotNone(result)

    def test_is_valid_codespeak_v0_true(self):
        self.assertTrue(is_valid_codespeak_v0("core.patch.request.update"))

    def test_is_valid_codespeak_v0_false(self):
        self.assertFalse(is_valid_codespeak_v0("not valid"))


class CodeSpeakBuildTest(unittest.TestCase):
    """build_codespeak with various request types."""

    def test_english_ui_request(self):
        result = build_codespeak("add progress bar to the main window")
        self.assertEqual(result.layer, "ui")
        self.assertEqual(result.action, "add")
        self.assertEqual(result.confidence, "high")

    def test_fix_request(self):
        result = build_codespeak("fix the login bug")
        self.assertEqual(result.action, "fix")

    def test_remove_request(self):
        result = build_codespeak("remove the old sidebar")
        self.assertEqual(result.action, "remove")

    def test_very_long_request(self):
        """Very long request should not crash."""
        request = "add " + "very " * 500 + "important feature"
        result = build_codespeak(request)
        self.assertIsInstance(result.codespeak, str)
        self.assertIsInstance(result.confidence, str)

    def test_mixed_english_korean(self):
        """Request with both English and Korean words."""
        result = build_codespeak("button 추가해줘")
        # "button" should be detected
        self.assertEqual(result.layer, "ui")


class PatchSuggesterScoreTest(unittest.TestCase):
    """score_path edge cases."""

    def test_score_init_file_low_priority(self):
        path = Path("__init__.py")
        score, rationale = score_path(path, ["test"], "__init__.py")
        self.assertTrue(score < 0)

    def test_score_test_file_low_priority(self):
        path = Path("tests/test_foo.py")
        score, rationale = score_path(path, ["foo"], "tests/test_foo.py")
        # Should have test-dir penalty
        self.assertTrue(any("test" in r for r in rationale))

    def test_score_with_no_tokens(self):
        path = Path("main.py")
        score, rationale = score_path(path, [], "main.py")
        self.assertIsInstance(score, int)

    def test_resolve_target_for_role_returns_structured_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: NAV_TABS_START ===\n"
                "export default function App() { return <div>nav-tabs</div>; }\n"
                "// === ANCHOR: NAV_TABS_END ===\n",
                encoding="utf-8",
            )
            resolution = resolve_target_for_role(
                root, "상단 메뉴 CHECKPOINTS", role="destination"
            )
            if resolution is None:
                self.fail("resolve_target_for_role should return a structured object")
            self.assertEqual(resolution.role, "destination")
            self.assertEqual(resolution.target_file, "vibelign-gui/src/App.tsx")


class ChooseAnchorTest(unittest.TestCase):
    """choose_anchor and choose_suggested_anchor edge cases."""

    def test_no_anchors(self):
        anchor, rationale = choose_anchor([], ["test"])
        self.assertEqual(anchor, "[먼저 앵커를 추가하세요]")

    def test_single_anchor(self):
        anchor, rationale = choose_anchor(["MY_MODULE"], ["test"])
        self.assertEqual(anchor, "MY_MODULE")

    def test_best_matching_anchor(self):
        anchor, rationale = choose_anchor(
            ["AUTH_LOGIC", "UI_RENDER", "DATA_STORE"], ["auth", "login"]
        )
        self.assertEqual(anchor, "AUTH_LOGIC")

    def test_no_suggested_anchors(self):
        anchor, rationale = choose_suggested_anchor([], ["test"])
        self.assertIsNone(anchor)

    def test_weak_suggested_anchor_rejected(self):
        """Suggested anchor with no keyword match should be rejected (score <= 0)."""
        anchor, rationale = choose_suggested_anchor(
            ["_internal_helper"], ["progress", "bar"]
        )
        self.assertIsNone(anchor)


class PatchSuggesterIntegrationTest(unittest.TestCase):
    """suggest_patch integration with real temp directories."""

    def test_project_with_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "app.py").write_text("def main(): pass\n")
            result = suggest_patch(Path(tmp), "add feature")
        self.assertEqual(result.target_file, "app.py")
        self.assertIn(result.confidence, {"low", "medium", "high"})

    def test_project_prefers_matching_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "auth.py").write_text("def login(): pass\n")
            (Path(tmp) / "utils.py").write_text("def helper(): pass\n")
            result = suggest_patch(Path(tmp), "fix login auth bug")
        self.assertEqual(result.target_file, "auth.py")

    def test_project_with_anchored_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "worker.py").write_text(
                "# === ANCHOR: WORKER_START ===\n"
                "def process(): pass\n"
                "# === ANCHOR: WORKER_END ===\n"
            )
            result = suggest_patch(Path(tmp), "update worker process")
        self.assertEqual(result.target_file, "worker.py")
        self.assertNotEqual(result.target_anchor, "[먼저 앵커를 추가하세요]")


if __name__ == "__main__":
    unittest.main()
