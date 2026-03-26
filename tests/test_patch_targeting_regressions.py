import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.patch_suggester import choose_anchor, suggest_patch


class PatchTargetingRegressionTest(unittest.TestCase):
    def _write_project_map(self, root: Path) -> None:
        meta_dir = root / ".vibelign"
        meta_dir.mkdir(exist_ok=True)
        (meta_dir / "project_map.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "project_name": root.name,
                    "entry_files": [],
                    "ui_modules": ["vibelign/commands/install_guide_cmd.py"],
                    "core_modules": [],
                    "service_modules": [],
                    "large_files": [],
                    "file_count": 2,
                    "anchor_index": {
                        "vibelign/commands/install_guide_cmd.py": [
                            "INSTALL_GUIDE_CMD",
                            "INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE",
                        ],
                        "vibelign-gui/src/pages/Home.tsx": [
                            "HOME",
                            "FUNCTION_NAME",
                            "NAME",
                        ],
                    },
                    "files": {
                        "vibelign/commands/install_guide_cmd.py": {
                            "category": "ui",
                            "anchors": [
                                "INSTALL_GUIDE_CMD",
                                "INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE",
                            ],
                            "line_count": 120,
                        },
                        "vibelign-gui/src/pages/Home.tsx": {
                            "category": "ui",
                            "anchors": ["HOME", "FUNCTION_NAME", "NAME"],
                            "line_count": 500,
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (meta_dir / "anchor_index.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "anchors": {},
                    "files": {
                        "vibelign/commands/install_guide_cmd.py": {
                            "anchors": [
                                "INSTALL_GUIDE_CMD",
                                "INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE",
                            ],
                            "suggested_anchors": [],
                        },
                        "vibelign-gui/src/pages/Home.tsx": {
                            "anchors": ["HOME", "FUNCTION_NAME", "NAME"],
                            "suggested_anchors": [],
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_files(self, root: Path) -> None:
        install_guide = root / "vibelign/commands/install_guide_cmd.py"
        install_guide.parent.mkdir(parents=True, exist_ok=True)
        install_guide.write_text(
            "# === ANCHOR: INSTALL_GUIDE_CMD_START ===\n"
            "def run_install_guide():\n"
            "    return 'install guide'\n"
            "# === ANCHOR: INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE_START ===\n"
            "def render_install_steps():\n"
            "    return 'guide'\n"
            "# === ANCHOR: INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE_END ===\n"
            "# === ANCHOR: INSTALL_GUIDE_CMD_END ===\n",
            encoding="utf-8",
        )
        home = root / "vibelign-gui/src/pages/Home.tsx"
        home.parent.mkdir(parents=True, exist_ok=True)
        home.write_text(
            "// === ANCHOR: HOME_START ===\n"
            "export function HomePage() {\n"
            "  return <div>Home screen version</div>;\n"
            "}\n"
            "// === ANCHOR: HOME_END ===\n"
            "// === ANCHOR: FUNCTION_NAME_START ===\n"
            "const functionName = 'HomePage';\n"
            "// === ANCHOR: FUNCTION_NAME_END ===\n"
            "// === ANCHOR: NAME_START ===\n"
            "const name = 'home';\n"
            "// === ANCHOR: NAME_END ===\n",
            encoding="utf-8",
        )

    def test_gui_home_request_prefers_home_page_over_install_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_project_map(root)
            self._write_files(root)

            result = suggest_patch(
                root,
                "바이브라인 gui 버전 실행하면 홈화면에 바이브라인 버전 표시해줘",
            )

            self.assertEqual(result.target_file, "vibelign-gui/src/pages/Home.tsx")
            self.assertEqual(result.target_anchor, "HOME")

    def test_install_guide_request_still_prefers_install_guide_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_project_map(root)
            self._write_files(root)

            result = suggest_patch(root, "설치 가이드 문구를 수정해줘")

            self.assertEqual(
                result.target_file, "vibelign/commands/install_guide_cmd.py"
            )
            self.assertEqual(result.target_anchor, "INSTALL_GUIDE_CMD")

    def test_ambiguous_request_drops_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_project_map(root)
            self._write_files(root)

            result = suggest_patch(root, "버전 표시해줘")

            self.assertEqual(result.confidence, "low")
            self.assertNotEqual(
                result.target_file, "vibelign/commands/install_guide_cmd.py"
            )

    def test_mixed_language_gui_request_still_prefers_home_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_project_map(root)
            self._write_files(root)

            result = suggest_patch(root, "gui 홈 화면에 version badge 추가해줘")

            self.assertEqual(result.target_file, "vibelign-gui/src/pages/Home.tsx")
            self.assertEqual(result.target_anchor, "HOME")

    def test_korean_particle_request_trims_to_install_guide_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_project_map(root)
            self._write_files(root)

            result = suggest_patch(root, "설치 가이드로 안내 문구를 바꿔줘")

            self.assertEqual(
                result.target_file, "vibelign/commands/install_guide_cmd.py"
            )

    def test_suggested_anchor_does_not_match_gui_to_guide_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "anchor_index.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "anchors": {},
                        "files": {
                            "guide_screen.py": {
                                "anchors": [],
                                "suggested_anchors": ["INSTALL_GUIDE_PANEL"],
                            },
                            "gui_home.py": {
                                "anchors": [],
                                "suggested_anchors": ["GUI_HOME_VERSION_BADGE"],
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "guide_screen.py").write_text(
                "def render_guide():\n    return 'guide'\n", encoding="utf-8"
            )
            (root / "gui_home.py").write_text(
                "def render_home():\n    return 'gui home'\n", encoding="utf-8"
            )

            result = suggest_patch(root, "gui version 표시해줘")

            self.assertEqual(result.target_file, "gui_home.py")
            self.assertEqual(
                result.target_anchor, "[추천 앵커: GUI_HOME_VERSION_BADGE]"
            )

    def test_anchor_intent_does_not_match_gui_to_guide_substring(self):
        anchor, rationale = choose_anchor(
            ["HOME_PANEL", "INSTALL_GUIDE_PANEL"],
            ["gui", "version"],
            {
                "HOME_PANEL": {"intent": "gui home version panel"},
                "INSTALL_GUIDE_PANEL": {"intent": "install guide instructions"},
            },
        )

        self.assertEqual(anchor, "HOME_PANEL")
        self.assertTrue(any("gui" in item or "version" in item for item in rationale))


if __name__ == "__main__":
    unittest.main()
