import unittest
from typing import Any, cast

from vibelign.commands.init_cmd import run_init
from vibelign.cli.vib_cli import build_parser


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


if __name__ == "__main__":
    _ = unittest.main()
