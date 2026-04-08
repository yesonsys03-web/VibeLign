import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_start_cmd import run_vib_start
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.commands.vib_doctor_cmd import _run_fix
from vibelign.action_engine.action_planner import generate_plan
from vibelign.core.doctor_v2 import (
    _project_score_from_issues,
    build_doctor_envelope,
    render_doctor_markdown,
    DoctorV2Report,
)


class VibDoctorV2Test(unittest.TestCase):
    @staticmethod
    def _start_args() -> Namespace:
        return Namespace(all_tools=False, tools=None, force=False)

    def test_render_doctor_markdown_uses_friendly_labels(self):
        markdown = render_doctor_markdown(
            DoctorV2Report(
                project_score=82,
                status="Good",
                anchor_coverage=60,
                stats={
                    "mcp_status": {
                        "cursor": {
                            "enabled": True,
                            "label": "Cursor",
                            "state": "registered",
                        }
                    },
                    "prepared_tool_status": {
                        "opencode": {
                            "enabled": True,
                            "label": "OpenCode",
                            "ready": True,
                        }
                    },
                },
                issues=[],
                recommended_actions=["vib anchor --suggest"],
            )
        )
        self.assertIn("VibeLign 프로젝트 상태 보기", markdown)
        self.assertIn("프로젝트 점수: 82 / 100", markdown)
        self.assertIn("Cursor MCP: 연결됨", markdown)
        self.assertIn("OpenCode: 준비됨", markdown)
        self.assertIn("다음에 하면 좋은 일:", markdown)

    def test_doctor_envelope_contains_score_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 90, encoding="utf-8")
            (root / "ui_panel.py").write_text(
                "def render():\n    return 'ui'\n", encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

            self.assertTrue(envelope["ok"])
            data = cast(dict[str, object], envelope["data"])
            self.assertIn("project_score", data)
            self.assertIn("anchor_coverage", data)
            self.assertTrue(0 <= cast(int, data["project_score"]) <= 100)
            self.assertIn(
                cast(str, data["status"]),
                {"Safe", "Good", "Caution", "Risky", "High Risk"},
            )
            self.assertIn("project_map_loaded", cast(dict[str, object], data["stats"]))

    def test_doctor_reports_small_anchorless_file_in_default_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            anchor_issue = next(
                item for item in issues if item.get("path") == "main.py"
            )
            self.assertEqual("anchor", anchor_issue["category"])
            self.assertEqual("low", anchor_issue["severity"])
            self.assertEqual("vib doctor --fix", anchor_issue["recommended_command"])
            self.assertTrue(anchor_issue["can_auto_fix"])

    def test_doctor_ignores_empty_init_files_for_anchor_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            stats = cast(dict[str, object], data["stats"])
            self.assertFalse(
                any(item.get("path") == "pkg/__init__.py" for item in issues)
            )
            self.assertEqual(100, cast(int, data["anchor_coverage"]))
            self.assertEqual(0, cast(int, stats["missing_anchor_files"]))

    def test_doctor_reports_logic_bearing_init_files_for_anchor_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text(
                "def exported():\n    return 1\n", encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            anchor_issue = next(
                item for item in issues if item.get("path") == "pkg/__init__.py"
            )
            self.assertEqual("anchor", anchor_issue["category"])
            self.assertEqual("low", anchor_issue["severity"])

    def test_doctor_ignores_docstring_only_init_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text('"""package docs"""\n', encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            self.assertFalse(
                any(item.get("path") == "pkg/__init__.py" for item in issues)
            )
            self.assertEqual(100, cast(int, data["anchor_coverage"]))

    def test_doctor_ignores_import_only_init_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text(
                "from .module import exported\n", encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            self.assertFalse(
                any(item.get("path") == "pkg/__init__.py" for item in issues)
            )
            self.assertEqual(100, cast(int, data["anchor_coverage"]))

    def test_doctor_ignores_all_only_init_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text(
                '__all__ = ["exported"]\n', encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            self.assertFalse(
                any(item.get("path") == "pkg/__init__.py" for item in issues)
            )
            self.assertEqual(100, cast(int, data["anchor_coverage"]))

    def test_doctor_updates_last_scan_at_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_start(self._start_args())
                run_vib_doctor(
                    Namespace(
                        json=True,
                        strict=False,
                        detailed=False,
                        fix_hints=False,
                        write_report=False,
                    )
                )
            finally:
                os.chdir(previous)

            state_text = (root / ".vibelign" / "state.json").read_text(encoding="utf-8")
            self.assertIn('"last_scan_at":', state_text)
            self.assertNotIn('"last_scan_at": null', state_text)

    def test_doctor_reports_project_map_when_initialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_start(self._start_args())
                envelope = build_doctor_envelope(root, strict=False)
            finally:
                os.chdir(previous)

            data = cast(dict[str, object], envelope["data"])
            stats = cast(dict[str, object], data["stats"])
            self.assertTrue(stats["project_map_loaded"])
            self.assertEqual(stats["project_map_file_count"], 1)

    def test_doctor_reports_invalid_project_map_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "project_map.json").write_text(
                '{"schema_version": 999, "project_name": "broken"}\n',
                encoding="utf-8",
            )

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            stats = cast(dict[str, object], data["stats"])
            self.assertFalse(cast(bool, stats["project_map_loaded"]))
            issues = cast(list[dict[str, object]], data["issues"])
            self.assertTrue(
                any(
                    "버전이 맞지 않아요" in str(item.get("found", ""))
                    for item in issues
                )
            )

    def test_doctor_reports_missing_cursor_mcp_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            stats = cast(dict[str, object], data["stats"])
            mcp_status = cast(dict[str, object], stats["mcp_status"])
            cursor_status = cast(dict[str, object], mcp_status["cursor"])
            self.assertEqual(cursor_status["state"], "not_configured")
            self.assertTrue(
                any(
                    ".cursor/mcp.json에 vibelign MCP 등록이 없어요"
                    in str(item.get("found", ""))
                    for item in cast(list[dict[str, object]], data["issues"])
                )
            )
            self.assertTrue(
                any(
                    "vib start --tools cursor" in action
                    for action in cast(list[str], data["recommended_actions"])
                )
            )

    def test_doctor_reports_registered_cursor_mcp_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")
            cursor_dir = root / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "mcp.json").write_text(
                "{\n"
                '  "mcpServers": {\n'
                '    "vibelign": {"command": "vibelign-mcp", "args": []}\n'
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            stats = cast(dict[str, object], data["stats"])
            mcp_status = cast(dict[str, object], stats["mcp_status"])
            cursor_status = cast(dict[str, object], mcp_status["cursor"])
            self.assertEqual(cursor_status["state"], "registered")
            self.assertFalse(
                any(
                    ".cursor/mcp.json에 vibelign MCP 등록이 없어요"
                    in str(item.get("found", ""))
                    for item in cast(list[dict[str, object]], data["issues"])
                )
            )

    def test_doctor_reports_partial_opencode_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "OPENCODE.md").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            stats = cast(dict[str, object], data["stats"])
            prepared = cast(dict[str, object], stats["prepared_tool_status"])
            opencode = cast(dict[str, object], prepared["opencode"])
            self.assertEqual(opencode["state"], "partial")
            self.assertTrue(
                any(
                    "OpenCode 준비 파일이 일부 없어요" in str(item.get("found", ""))
                    for item in cast(list[dict[str, object]], data["issues"])
                )
            )
            self.assertTrue(
                any(
                    "vib start --tools opencode" in action
                    for action in cast(list[str], data["recommended_actions"])
                )
            )

    def test_doctor_issue_contains_structured_recovery_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 300, encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            issue = issues[0]

            self.assertIn("severity", issue)
            self.assertIn("category", issue)
        self.assertIn("recommended_command", issue)
        self.assertIn("can_auto_fix", issue)
        self.assertIn("auto_fix_label", issue)

    def test_doctor_does_not_flag_cli_like_windows_install_module_as_mixed_concerns(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = (
                "import subprocess\n"
                "def render_help():\n    return 'Windows completion setup'\n\n"
                "def install():\n    subprocess.run(['cmd'])\n"
            ) + ("\n" * 160)
            (root / "cli_completion.py").write_text(content, encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            self.assertFalse(
                any(item.get("check_type") == "mixed_concerns_ui" for item in issues)
            )

    def test_project_score_from_structure_issues_does_not_collapse_to_zero(self):
        issues = cast(
            list[dict[str, object]],
            [{"category": "structure", "severity": "medium"} for _ in range(30)]
            + [{"category": "mcp", "severity": "high"}],
        )

        score = _project_score_from_issues(issues)

        self.assertGreater(score, 0)
        self.assertLess(score, 100)

    def test_doctor_score_includes_appended_mcp_issue_penalty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = cast(dict[str, object], envelope["data"])
            self.assertEqual(96, cast(int, data["project_score"]))
            self.assertEqual("Safe", cast(str, data["status"]))

    def test_doctor_report_to_plan_preserves_anchor_mcp_and_review_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")
            (root / "large_module.py").write_text(
                "print('x')\n" * 520, encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)
            data = cast(dict[str, object], envelope["data"])

            plan = generate_plan(data)

            anchor_action = next(
                action for action in plan.actions if action.target_path == "main.py"
            )
            mcp_action = next(
                action
                for action in plan.actions
                if action.target_path == ".cursor/mcp.json"
            )
            review_action = next(
                action
                for action in plan.actions
                if action.target_path == "large_module.py"
                and action.action_type == "review"
            )

            self.assertEqual("add_anchor", anchor_action.action_type)
            self.assertEqual("fix_mcp", mcp_action.action_type)
            self.assertEqual("review", review_action.action_type)

    def test_missing_cursor_mcp_issue_uses_mcp_category_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            data = cast(dict[str, object], envelope["data"])
            issues = cast(list[dict[str, object]], data["issues"])
            mcp_issue = next(i for i in issues if i["category"] == "mcp")

            self.assertEqual("high", mcp_issue["severity"])
            self.assertEqual(
                "vib start --tools cursor", mcp_issue["recommended_command"]
            )
            self.assertFalse(mcp_issue["can_auto_fix"])

    def test_doctor_plan_json_includes_small_anchorless_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.vib_doctor_cmd.print") as mocked:
                    run_vib_doctor(
                        Namespace(
                            strict=False,
                            json=True,
                            write_report=False,
                            fix=False,
                            detailed=False,
                            fix_hints=False,
                            plan=True,
                            patch=False,
                            apply=False,
                            force=False,
                        )
                    )
                    payload = json.loads(str(mocked.call_args.args[0]))
            finally:
                os.chdir(previous)

            actions = payload["actions"]
            anchor_action = next(
                item for item in actions if item.get("target_path") == "main.py"
            )
            self.assertEqual("add_anchor", anchor_action["action_type"])

    def test_doctor_apply_json_anchors_all_small_anchorless_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "main.py"
            second = root / "helper.py"
            first.write_text("print('hello')\n", encoding="utf-8")
            second.write_text("def helper():\n    return 1\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.vib_doctor_cmd.print") as mocked:
                    run_vib_doctor(
                        Namespace(
                            strict=False,
                            json=True,
                            write_report=False,
                            fix=False,
                            detailed=False,
                            fix_hints=False,
                            plan=False,
                            patch=False,
                            apply=True,
                            force=True,
                        )
                    )
                    payload = json.loads(str(mocked.call_args.args[0]))
            finally:
                os.chdir(previous)

            self.assertTrue(payload["ok"])
            self.assertEqual(2, payload["done"])
            self.assertTrue(
                first.read_text(encoding="utf-8").startswith("# === ANCHOR:")
            )
            self.assertTrue(
                second.read_text(encoding="utf-8").startswith("# === ANCHOR:")
            )

    def test_doctor_fix_skips_empty_init_but_anchors_logic_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            empty_init = pkg / "__init__.py"
            logic_file = root / "main.py"
            empty_init.write_text("", encoding="utf-8")
            logic_file.write_text("print('hello')\n", encoding="utf-8")

            _run_fix(root)

            self.assertEqual("", empty_init.read_text(encoding="utf-8"))
            self.assertTrue(
                logic_file.read_text(encoding="utf-8").startswith("# === ANCHOR:")
            )

    def test_analysis_cache_schema_bumped_to_2(self):
        from vibelign.core.analysis_cache import ANALYSIS_CACHE_SCHEMA

        self.assertEqual(2, ANALYSIS_CACHE_SCHEMA)

    def test_run_vib_doctor_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "vibelign.commands.vib_doctor_cmd.print_ai_response"
                ) as mocked:
                    run_vib_doctor(
                        Namespace(
                            json=False,
                            strict=False,
                            detailed=False,
                            fix_hints=False,
                            write_report=False,
                        )
                    )
                    mocked.assert_called_once()
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
