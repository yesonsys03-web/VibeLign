# === ANCHOR: VIB_CLI_START ===
import argparse
import importlib
from collections.abc import Callable
from typing import Any, cast

from ..commands.init_cmd import run_init


def _hide_suppressed_subcommands(parser: argparse.ArgumentParser) -> None:
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        choice_actions = getattr(action, "_choices_actions", None)
        if not choices or choice_actions is None:
            continue
        typed_action = cast(Any, action)
        typed_action._choices_actions = [
            item
            for item in choice_actions
            if getattr(item, "help", None) != argparse.SUPPRESS
        ]


def build_parser() -> argparse.ArgumentParser:
    cli_base = importlib.import_module("vibelign.cli.cli_base")
    main_description = cast(str, cli_base.MAIN_DESCRIPTION)
    main_epilog = cast(str, cli_base.MAIN_EPILOG)
    rich_argument_parser = cast(
        type[argparse.ArgumentParser], cli_base.RichArgumentParser
    )
    lazy_command_impl = cast(
        Callable[[str, str], Callable[[object], None]],
        cli_base.lazy_command,
    )
    run_vib_guard = cast(
        Callable[[object], None],
        importlib.import_module("vibelign.commands.vib_guard_cmd").run_vib_guard,
    )
    register_core_commands = cast(
        Callable[
            [
                object,
                Callable[[str, str], Callable[[object], None]],
                Callable[[object], None],
            ],
            None,
        ],
        importlib.import_module(
            "vibelign.cli.cli_core_commands"
        ).register_core_commands,
    )
    register_extended_commands = cast(
        Callable[
            [
                object,
                Callable[[str, str], Callable[[object], None]],
                Callable[[object], None],
            ],
            None,
        ],
        importlib.import_module(
            "vibelign.cli.cli_command_groups"
        ).register_extended_commands,
    )
    register_completion_command = cast(
        Callable[[object, argparse.ArgumentParser], None],
        importlib.import_module(
            "vibelign.cli.cli_completion"
        ).register_completion_command,
    )

    parser = rich_argument_parser(
        prog="vib",
        description=main_description,
        epilog=main_epilog,
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=rich_argument_parser,
        metavar="{install,init,start,checkpoint,undo,history,docs-build,docs-index,protect,ask,config,doctor,anchor,patch,secrets,explain,guard,claude-hook,export,scan,plan-structure,transfer,watch,bench,manual,rules,completion}",
    )

    register_core_commands(
        sub, lazy_command_impl, cast(Callable[[object], None], run_init)
    )
    register_extended_commands(sub, lazy_command_impl, run_vib_guard)
    register_completion_command(sub, parser)
    _hide_suppressed_subcommands(parser)

    return parser


def main() -> None:
    run_cli = cast(
        Callable[[Callable[[], argparse.ArgumentParser]], None],
        importlib.import_module("vibelign.cli.cli_runtime").run_cli,
    )
    run_cli(build_parser)


if __name__ == "__main__":
    main()
# === ANCHOR: VIB_CLI_END ===
