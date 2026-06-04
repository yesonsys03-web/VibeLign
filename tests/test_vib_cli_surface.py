import unittest
from collections.abc import Callable
from typing import Any, Protocol, cast

from vibelign.commands.init_cmd import run_init
from vibelign.cli.vib_cli import build_parser


class _RecoverCliArgs(Protocol):
    explain: bool
    preview: bool
    file: str | None
    apply: bool
    checkpoint_id: str
    sandwich_checkpoint_id: str
    confirmation: str
    func: Callable[[object], None]


class _MemoryCliArgs(Protocol):
    memory_action: str
    func: Callable[[object], None]


class _McpCliArgs(Protocol):
    mcp_action: str
    capability: str
    tool: str
    func: Callable[[object], None]


class _BenchCliArgs(Protocol):
    generate: bool
    score: bool
    report: bool
    func: Callable[[object], None]


class VibCliSurfaceTest(unittest.TestCase):
    def test_vib_cli_excludes_patch_and_keeps_supported_commands(self):
        parser = build_parser()
        subparsers_action = cast(
            Any,
            next(
                action for action in parser._actions if getattr(action, "choices", None)
            ),
        )
        commands = set(subparsers_action.choices.keys())
        self.assertNotIn("patch", commands)
        self.assertTrue(
            {
                "watch",
                "start",
                "checkpoint",
                "doctor",
                "guard",
                "anchor",
                "manual",
                "rules",
                "plan",
                "plan-structure",
            }.issubset(commands)
        )

    def test_vib_help_surface_mentions_visible_recent_commands(self):
        parser = build_parser()
        help_text = parser.format_help()

        for command in [
            "backup-db-viewer",
            "backup-graph-summary",
            "backup-db-maintenance",
            "backup-cleanup",
            "doc-sources",
            "show",
        ]:
            self.assertIn(command, help_text)

        usage_block = help_text.split("\n\n", maxsplit=1)[0]
        self.assertIn("backup-db-viewer", usage_block)
        self.assertIn("backup-graph-summary", usage_block)
        self.assertIn("backup-db-maintenance", usage_block)
        self.assertIn("backup-cleanup", usage_block)

    def test_vib_init_points_to_project_init_flow(self):
        parser = build_parser()
        subparsers_action = cast(
            Any,
            next(
                action for action in parser._actions if getattr(action, "choices", None)
            ),
        )
        init_parser = subparsers_action.choices["init"]
        args = init_parser.parse_args([])
        self.assertIs(args.func, run_init)

    def test_vib_watch_parser_accepts_auto_fix(self):
        parser = build_parser()
        args = parser.parse_args(["watch", "--auto-fix"])
        self.assertTrue(args.auto_fix)

    def test_vib_bench_rejects_removed_patch_mode(self):
        parser = build_parser()

        parsed = cast(object, parser.parse_args(["bench", "--generate"]))
        args = cast(_BenchCliArgs, parsed)
        self.assertTrue(args.generate)
        self.assertTrue(callable(args.func))

        subparsers_action = cast(
            Any,
            next(
                action for action in parser._actions if getattr(action, "choices", None)
            ),
        )
        bench_parser = subparsers_action.choices["bench"]
        help_text = bench_parser.format_help()
        self.assertIn("--generate", help_text)
        self.assertIn("--score", help_text)
        self.assertIn("--report", help_text)
        self.assertNotIn("--patch", help_text)
        self.assertNotIn("--update-baseline", help_text)

        with self.assertRaises(SystemExit):
            parser.parse_args(["bench", "--patch"])

    def test_vib_recover_parser_accepts_explain(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["recover", "--explain"]))
        args = cast(_RecoverCliArgs, parsed)
        self.assertTrue(args.explain)
        self.assertTrue(callable(args.func))

    def test_vib_recover_parser_accepts_preview(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["recover", "--preview"]))
        args = cast(_RecoverCliArgs, parsed)
        self.assertTrue(args.preview)
        self.assertTrue(callable(args.func))

    def test_vib_recover_parser_accepts_file_preview_target(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["recover", "--file", "src/app.py"]))
        args = cast(_RecoverCliArgs, parsed)
        self.assertEqual(args.file, "src/app.py")
        self.assertTrue(callable(args.func))

    def test_vib_recover_parser_accepts_explicit_apply_arguments(self):
        parser = build_parser()
        parsed = cast(
            object,
            parser.parse_args([
                "recover",
                "--file",
                "src/app.py",
                "--apply",
                "--checkpoint-id",
                "ckpt_before",
                "--sandwich-checkpoint-id",
                "ckpt_safety",
                "--confirmation",
                "APPLY ckpt_before",
            ]),
        )
        args = cast(_RecoverCliArgs, parsed)
        self.assertTrue(args.apply)
        self.assertEqual(args.checkpoint_id, "ckpt_before")
        self.assertEqual(args.sandwich_checkpoint_id, "ckpt_safety")
        self.assertEqual(args.confirmation, "APPLY ckpt_before")

    def test_vib_memory_parser_accepts_nested_actions(self):
        parser = build_parser()
        for action in ("show", "review"):
            parsed = cast(object, parser.parse_args(["memory", action]))
            args = cast(_MemoryCliArgs, parsed)
            self.assertEqual(args.memory_action, action)
            self.assertTrue(callable(args.func))

    def test_vib_memory_parser_accepts_explicit_write_actions(self):
        parser = build_parser()
        intent = parser.parse_args(["memory", "intent", "Confirmed goal"])
        decide = parser.parse_args(["memory", "decide", "Use memory core"])
        next_action = parser.parse_args(["memory", "next", "Rerun tests"])
        relevant = parser.parse_args(["memory", "relevant", "src/app.py", "main file"])

        self.assertEqual(intent.memory_action, "intent")
        self.assertEqual(decide.memory_action, "decide")
        self.assertEqual(next_action.memory_action, "next")
        self.assertEqual(relevant.memory_action, "relevant")
        self.assertTrue(callable(intent.func))
        self.assertTrue(callable(decide.func))
        self.assertTrue(callable(next_action.func))
        self.assertTrue(callable(relevant.func))

    def test_vib_mcp_parser_accepts_grant_action(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["mcp", "grant", "recovery_apply", "--tool", "claude"]))
        args = cast(_McpCliArgs, parsed)

        self.assertEqual(args.mcp_action, "grant")
        self.assertEqual(args.capability, "recovery_apply")
        self.assertEqual(args.tool, "claude")
        self.assertTrue(callable(args.func))

    def test_vib_mcp_parser_accepts_grants_action(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["mcp", "grants"]))
        args = cast(_McpCliArgs, parsed)

        self.assertEqual(args.mcp_action, "grants")
        self.assertTrue(callable(args.func))

    def test_vib_mcp_parser_accepts_revoke_action(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["mcp", "revoke", "recovery_apply", "--tool", "claude"]))
        args = cast(_McpCliArgs, parsed)

        self.assertEqual(args.mcp_action, "revoke")
        self.assertEqual(args.capability, "recovery_apply")
        self.assertEqual(args.tool, "claude")
        self.assertTrue(callable(args.func))


if __name__ == "__main__":
    _ = unittest.main()
