import argparse
import importlib
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch
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

    def test_run_cli_records_unhandled_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()

            def run_boom(_: object) -> None:
                raise RuntimeError("boom")

            def build_parser() -> argparse.ArgumentParser:
                parser = argparse.ArgumentParser()
                sub = parser.add_subparsers(dest="command", required=True)
                parser_boom = sub.add_parser("boom")
                parser_boom.set_defaults(func=run_boom)
                return parser

            with (
                patch("sys.argv", ["vib", "boom"]),
                patch("pathlib.Path.cwd", return_value=root),
            ):
                with self.assertRaises(RuntimeError):
                    cli_runtime.run_cli(build_parser)

            files = list((root / ".vibelign" / "logs").glob("cli-error-*.jsonl"))
            self.assertEqual(1, len(files))


if __name__ == "__main__":
    _ = unittest.main()
