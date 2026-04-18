import json
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_patch_cmd import _build_patch_data_with_options
from vibelign.core.codespeak import build_codespeak_result
from vibelign.core.patch_suggester import (
    _decompose_korean_compound,
    _path_tokens,
    choose_anchor,
    suggest_patch,
    tokenize,
)


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
        # 자동 UI 라벨 인덱스 생성 시 TSX의 "version" 등이 «버전» 별칭과 맞물려
        # 점수·confidence가 의도치 않게 올라가므로, 픽스처에서는 빈 인덱스로 고정한다.
        (meta_dir / "ui_label_index.json").write_text(
            json.dumps({"schema_version": 1, "labels": {}}) + "\n",
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

            result = suggest_patch(root, "gui version 표시해줘", use_ai=False)

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

    def test_navigation_destination_prefers_app_over_content_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": ["vibelign-gui/src/pages/Checkpoints.tsx"],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["CHECKPOINTS"],
                            "vibelign-gui/src/pages/Checkpoints.tsx": [
                                "CHECKPOINTS_PAGE"
                            ],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["CHECKPOINTS"],
                                "line_count": 200,
                            },
                            "vibelign-gui/src/pages/Checkpoints.tsx": {
                                "category": "ui",
                                "anchors": ["CHECKPOINTS_PAGE"],
                                "line_count": 140,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                "export function App() {\n"
                "  return <nav>CHECKPOINTS</nav>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Checkpoints.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Checkpoints.tsx").write_text(
                "// === ANCHOR: CHECKPOINTS_PAGE_START ===\n"
                "export function CheckpointsPage() {\n"
                "  return <div>Checkpoints page</div>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_PAGE_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "상단 메뉴 CHECKPOINTS",
            )

            self.assertEqual(result.target_file, "vibelign-gui/src/App.tsx")
            self.assertEqual(result.target_anchor, "CHECKPOINTS")

    def test_navigation_destination_avoids_backend_checkpoints_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": ["vibelign-gui/src/pages/Home.tsx"],
                        "core_modules": ["vibelign/core/local_checkpoints.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 3,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["CHECKPOINTS"],
                            "vibelign/core/local_checkpoints.py": ["LOCAL_CHECKPOINTS"],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["CHECKPOINTS"],
                                "line_count": 200,
                            },
                            "vibelign/core/local_checkpoints.py": {
                                "category": "core",
                                "anchors": ["LOCAL_CHECKPOINTS"],
                                "line_count": 160,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                "export function App() {\n"
                "  return <nav>CHECKPOINTS</nav>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign/core/local_checkpoints.py").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign/core/local_checkpoints.py").write_text(
                "# === ANCHOR: LOCAL_CHECKPOINTS_START ===\n"
                "def list_local_checkpoints():\n"
                "    return []\n"
                "# === ANCHOR: LOCAL_CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(root, "상단 메뉴 CHECKPOINTS")

            self.assertEqual(result.target_file, "vibelign-gui/src/App.tsx")
            self.assertEqual(result.target_anchor, "CHECKPOINTS")

    def test_nav_tabs_request_prefers_app_over_titlebar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": [
                            "vibelign-gui/src/pages/Home.tsx",
                            "vibelign-gui/src/components/CustomTitleBar.tsx",
                        ],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["NAV_TABS"],
                            "vibelign-gui/src/pages/Home.tsx": ["HOME"],
                            "vibelign-gui/src/components/CustomTitleBar.tsx": [
                                "CUSTOM_TITLEBAR"
                            ],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["NAV_TABS"],
                                "line_count": 240,
                            },
                            "vibelign-gui/src/components/CustomTitleBar.tsx": {
                                "category": "ui",
                                "anchors": ["CUSTOM_TITLEBAR"],
                                "line_count": 70,
                            },
                            "vibelign-gui/src/pages/Home.tsx": {
                                "category": "ui",
                                "anchors": ["HOME"],
                                "line_count": 500,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: NAV_TABS_START ===\n"
                "export function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: NAV_TABS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").write_text(
                "// === ANCHOR: CUSTOM_TITLEBAR_START ===\n"
                "export default function CustomTitleBar() {\n"
                '  return <div className="title-bar">VIBELIGN</div>;\n'
                "}\n"
                "// === ANCHOR: CUSTOM_TITLEBAR_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Home.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Home.tsx").write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export default function Home() {\n"
                "  return <div>Manual card</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "카드 메뉴얼은 상단 메뉴 홈 | DOCTOR | CHECKPOINTS 옆으로 가는게 좋을 거 같아",
            )

            self.assertEqual(result.target_file, "vibelign-gui/src/App.tsx")
            self.assertEqual(result.target_anchor, "NAV_TABS")

    def test_nav_tabs_request_prefers_app_over_home_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": ["vibelign-gui/src/pages/Home.tsx"],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["NAV_TABS"],
                            "vibelign-gui/src/pages/Home.tsx": ["HOME"],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["NAV_TABS"],
                                "line_count": 141,
                            },
                            "vibelign-gui/src/pages/Home.tsx": {
                                "category": "ui",
                                "anchors": ["HOME"],
                                "line_count": 1483,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: NAV_TABS_START ===\n"
                "export default function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: NAV_TABS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Home.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Home.tsx").write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export default function Home() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "카드 메뉴얼은 상단 메뉴 홈 | DOCTOR | CHECKPOINTS 옆으로 가는게 좋을 거 같아.",
            )

            self.assertEqual(result.target_file, "vibelign-gui/src/App.tsx")
            self.assertEqual(result.target_anchor, "NAV_TABS")

    def test_composite_move_request_preserves_manual_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": ["vibelign-gui/src/pages/Home.tsx"],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["NAV_TABS"],
                            "vibelign-gui/src/pages/Home.tsx": ["HOME"],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["NAV_TABS"],
                                "line_count": 141,
                            },
                            "vibelign-gui/src/pages/Home.tsx": {
                                "category": "ui",
                                "anchors": ["HOME"],
                                "line_count": 1483,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: APP_START ===\n"
                "export default function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: APP_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Home.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Home.tsx").write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export default function Home() {\n"
                "  return <div>Manual card</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )

            request = (
                "프로젝트 홈에서 메뉴얼 카드 삭제하고 상단 메뉴의 CHECKPOINTS 옆으로 이동시켜. "
                "그리고 클릭하면 메뉴얼 화면으로 이동해야 돼."
            )
            result = _build_patch_data_with_options(
                root, request, use_ai=False, quiet_ai=True
            )["patch_plan"]

            self.assertEqual(result["request"], request)
            self.assertEqual(result["target_file"], "vibelign-gui/src/pages/Home.tsx")
            self.assertEqual(result["target_anchor"], "HOME")
            self.assertEqual(
                result["destination_target_file"], "vibelign-gui/src/App.tsx"
            )
            self.assertEqual(result["destination_target_anchor"], "APP")
            self.assertEqual(result["patch_points"]["operation"], "move")
            steps = cast(list[dict[str, object]], result["steps"])
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["target_file"], result["target_file"])
            self.assertEqual(steps[0]["target_anchor"], result["target_anchor"])
            self.assertEqual(
                result["patch_points"]["behavior_constraint"],
                "클릭하면 메뉴얼 화면으로 이동해야 돼.",
            )
            self.assertEqual(
                steps[0]["search_fingerprint"], result["patch_points"]["source"]
            )
            self.assertIn(
                "Behavior preservation: 클릭하면 메뉴얼 화면으로 이동해야 돼.",
                result["constraints"],
            )

    def test_builder_move_request_matches_standalone_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": [
                            "vibelign-gui/src/components/CustomTitleBar.tsx"
                        ],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["NAV_TABS"],
                            "vibelign-gui/src/components/CustomTitleBar.tsx": [
                                "CUSTOM_TITLEBAR"
                            ],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["NAV_TABS"],
                                "line_count": 240,
                            },
                            "vibelign-gui/src/components/CustomTitleBar.tsx": {
                                "category": "ui",
                                "anchors": ["CUSTOM_TITLEBAR"],
                                "line_count": 70,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: NAV_TABS_START ===\n"
                "export function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: NAV_TABS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").write_text(
                "// === ANCHOR: CUSTOM_TITLEBAR_START ===\n"
                "export default function CustomTitleBar() {\n"
                '  return <div className="title-bar">VIBELIGN</div>;\n'
                "}\n"
                "// === ANCHOR: CUSTOM_TITLEBAR_END ===\n",
                encoding="utf-8",
            )

            request = "카드 메뉴얼은 상단 메뉴 홈 | DOCTOR | CHECKPOINTS 옆으로 가는게 좋을 거 같아."
            builder = _build_patch_data_with_options(
                root, request, use_ai=True, quiet_ai=True
            )

            self.assertEqual(builder["patch_plan"]["patch_points"]["operation"], "move")
            steps = cast(list[dict[str, object]], builder["patch_plan"]["steps"])
            self.assertEqual(len(steps), 1)
            self.assertEqual(
                steps[0]["target_file"], builder["patch_plan"]["target_file"]
            )
            self.assertEqual(
                builder["patch_plan"]["destination_target_file"],
                "vibelign-gui/src/App.tsx",
            )
            self.assertEqual(
                builder["patch_plan"]["destination_target_anchor"], "NAV_TABS"
            )

    def test_ai_move_upgrade_recomputes_destination_targeting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": ["vibelign-gui/src/pages/Home.tsx"],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["NAV_TABS"],
                            "vibelign-gui/src/pages/Home.tsx": ["HOME"],
                        },
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "entry",
                                "anchors": ["NAV_TABS"],
                                "line_count": 240,
                            },
                            "vibelign-gui/src/pages/Home.tsx": {
                                "category": "ui",
                                "anchors": ["HOME"],
                                "line_count": 120,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: NAV_TABS_START ===\n"
                "export function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: NAV_TABS_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Home.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Home.tsx").write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export default function Home() {\n"
                "  return <div>Manual card</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )

            request = "manual card를 상단 메뉴 CHECKPOINTS 옆으로 옮겨줘"

            base_result = build_codespeak_result(
                request,
                codespeak="ui.component.manual_card.update",
                interpretation="manual card를 업데이트하는 요청으로 해석했습니다.",
                confidence="medium",
                clarifying_questions=[],
            )
            if base_result is None:
                self.fail("build_codespeak_result should return a baseline rule result")

            with (
                patch(
                    "vibelign.patch.patch_builder.build_codespeak",
                    return_value=base_result,
                ),
                patch(
                    "vibelign.core.ai_explain.has_ai_provider",
                    return_value=True,
                ),
                patch(
                    "vibelign.core.ai_explain.generate_text_with_ai",
                    return_value=(
                        '{"codespeak":"ui.component.manual_card.move","interpretation":"메뉴얼 카드를 상단 메뉴로 이동하는 요청으로 해석했습니다.","confidence":"high","clarifying_questions":[]}',
                        True,
                    ),
                ),
            ):
                builder = _build_patch_data_with_options(
                    root,
                    request,
                    use_ai=True,
                    quiet_ai=True,
                )

            patch_plan = cast(dict[str, object], builder["patch_plan"])
            patch_points = cast(dict[str, object], patch_plan["patch_points"])
            destination_resolution = cast(
                dict[str, object], patch_plan["destination_resolution"]
            )
            intent_ir = cast(dict[str, object], patch_plan["intent_ir"])
            self.assertEqual(patch_points["operation"], "move")
            steps = cast(list[dict[str, object]], patch_plan["steps"])
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["status"], "READY")
            self.assertEqual(steps[0]["search_fingerprint"], patch_points["source"])
            self.assertEqual(
                patch_plan["destination_target_file"], "vibelign-gui/src/App.tsx"
            )
            self.assertEqual(patch_plan["destination_target_anchor"], "NAV_TABS")
            self.assertEqual(destination_resolution["role"], "destination")
            self.assertEqual(intent_ir["operation"], "move")

    def test_move_without_source_fingerprint_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "vibelign-gui/src/pages/Home.tsx"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function HomePage() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            app.write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                "export function CheckpointsMenu() {\n"
                "  return <nav>CHECKPOINTS</nav>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            with patch(
                "vibelign.patch.patch_builder.build_codespeak",
                return_value=cast(
                    object,
                    build_codespeak_result(
                        "이걸 상단 메뉴 CHECKPOINTS로 옮겨줘",
                        codespeak="ui.component.card.move",
                        interpretation="카드를 상단 메뉴로 이동하는 요청으로 해석했습니다.",
                        confidence="high",
                        clarifying_questions=[],
                    ),
                ),
            ):
                builder = _build_patch_data_with_options(
                    root,
                    "이걸 상단 메뉴 CHECKPOINTS로 옮겨줘",
                    use_ai=False,
                    quiet_ai=True,
                )

            patch_plan = cast(dict[str, object], builder["patch_plan"])
            step = cast(dict[str, object], patch_plan["steps"][0])
            self.assertEqual(step["status"], "NEEDS_CLARIFICATION")
            self.assertIsNone(step["search_fingerprint"])

    def test_card_manual_placement_prefers_app_over_command_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "project_map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": root.name,
                        "entry_files": [],
                        "ui_modules": [
                            "vibelign-gui/src/pages/Home.tsx",
                            "vibelign-gui/src/components/CustomTitleBar.tsx",
                            "vibelign-gui/src/App.tsx",
                        ],
                        "core_modules": ["vibelign/commands/vib_patch_cmd.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 4,
                        "anchor_index": {
                            "vibelign-gui/src/pages/Home.tsx": ["HOME"],
                            "vibelign-gui/src/components/CustomTitleBar.tsx": [
                                "CUSTOM_TITLEBAR"
                            ],
                            "vibelign-gui/src/App.tsx": ["APP"],
                            "vibelign/commands/vib_patch_cmd.py": ["VIB_PATCH_CMD"],
                        },
                        "files": {
                            "vibelign-gui/src/pages/Home.tsx": {
                                "category": "ui",
                                "anchors": ["HOME"],
                                "line_count": 260,
                            },
                            "vibelign-gui/src/components/CustomTitleBar.tsx": {
                                "category": "ui",
                                "anchors": ["CUSTOM_TITLEBAR"],
                                "line_count": 36,
                            },
                            "vibelign-gui/src/App.tsx": {
                                "category": "ui",
                                "anchors": ["APP"],
                                "line_count": 141,
                            },
                            "vibelign/commands/vib_patch_cmd.py": {
                                "category": "core",
                                "anchors": ["VIB_PATCH_CMD"],
                                "line_count": 689,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/pages/Home.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/pages/Home.tsx").write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function HomePage() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/components/CustomTitleBar.tsx").write_text(
                "// === ANCHOR: CUSTOM_TITLEBAR_START ===\n"
                "export default function CustomTitleBar() {\n"
                "  return <div>VIBELIGN</div>;\n"
                "}\n"
                "// === ANCHOR: CUSTOM_TITLEBAR_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign-gui/src/App.tsx").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign-gui/src/App.tsx").write_text(
                "// === ANCHOR: APP_START ===\n"
                "export function App() {\n"
                '  return <div className="nav-tabs">HOME | DOCTOR | CHECKPOINTS</div>;\n'
                "}\n"
                "// === ANCHOR: APP_END ===\n",
                encoding="utf-8",
            )
            (root / "vibelign/commands/vib_patch_cmd.py").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / "vibelign/commands/vib_patch_cmd.py").write_text(
                "# === ANCHOR: VIB_PATCH_CMD_START ===\n"
                "def run_vib_patch():\n"
                "    return None\n"
                "# === ANCHOR: VIB_PATCH_CMD_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "카드 메뉴얼은 상단 메뉴 홈 | DOCTOR | CHECKPOINTS 옆으로 가는게 좋을 거 같아.",
            )

            self.assertEqual(result.target_file, "vibelign-gui/src/App.tsx")
            self.assertEqual(result.target_anchor, "APP")

    def test_path_tokens_splits_pascal_case_file_name(self):
        """PascalCase 파일명은 토큰으로 분리되어야 한다.

        'ClaudeHookCard.tsx' 가 {'claudehookcard'} 하나로만 떨어지면
        'claude' / 'hook' / 'card' 같은 요청 토큰이 path 매칭에 실패한다.
        """
        tokens = _path_tokens(
            "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx"
        )
        self.assertIn("claude", tokens)
        self.assertIn("hook", tokens)
        self.assertIn("card", tokens)
        # snake_case 도 여전히 정상 동작해야 한다
        self.assertEqual(
            _path_tokens("vibelign/core/patch_suggester.py"),
            _path_tokens("vibelign/core/patch_suggester.py"),
        )
        snake_tokens = _path_tokens("vibelign/core/patch_suggester.py")
        self.assertIn("patch", snake_tokens)
        self.assertIn("suggester", snake_tokens)

    def test_korean_claude_hook_request_prefers_card_component_over_settings_page(
        self,
    ):
        """한국어 "클로드 훅 ... 수정해줘" 요청은 ClaudeHookCard.tsx 를 고르고
        Settings.tsx 페이지는 피해야 한다 — ui_label_index · anchor_index 가
        없어도 파일명 토큰과 state-owner hint 만으로 정답이 나와야 한다.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            # 라벨 인덱스 · anchor 인덱스 를 의도적으로 비운다
            (meta_dir / "ui_label_index.json").write_text(
                json.dumps({"schema_version": 1, "labels": {}}) + "\n",
                encoding="utf-8",
            )
            (meta_dir / "anchor_index.json").write_text(
                json.dumps(
                    {"schema_version": 1, "anchors": {}, "files": {}}
                )
                + "\n",
                encoding="utf-8",
            )

            card_path = (
                root
                / "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx"
            )
            card_path.parent.mkdir(parents=True, exist_ok=True)
            card_path.write_text(
                "// === ANCHOR: CLAUDE_HOOK_CARD_START ===\n"
                "export default function ClaudeHookCard() { return null; }\n"
                "// === ANCHOR: CLAUDE_HOOK_CARD_END ===\n",
                encoding="utf-8",
            )

            settings_path = root / "vibelign-gui/src/pages/Settings.tsx"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                "// === ANCHOR: SETTINGS_START ===\n"
                "export default function Settings() { return null; }\n"
                "// === ANCHOR: SETTINGS_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "클로드 훅 enable 시키고 새로고침하면 유지되지 않아. 수정해줘.",
                use_ai=False,
            )

            self.assertEqual(
                result.target_file,
                "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx",
                result.rationale,
            )

    def test_decompose_korean_compound_splits_known_alias_keys(self):
        """'클로드훅' 처럼 _TOKEN_ALIASES 키로 완전히 덮이는 합성어만 분해한다.

        단어장 확장이 아니라 '이미 아는 조각을 알아본다'는 원칙이다.
        """
        self.assertEqual(_decompose_korean_compound("클로드훅"), ["클로드", "훅"])
        # 알 수 없는 한글은 그대로 둔다 (할루시네이션 방지)
        self.assertEqual(_decompose_korean_compound("안녕하세요"), [])
        # 이미 단일 alias 키인 경우는 분해하지 않는다
        self.assertEqual(_decompose_korean_compound("훅"), [])
        # 토크나이저가 '클로드훅' 에서 claude/hook 영문 토큰을 만들어내야 한다
        tokens = tokenize("클로드훅 enable 유지 안됨")
        self.assertIn("claude", tokens)
        self.assertIn("hook", tokens)

    def test_korean_hook_state_request_skips_backend_state_store(self):
        """실제 GUI 사용자 요청 재현 테스트.

        "클로드훅 enable 실행 뒤 다른 메뉴 갔다 오면 enable 유지가 안돼. 수정해줘."

        규칙 기반 스코어러는 아래 함정에 빠지면 안 된다:
        - 'state' 토큰이 backend `vibelign/mcp/mcp_state_store.py` 에 매칭되는 함정
        - '메뉴' 토큰이 nav-only 페널티를 유발해서 UI 카드 파일을 떨어뜨리는 함정
        - Settings.tsx 페이지로 잘못 가는 함정

        ClaudeHookCard.tsx 가 1순위로 선택돼야 한다.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "ui_label_index.json").write_text(
                json.dumps({"schema_version": 1, "labels": {}}) + "\n",
                encoding="utf-8",
            )
            (meta_dir / "anchor_index.json").write_text(
                json.dumps({"schema_version": 1, "anchors": {}, "files": {}}) + "\n",
                encoding="utf-8",
            )

            # Frontend: Claude hook 전용 카드 (정답)
            card_path = (
                root
                / "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx"
            )
            card_path.parent.mkdir(parents=True, exist_ok=True)
            card_path.write_text(
                "// === ANCHOR: CLAUDE_HOOK_CARD_START ===\n"
                "export default function ClaudeHookCard() { return null; }\n"
                "// === ANCHOR: CLAUDE_HOOK_CARD_END ===\n",
                encoding="utf-8",
            )

            # Frontend: 일반 설정 페이지 (오답 후보 A)
            settings_path = root / "vibelign-gui/src/pages/Settings.tsx"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                "// === ANCHOR: SETTINGS_START ===\n"
                "export default function Settings() { return null; }\n"
                "// === ANCHOR: SETTINGS_END ===\n",
                encoding="utf-8",
            )

            # Backend: state 토큰이 경로에 있지만 Claude hook과 무관 (오답 후보 B)
            mcp_state_path = root / "vibelign/mcp/mcp_state_store.py"
            mcp_state_path.parent.mkdir(parents=True, exist_ok=True)
            mcp_state_path.write_text(
                "# === ANCHOR: MCP_STATE_STORE_START ===\n"
                "def load_state():\n    return {}\n"
                "# === ANCHOR: MCP_STATE_STORE_END ===\n",
                encoding="utf-8",
            )

            result = suggest_patch(
                root,
                "클로드훅 enable 실행 뒤 다른 메뉴 갔다 오면 enable 유지가 안돼. 수정해줘.",
                use_ai=False,
            )

            self.assertEqual(
                result.target_file,
                "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx",
                result.rationale,
            )


if __name__ == "__main__":
    unittest.main()
