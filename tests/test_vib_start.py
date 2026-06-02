import json
import tempfile
import types
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.cli import build_parser as build_basic_parser
from vibelign.commands.export_cmd import export_tool_files
from vibelign.commands.vib_start_cmd import (
    VIB_START_PROGRESS_LABELS,
    _ensure_gitignore_entry,
    _ensure_rule_files,
    _emit_start_progress,
    _next_step,
    _parse_start_tools,
    _register_mcp_cursor,
    _selected_start_tools,
    _status_line,
    _tool_readiness,
)
from vibelign.core.auto_install import ensure_pyproject_toml
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

    def test_ensure_gitignore_entry_includes_rust_backup_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            _ensure_gitignore_entry(root)
            _ensure_gitignore_entry(root)

            lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines.count(".vibelign/checkpoints/"), 1)
            self.assertEqual(lines.count(".vibelign/rust_checkpoints/"), 1)
            self.assertEqual(lines.count(".vibelign/rust_objects/"), 1)
            self.assertEqual(lines.count(".vibelign/scan_cache.json"), 1)

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

    def test_vib_cli_start_parser_accepts_non_interactive(self):
        parser = build_vib_parser()
        args = parser.parse_args(["start", "--non-interactive"])
        self.assertTrue(args.non_interactive)

    def test_basic_cli_start_parser_accepts_non_interactive(self):
        parser = build_basic_parser()
        args = parser.parse_args(["start", "--non-interactive"])
        self.assertTrue(args.non_interactive)

    def test_emit_start_progress_outputs_json_marker(self):
        with patch("builtins.print") as mocked_print:
            _emit_start_progress(2)

        payload = json.loads(mocked_print.call_args.args[0])
        self.assertEqual(payload["type"], "vib_start_progress")
        self.assertEqual(payload["step"], 2)
        self.assertEqual(payload["total"], 5)
        self.assertEqual(payload["label"], VIB_START_PROGRESS_LABELS[1])

    def test_start_progress_labels_do_not_expose_internal_terms(self):
        forbidden_terms = ("watch", "anchor", "guard", "vib start")
        joined = "\n".join(VIB_START_PROGRESS_LABELS).lower()
        for term in forbidden_terms:
            self.assertNotIn(term, joined)

    def test_ensure_pyproject_non_interactive_skips_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages: list[str] = []
            with patch("builtins.input", side_effect=AssertionError("input called")):
                created = ensure_pyproject_toml(
                    root,
                    messages.append,
                    messages.append,
                    messages.append,
                    interactive=False,
                )

            self.assertFalse(created)
            self.assertFalse((root / "pyproject.toml").exists())
            self.assertTrue(any("건너뜀" in message for message in messages))

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

    def test_build_project_map_uses_opt_in_rust_project_scan_cache_path(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            _ = (root / "ignored.py").write_text("print('skip')\n", encoding="utf-8")

            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "1"}, clear=False), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {"path": "main.py", "category": "entry", "imports": []},
                        ],
                    },
                    None,
                ),
            ) as rust_scan:
                pm = _build_project_map(root, force_scan=True)

        files = cast(dict[str, object], pm["files"])
        self.assertEqual(pm["file_count"], 1)
        self.assertIn("main.py", files)
        self.assertNotIn("ignored.py", files)
        rust_scan.assert_called_once_with(root)

    def test_build_project_map_preserves_scan_cache_schema_with_rust_project_scan(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "main.py").write_text(
                "# === ANCHOR: MAIN_START ===\nprint('ok')\n# === ANCHOR: MAIN_END ===\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {"path": "main.py", "category": "entry", "imports": []},
                        ],
                    },
                    None,
                ),
            ) as rust_scan:
                _ = _build_project_map(root, force_scan=True)

            cache_payload = cast(
                dict[str, object],
                json.loads((root / ".vibelign" / "scan_cache.json").read_text(encoding="utf-8")),
            )
            entries = cast(dict[str, dict[str, object]], cache_payload["entries"])
            main_entry = entries["main.py"]

        self.assertEqual(cache_payload["schema_version"], 2)
        self.assertEqual(set(entries), {"main.py"})
        self.assertEqual(main_entry["category"], "entry")
        self.assertEqual(main_entry["anchors"], ["MAIN"])
        self.assertIn("mtime", main_entry)
        self.assertIn("size", main_entry)
        self.assertIn("anchor_spans", main_entry)
        self.assertIn("imports", main_entry)
        self.assertIn("line_count", main_entry)
        rust_scan.assert_called_once_with(root)

    def test_build_project_map_uses_rust_project_scan_metadata_when_available(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "feature.py").write_text(
                "import python_side\nprint('ok')\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {
                                "path": "feature.py",
                                "category": "service",
                                "imports": ["rust.side"],
                            },
                        ],
                    },
                    None,
                ),
            ) as rust_scan:
                pm = _build_project_map(root, force_scan=True)

            cache_payload = cast(
                dict[str, object],
                json.loads((root / ".vibelign" / "scan_cache.json").read_text(encoding="utf-8")),
            )
            entries = cast(dict[str, dict[str, object]], cache_payload["entries"])

        files = cast(dict[str, dict[str, object]], pm["files"])
        feature = files["feature.py"]
        feature_cache = entries["feature.py"]
        self.assertEqual(feature["category"], "service")
        self.assertEqual(feature_cache["imports"], ["rust.side"])
        rust_scan.assert_called_once_with(root)

    def test_build_project_map_anchor_fields_match_python_path_under_rust_scan(self):
        from vibelign.commands.vib_start_cmd import _build_project_map

        with tempfile.TemporaryDirectory() as rust_tmp, tempfile.TemporaryDirectory() as python_tmp:
            rust_root = Path(rust_tmp)
            python_root = Path(python_tmp)
            rel = "core/service.py"
            content = (
                "# === ANCHOR: CORE_SERVICE_START ===\n"
                "def run():\n"
                "    return True\n"
                "# === ANCHOR: CORE_SERVICE_END ===\n"
            )
            for root in (rust_root, python_root):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                _ = path.write_text(content, encoding="utf-8")

            with patch.dict("os.environ", {}, clear=True), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {"path": rel, "category": "core", "imports": []},
                        ],
                    },
                    None,
                ),
            ) as rust_scan:
                rust_map = _build_project_map(rust_root, force_scan=True)

            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "0"}, clear=False), patch(
                "vibelign.core.fast_tools.has_fd", return_value=False
            ):
                python_map = _build_project_map(python_root, force_scan=True)

        rust_files = cast(dict[str, dict[str, object]], rust_map["files"])
        python_files = cast(dict[str, dict[str, object]], python_map["files"])
        self.assertEqual(rust_map["anchor_index"], python_map["anchor_index"])
        self.assertEqual(rust_files[rel]["anchors"], python_files[rel]["anchors"])
        self.assertEqual(rust_files[rel]["anchor_spans"], python_files[rel]["anchor_spans"])
        rust_scan.assert_called_once_with(rust_root)


if __name__ == "__main__":
    unittest.main()
