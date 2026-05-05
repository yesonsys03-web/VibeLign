import unittest
from typing import cast

from vibelign.cli.cli_completion import generate_completion_script, generate_powershell_script
from vibelign.cli.vib_cli import build_parser


class VibCliCompletionTest(unittest.TestCase):
    def test_build_parser_registers_completion_command(self) -> None:
        parser = build_parser()
        subparser_action = next(
            action for action in parser._actions if getattr(action, "choices", None)
        )
        choices = cast(dict[str, object], subparser_action.choices)
        self.assertIn("completion", choices)

    def test_completion_script_mentions_completion_command(self) -> None:
        parser = build_parser()
        script = generate_completion_script(parser)
        self.assertIn("completion", script)
        self.assertIn("_vib_completions", script)

    def test_completion_script_includes_memory_nested_completions(self) -> None:
        parser = build_parser()
        script = generate_completion_script(parser)

        self.assertIn("memory) opts=\"show review intent decide next relevant", script)
        self.assertIn("proposal-create", script)
        self.assertIn("--first-next-action", script)
        self.assertIn("--draft-json", script)
        self.assertIn("--proposal-hash", script)

    def test_powershell_completion_includes_memory_nested_completions(self) -> None:
        parser = build_parser()
        script = generate_powershell_script(parser)

        self.assertIn("'memory' = @('show', 'review', 'intent'", script)
        self.assertIn("'proposal-create'", script)
        self.assertIn("'--first-next-action'", script)
        self.assertIn("'--draft-json'", script)
        self.assertIn("'--proposal-hash'", script)


if __name__ == "__main__":
    _ = unittest.main()
