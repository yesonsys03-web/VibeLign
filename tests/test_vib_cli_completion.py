import unittest

from vibelign.cli.cli_completion import generate_completion_script
from vibelign.cli.vib_cli import build_parser


class VibCliCompletionTest(unittest.TestCase):
    def test_build_parser_registers_completion_command(self) -> None:
        parser = build_parser()
        subparser_action = next(
            action for action in parser._actions if getattr(action, "choices", None)
        )
        self.assertIn("completion", subparser_action.choices)

    def test_completion_script_mentions_completion_command(self) -> None:
        parser = build_parser()
        script = generate_completion_script(parser)
        self.assertIn("completion", script)
        self.assertIn("_vib_completions", script)


if __name__ == "__main__":
    _ = unittest.main()
