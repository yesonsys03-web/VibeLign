import tempfile
import types
import unittest
from pathlib import Path

from vibelign.cli import build_parser as build_basic_parser
from vibelign.commands.export_cmd import export_tool_files
from vibelign.commands.vib_start_cmd import (
    _ensure_rule_files,
    _next_step,
    _parse_start_tools,
    _register_mcp_cursor,
    _selected_start_tools,
    _status_line,
    _tool_readiness,
)
from vibelign.cli.vib_cli import build_parser as build_vib_parser


class VibStartTest(unittest.TestCase):
    def test_status_line_uses_simple_language(self):
        self.assertIn("좋아요", _status_line("Good"))
        self.assertIn("문제를 확인", _status_line("High Risk"))

    def test_next_step_uses_first_recommended_action(self):
        data = {
            "recommended_actions": ["vib anchor --suggest", "vib doctor --detailed"]
        }
        self.assertEqual(_next_step(data), "vib anchor --suggest")

    def test_parse_start_tools_normalizes_codex_aliases(self):
        self.assertEqual(
            _parse_start_tools("claude, antigravity, codex,opencode"),
            ["claude", "antigravity", "codex", "opencode"],
        )

    def test_parse_start_tools_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            _parse_start_tools("claude,unknown")

    def test_selected_start_tools_supports_all_tools_flag(self):
        args = types.SimpleNamespace(all_tools=True, tools=None)
        self.assertEqual(
            _selected_start_tools(args),
            ["claude", "opencode", "cursor", "antigravity", "codex"],
        )

    def test_tool_readiness_marks_all_tools_ready(self):
        # 5개 도구 모두 MCP 자동 등록 → 전부 ready 분류.
        readiness = _tool_readiness(
            ["claude", "opencode", "cursor", "antigravity", "codex"]
        )

        self.assertEqual(
            readiness["ready"],
            ["Claude", "OpenCode", "Cursor", "Antigravity", "Codex"],
        )
        self.assertEqual(readiness["almost_ready"], [])

    def test_register_mcp_cursor_creates_config_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            created = _register_mcp_cursor(root)

            self.assertTrue(created)
            config = root / ".cursor" / "mcp.json"
            self.assertTrue(config.exists())
            self.assertIn('"vibelign"', config.read_text(encoding="utf-8"))

    def test_register_mcp_cursor_merges_without_overwriting_existing_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / ".cursor"
            cursor_dir.mkdir()
            config = cursor_dir / "mcp.json"
            config.write_text(
                "{\n"
                '  "mcpServers": {\n'
                '    "existing": {"command": "demo", "args": ["--keep"]}\n'
                "  },\n"
                '  "theme": "light"\n'
                "}\n",
                encoding="utf-8",
            )

            created = _register_mcp_cursor(root)

            self.assertTrue(created)
            content = config.read_text(encoding="utf-8")
            self.assertIn('"existing"', content)
            self.assertIn('"vibelign"', content)
            self.assertIn('"theme": "light"', content)

    def test_register_mcp_cursor_skips_when_already_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / ".cursor"
            cursor_dir.mkdir()
            config = cursor_dir / "mcp.json"
            original = (
                "{\n"
                '  "mcpServers": {\n'
                '    "vibelign": {"command": "vibelign-mcp", "args": []},\n'
                '    "existing": {"command": "demo", "args": []}\n'
                "  }\n"
                "}\n"
            )
            config.write_text(original, encoding="utf-8")

            created = _register_mcp_cursor(root)

            self.assertFalse(created)
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_export_tool_files_creates_codex_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_tool_files(root, "codex")
            export_dir = root / "vibelign_exports" / "codex"
            self.assertTrue((export_dir / "TASK_ARTIFACT.md").exists())
            self.assertTrue((export_dir / "VERIFICATION_CHECKLIST.md").exists())
            self.assertTrue((export_dir / "SETUP.md").exists())

    def test_export_tool_files_preserves_existing_files_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_dir = root / "vibelign_exports" / "opencode"
            export_dir.mkdir(parents=True)
            rules_path = export_dir / "RULES.md"
            rules_path.write_text("keep me", encoding="utf-8")

            export_tool_files(root, "opencode", overwrite=False)

            self.assertEqual(rules_path.read_text(encoding="utf-8"), "keep me")

    def test_ensure_rule_files_preserves_existing_content_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents_path = root / "AGENTS.md"
            agents_path.write_text("custom", encoding="utf-8")

            result = _ensure_rule_files(root, overwrite=False)

            self.assertEqual(agents_path.read_text(encoding="utf-8"), "custom")
            self.assertNotIn("AGENTS.md", result["updated"])
            self.assertFalse((root / "AGENTS.md~").exists())

    def test_vib_cli_start_parser_accepts_tool_flags(self):
        parser = build_vib_parser()
        args = parser.parse_args(["start", "--tools", "claude,opencode"])
        self.assertEqual(args.tools, "claude,opencode")
        self.assertFalse(args.all_tools)
        self.assertFalse(args.force)

    def test_vib_cli_start_parser_accepts_force(self):
        parser = build_vib_parser()
        args = parser.parse_args(["start", "--all-tools", "--force"])
        self.assertTrue(args.all_tools)
        self.assertTrue(args.force)

    def test_basic_cli_start_parser_accepts_all_tools(self):
        parser = build_basic_parser()
        args = parser.parse_args(["start", "--all-tools"])
        self.assertTrue(args.all_tools)
        self.assertFalse(args.force)

    def test_basic_cli_watch_parser_accepts_auto_fix(self):
        parser = build_basic_parser()
        args = parser.parse_args(["watch", "--auto-fix"])
        self.assertTrue(args.auto_fix)

    def test_basic_cli_includes_claude_hook_command(self):
        parser = build_basic_parser()
        args = parser.parse_args(["claude-hook", "status"])
        self.assertEqual(args.command, "claude-hook")
        self.assertEqual(args.action, "status")

    def test_basic_cli_includes_plan_structure_command(self):
        parser = build_basic_parser()
        args = parser.parse_args(["plan-structure", "OAuth 인증 추가"])
        self.assertEqual(args.command, "plan-structure")
        self.assertEqual(args.feature, ["OAuth 인증 추가"])


class TestPagesRoutesUiClassification(unittest.TestCase):
    """C2 Part 1: pages/ and routes/ must classify as ui_modules.

    Without this, C2's layer-routing rule can't identify ui-layer callers
    in project_map.files[rel].imported_by.
    """

    def test_pages_directory_is_classified_as_ui(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pages").mkdir()
            (root / "pages" / "signup.py").write_text("def handle(): pass\n")
            pm = _build_project_map(root, force_scan=True)
            self.assertIn("pages/signup.py", pm["ui_modules"])

    def test_routes_directory_is_classified_as_ui(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "routes").mkdir()
            (root / "routes" / "users.py").write_text("def get(): pass\n")
            pm = _build_project_map(root, force_scan=True)
            self.assertIn("routes/users.py", pm["ui_modules"])


if __name__ == "__main__":
    unittest.main()
