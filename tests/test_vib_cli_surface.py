import unittest
from typing import Any, cast

from vibelign.commands.vib_init_cmd import run_vib_init_cli
from vibelign.vib_cli import build_parser


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
            {"protect", "ask", "config", "export", "watch", "start"}.issubset(commands)
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
        self.assertIs(args.func, run_vib_init_cli)


if __name__ == "__main__":
    unittest.main()
