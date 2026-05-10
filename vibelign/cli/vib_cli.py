# === ANCHOR: VIB_CLI_START ===
import argparse
import importlib
import sys
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
        metavar="{install,init,start,checkpoint,undo,history,backup-db-viewer,backup-graph-summary,backup-db-maintenance,backup-cleanup,docs-build,docs-enhance,docs-index,doc-sources,protect,ask,config,doctor,anchor,patch,secrets,explain,recover,guard,claude-hook,export,scan,show,memory,plan-structure,transfer,watch,bench,manual,rules,completion}",
    )

    register_core_commands(
        sub, lazy_command_impl, cast(Callable[[object], None], run_init)
    )
    register_extended_commands(sub, lazy_command_impl, run_vib_guard)
    register_completion_command(sub, parser)
    _hide_suppressed_subcommands(parser)

    return parser


def _install_sigpipe_default_handler() -> None:
    """Unix 표준: 파이프 수신측이 닫히면 SIGPIPE 로 조용히 종료한다.

    `vib doctor | head -5` 처럼 출력이 잘릴 때 Python 의 기본 동작은
    print 가 BrokenPipeError 를 raise → cli runtime 이 캐치해서 통합 에러 로그에
    traceback 을 기록한다. 이는 실제 사용자 에러가 아니므로 표준 Unix 도구처럼
    SIGPIPE 의 기본 핸들러(프로세스 정상 종료)로 되돌려 노이즈를 줄인다.
    Windows 에는 SIGPIPE 자체가 없으므로 no-op.
    """
    if sys.platform == "win32":
        return
    try:
        import signal

        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, OSError, ValueError):
        # 일부 환경(임베디드 stdin/stdout 재정의 등)에서는 signal 등록이
        # 실패할 수 있다. 그럴 땐 기존 BrokenPipeError 경로로 폴백.
        pass


def main() -> None:
    _install_sigpipe_default_handler()
    run_cli = cast(
        Callable[[Callable[[], argparse.ArgumentParser]], None],
        importlib.import_module("vibelign.cli.cli_runtime").run_cli,
    )
    run_cli(build_parser)


if __name__ == "__main__":
    main()
# === ANCHOR: VIB_CLI_END ===
