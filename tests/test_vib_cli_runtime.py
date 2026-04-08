import argparse
import importlib
import unittest
from collections.abc import Callable
from typing import cast


cli_runtime = importlib.import_module("vibelign.cli.cli_runtime")
run_cli_with_args = cast(
    Callable[[Callable[[], argparse.ArgumentParser], list[str]], object],
    cli_runtime.run_cli_with_args,
)


class VibCliRuntimeTest(unittest.TestCase):
    def test_run_cli_with_args_executes_selected_command(self) -> None:
        called: list[str] = []

        def run_alpha(_: object) -> None:
            called.append("alpha")

        def build_parser() -> argparse.ArgumentParser:
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            parser_a = sub.add_parser("alpha")
            parser_a.set_defaults(func=run_alpha)
            return parser

        _ = run_cli_with_args(build_parser, ["alpha"])

        self.assertEqual(called, ["alpha"])


if __name__ == "__main__":
    _ = unittest.main()
