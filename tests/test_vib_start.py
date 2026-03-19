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
    _selected_start_tools,
    _status_line,
    _tool_readiness,
)
from vibelign.vib_cli import build_parser as build_vib_parser


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

    def test_tool_readiness_uses_ready_and_almost_ready_groups(self):
        readiness = _tool_readiness(
            ["claude", "opencode", "cursor", "antigravity", "codex"]
        )

        self.assertEqual(
            readiness["ready"],
            ["Claude", "OpenCode", "Antigravity"],
        )
        self.assertEqual(readiness["almost_ready"], ["Cursor", "Codex"])

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


if __name__ == "__main__":
    unittest.main()
