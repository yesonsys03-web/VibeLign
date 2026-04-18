import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout
from types import SimpleNamespace
from typing import cast

from vibelign.commands.vib_plan_structure_cmd import run_vib_plan_structure
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.structure_planner import build_structure_plan
from vibelign.mcp.mcp_state_store import load_planning_session


class StructurePlannerTest(unittest.TestCase):
    def test_build_structure_plan_includes_phase1_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/auth.py": {
                                "category": "core",
                                "anchors": ["AUTH_HANDLER", "AUTH_STORAGE"],
                                "line_count": 187,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/auth.py"],
                        "service_modules": [],
                        "large_files": ["vibelign/core/auth.py"],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/auth.py": ["AUTH_HANDLER", "AUTH_STORAGE"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "OAuth 인증 추가")

            self.assertEqual(plan["schema_version"], 1)
            self.assertEqual(plan["mode"], "rules")
            self.assertIn("evidence", plan)
            self.assertIn("scope", plan)
            self.assertTrue(plan["required_new_files"])
            self.assertTrue(plan["allowed_modifications"])
            self.assertTrue(plan["forbidden"])
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertEqual(evidence["matched_categories"], ["core"])
            self.assertIn("auth", cast(list[object], evidence["path_signals"]))
            required_new_files = cast(
                list[dict[str, object]], plan["required_new_files"]
            )
            self.assertEqual(
                required_new_files[0]["path"], "vibelign/core/oauth_provider.py"
            )

    def test_run_vib_plan_structure_persists_plan_and_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.state_path.write_text(
                json.dumps({"schema_version": 1}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": ["WATCH_ENGINE_START"],
                                "line_count": 120,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/watch_engine.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            previous = Path.cwd()
            try:
                os.chdir(root)
                args = cast(
                    object,
                    SimpleNamespace(
                        feature=["watch", "기능", "확장"],
                        ai=False,
                        scope="",
                        json=False,
                    ),
                )
                run_vib_plan_structure(cast(object, args))
            finally:
                os.chdir(previous)

            plans = list(meta.plans_dir.glob("*.json"))
            self.assertEqual(len(plans), 1)
            payload = json.loads(plans[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["feature"], "watch 기능 확장")
            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["plan_id"], payload["id"])
            self.assertEqual(planning["active"], True)

    def test_existing_file_only_plan_has_no_self_contradicting_forbidden_rule(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": ["WATCH_ENGINE_START"],
                                "line_count": 120,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/watch_engine.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "watch 기능 확장")

            self.assertFalse(plan["required_new_files"])
            allowed_modifications = cast(
                list[dict[str, object]], plan["allowed_modifications"]
            )
            self.assertEqual(len(allowed_modifications), 1)
            self.assertEqual(plan["forbidden"], [])

    def test_new_file_plan_forbids_broad_edit_but_keeps_allowed_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/auth.py": {
                                "category": "core",
                                "anchors": ["AUTH_HANDLER", "AUTH_STORAGE"],
                                "line_count": 187,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/auth.py"],
                        "service_modules": [],
                        "large_files": ["vibelign/core/auth.py"],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/auth.py": ["AUTH_HANDLER", "AUTH_STORAGE"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "OAuth 인증 추가")

            forbidden = cast(list[dict[str, object]], plan["forbidden"])
            self.assertEqual(len(forbidden), 1)
            self.assertEqual(forbidden[0]["type"], "path_edit_outside_allowed_anchor")
            self.assertEqual(forbidden[0]["path"], "vibelign/core/auth.py")
            self.assertEqual(forbidden[0]["anchor"], "AUTH_HANDLER")

    def test_mcp_handler_feature_prefers_existing_mcp_handler_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/mcp/mcp_patch_handlers.py": {
                                "category": "mcp",
                                "anchors": ["PATCH_HANDLERS_START"],
                                "line_count": 90,
                            },
                            "vibelign/mcp/mcp_handler_registry.py": {
                                "category": "mcp",
                                "anchors": ["REGISTRY_START"],
                                "line_count": 80,
                            },
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": [],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign/mcp/mcp_patch_handlers.py": [
                                "PATCH_HANDLERS_START"
                            ],
                            "vibelign/mcp/mcp_handler_registry.py": ["REGISTRY_START"],
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "mcp handler 수정")

            allowed_modifications = cast(
                list[dict[str, object]], plan["allowed_modifications"]
            )
            self.assertEqual(
                allowed_modifications[0]["path"], "vibelign/mcp/mcp_patch_handlers.py"
            )
            self.assertFalse(plan["required_new_files"])
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertIn(
                evidence["anchor_selection"],
                ["keyword_anchor_match", "strong_path_signal_fallback"],
            )

    def test_missing_project_map_falls_back_to_conservative_new_file_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            plan = build_structure_plan(root, "개선")

            required_new_files = cast(
                list[dict[str, object]], plan["required_new_files"]
            )
            self.assertEqual(
                required_new_files[0]["path"], "vibelign/core/new_feature.py"
            )
            messages = cast(dict[str, object], plan["messages"])
            warnings = cast(list[object], messages["warnings"])
            self.assertTrue(
                any("project_map이 없습니다" in str(item) for item in warnings)
            )
            self.assertTrue(any("--ai 옵션" in str(item) for item in warnings))

    def test_anchor_index_is_used_when_file_metadata_has_no_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": [],
                                "line_count": 120,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/watch_engine.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "watch 기능 확장")

            allowed_modifications = cast(
                list[dict[str, object]], plan["allowed_modifications"]
            )
            self.assertEqual(allowed_modifications[0]["anchor"], "WATCH_ENGINE_START")
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertEqual(evidence["anchor_selection"], "keyword_anchor_match")
            self.assertEqual(
                evidence["candidate_files"], ["vibelign/core/watch_engine.py"]
            )

    def test_gui_request_prefers_gui_entry_and_gui_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign-gui/src/App.tsx": {
                                "category": "ui",
                                "anchors": ["APP"],
                                "line_count": 173,
                            },
                            "vibelign-gui/src/components/CustomTitleBar.tsx": {
                                "category": "ui",
                                "anchors": ["CUSTOM_TITLEBAR"],
                                "line_count": 40,
                            },
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": ["WATCH_ENGINE_START"],
                                "line_count": 120,
                            },
                        },
                        "entry_files": ["vibelign-gui/src/App.tsx"],
                        "ui_modules": [
                            "vibelign-gui/src/App.tsx",
                            "vibelign-gui/src/components/CustomTitleBar.tsx",
                        ],
                        "core_modules": ["vibelign/core/watch_engine.py"],
                        "service_modules": [],
                        "large_files": ["vibelign-gui/src/App.tsx"],
                        "file_count": 3,
                        "anchor_index": {
                            "vibelign-gui/src/App.tsx": ["APP"],
                            "vibelign-gui/src/components/CustomTitleBar.tsx": [
                                "CUSTOM_TITLEBAR"
                            ],
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"],
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(
                root,
                "상단의 폴더열기 오른쪽에 실시간 로그 버튼 추가해줘. 누르면 로그 패널이 열리게 해줘.",
            )

            allowed_modifications = cast(
                list[dict[str, object]], plan["allowed_modifications"]
            )
            self.assertEqual(
                allowed_modifications[0]["path"], "vibelign-gui/src/App.tsx"
            )
            required_new_files = cast(
                list[dict[str, object]], plan["required_new_files"]
            )
            self.assertEqual(
                required_new_files[0]["path"], "vibelign-gui/src/log_panel.tsx"
            )
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertEqual(evidence["matched_categories"], ["ui"])
            self.assertNotIn("watch", cast(list[object], evidence["path_signals"]))

    def test_run_vib_plan_structure_json_outputs_saved_plan_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.state_path.write_text(
                json.dumps({"schema_version": 1}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": ["WATCH_ENGINE_START"],
                                "line_count": 120,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/watch_engine.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            previous = Path.cwd()
            stdout = StringIO()
            try:
                os.chdir(root)
                args = cast(
                    object,
                    SimpleNamespace(
                        feature=["watch", "기능", "확장"], ai=False, scope="", json=True
                    ),
                )
                with redirect_stdout(stdout):
                    run_vib_plan_structure(cast(object, args))
            finally:
                os.chdir(previous)

            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            data = cast(dict[str, object], payload["data"])
            self.assertTrue(str(data["plan_path"]).startswith(".vibelign/plans/"))
            plan = cast(dict[str, object], data["plan"])
            self.assertEqual(plan["feature"], "watch 기능 확장")

    def test_weak_signal_candidate_stays_conservative_when_anchor_does_not_match(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/scan_report.py": {
                                "category": "core",
                                "anchors": ["REPORT_SECTION"],
                                "line_count": 120,
                            }
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": ["vibelign/core/scan_report.py"],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 1,
                        "anchor_index": {
                            "vibelign/core/scan_report.py": ["REPORT_SECTION"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "scan 기능 확장")

            self.assertEqual(plan["allowed_modifications"], [])
            required_new_files = cast(
                list[dict[str, object]], plan["required_new_files"]
            )
            self.assertEqual(
                required_new_files[0]["path"], "vibelign/core/watch_extension.py"
            )
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertEqual(evidence["anchor_selection"], None)

    def test_candidate_files_reflect_scored_subset_not_all_scoped_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/noise_a.py": {
                                "category": "core",
                                "anchors": ["NOISE_A"],
                                "line_count": 120,
                            },
                            "vibelign/core/noise_b.py": {
                                "category": "core",
                                "anchors": ["NOISE_B"],
                                "line_count": 120,
                            },
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": ["WATCH_ENGINE_START"],
                                "line_count": 120,
                            },
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": [
                            "vibelign/core/noise_a.py",
                            "vibelign/core/noise_b.py",
                            "vibelign/core/watch_engine.py",
                        ],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 3,
                        "anchor_index": {
                            "vibelign/core/noise_a.py": ["NOISE_A"],
                            "vibelign/core/noise_b.py": ["NOISE_B"],
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"],
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "watch 기능 확장", scope="vibelign/core/")

            evidence = cast(dict[str, object], plan["evidence"])
            candidate_files = cast(list[object], evidence["candidate_files"])
            self.assertEqual(candidate_files, ["vibelign/core/watch_engine.py"])

    def test_anchor_index_affects_candidate_selection_viability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.project_map_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_name": "demo",
                        "tree": [],
                        "files": {
                            "vibelign/core/watch_engine.py": {
                                "category": "core",
                                "anchors": [],
                                "line_count": 120,
                            },
                            "vibelign/core/watch_notes.py": {
                                "category": "core",
                                "anchors": [],
                                "line_count": 120,
                            },
                        },
                        "entry_files": [],
                        "ui_modules": [],
                        "core_modules": [
                            "vibelign/core/watch_engine.py",
                            "vibelign/core/watch_notes.py",
                        ],
                        "service_modules": [],
                        "large_files": [],
                        "file_count": 2,
                        "anchor_index": {
                            "vibelign/core/watch_engine.py": ["WATCH_ENGINE_START"]
                        },
                        "generated_at": "2026-04-09T00:00:00Z",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = build_structure_plan(root, "watch 기능 확장")

            allowed_modifications = cast(
                list[dict[str, object]], plan["allowed_modifications"]
            )
            self.assertEqual(
                allowed_modifications[0]["path"], "vibelign/core/watch_engine.py"
            )
            evidence = cast(dict[str, object], plan["evidence"])
            self.assertEqual(
                evidence["candidate_files"], ["vibelign/core/watch_engine.py"]
            )


if __name__ == "__main__":
    unittest.main()
