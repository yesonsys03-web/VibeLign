import unittest
from collections.abc import Callable
from typing import Any, Protocol, cast

from vibelign.commands.init_cmd import run_init
from vibelign.cli.vib_cli import build_parser


class _RecoverCliArgs(Protocol):
    explain: bool
    func: Callable[[object], None]


class _MemoryCliArgs(Protocol):
    memory_action: str
    func: Callable[[object], None]


class VibCliSurfaceTest(unittest.TestCase):
    def test_vib_cli_includes_remaining_legacy_commands(self):
        parser = build_parser()
        subparsers_action = cast(
            Any,
            next(
                action for action in parser._actions if getattr(action, "choices", None)
            ),
        )
        commands = set(subparsers_action.choices.keys())
        self.assertTrue(
            {
                "protect",
                "ask",
                "config",
                "recover",
                "memory",
                "claude-hook",
                "export",
                "plan-structure",
                "watch",
                "start",
                "secrets",
            }.issubset(commands)
        )

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

    def test_vib_recover_parser_accepts_explain(self):
        parser = build_parser()
        parsed = cast(object, parser.parse_args(["recover", "--explain"]))
        args = cast(_RecoverCliArgs, parsed)
        self.assertTrue(args.explain)
        self.assertTrue(callable(args.func))

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
        relevant = parser.parse_args(["memory", "relevant", "src/app.py", "main file"])

        self.assertEqual(intent.memory_action, "intent")
        self.assertEqual(decide.memory_action, "decide")
        self.assertEqual(relevant.memory_action, "relevant")
        self.assertTrue(callable(intent.func))
        self.assertTrue(callable(decide.func))
        self.assertTrue(callable(relevant.func))


if __name__ == "__main__":
    _ = unittest.main()
