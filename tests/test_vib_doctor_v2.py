import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_start_cmd import run_vib_start
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.core.doctor_v2 import (
    build_doctor_envelope,
    render_doctor_markdown,
    DoctorV2Report,
)


class VibDoctorV2Test(unittest.TestCase):
    @staticmethod
    def _start_args() -> SimpleNamespace:
        return SimpleNamespace(all_tools=False, tools=None, force=False)

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
            data = envelope["data"]
            self.assertIn("project_score", data)
            self.assertIn("anchor_coverage", data)
            self.assertTrue(0 <= data["project_score"] <= 100)
            self.assertIn(
                data["status"], {"Safe", "Good", "Caution", "Risky", "High Risk"}
            )
            self.assertIn("project_map_loaded", data["stats"])

    def test_doctor_updates_last_scan_at_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_start(self._start_args())
                run_vib_doctor(
                    SimpleNamespace(
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

            stats = envelope["data"]["stats"]
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

            self.assertFalse(envelope["data"]["stats"]["project_map_loaded"])
            issues = envelope["data"]["issues"]
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

            data = envelope["data"]
            self.assertEqual(
                data["stats"]["mcp_status"]["cursor"]["state"], "not_configured"
            )
            self.assertTrue(
                any(
                    ".cursor/mcp.json에 vibelign MCP 등록이 없어요"
                    in str(item.get("found", ""))
                    for item in data["issues"]
                )
            )
            self.assertTrue(
                any(
                    "vib start --tools cursor" in action
                    for action in data["recommended_actions"]
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

            data = envelope["data"]
            self.assertEqual(
                data["stats"]["mcp_status"]["cursor"]["state"], "registered"
            )
            self.assertFalse(
                any(
                    ".cursor/mcp.json에 vibelign MCP 등록이 없어요"
                    in str(item.get("found", ""))
                    for item in data["issues"]
                )
            )

    def test_doctor_reports_partial_opencode_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "OPENCODE.md").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)

            data = envelope["data"]
            self.assertEqual(
                data["stats"]["prepared_tool_status"]["opencode"]["state"], "partial"
            )
            self.assertTrue(
                any(
                    "OpenCode 준비 파일이 일부 없어요" in str(item.get("found", ""))
                    for item in data["issues"]
                )
            )
            self.assertTrue(
                any(
                    "vib start --tools opencode" in action
                    for action in data["recommended_actions"]
                )
            )

    def test_doctor_issue_contains_structured_recovery_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 300, encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            issue = envelope["data"]["issues"][0]

            self.assertIn("severity", issue)
            self.assertIn("category", issue)
            self.assertIn("recommended_command", issue)
            self.assertIn("can_auto_fix", issue)
            self.assertIn("auto_fix_label", issue)

    def test_missing_cursor_mcp_issue_uses_mcp_category_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            issues = envelope["data"]["issues"]
            mcp_issue = next(i for i in issues if i["category"] == "mcp")

            self.assertEqual("high", mcp_issue["severity"])
            self.assertEqual("vib start --tools cursor", mcp_issue["recommended_command"])
            self.assertFalse(mcp_issue["can_auto_fix"])

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
                        SimpleNamespace(
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
