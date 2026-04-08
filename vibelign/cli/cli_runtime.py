# === ANCHOR: CLI_RUNTIME_START ===
import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from typing import cast


# === ANCHOR: CLI_RUNTIME__CONFIGURE_WINDOWS_CONSOLE_START ===
def _configure_windows_console() -> None:
    if sys.platform != "win32":
        return
    try:
        stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
        stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
        if callable(stdout_reconfigure):
            _ = stdout_reconfigure(encoding="utf-8", errors="replace")
        if callable(stderr_reconfigure):
            _ = stderr_reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
# === ANCHOR: CLI_RUNTIME__CONFIGURE_WINDOWS_CONSOLE_END ===


# === ANCHOR: CLI_RUNTIME_RUN_CLI_START ===
def run_cli(build_parser: Callable[[], argparse.ArgumentParser]) -> None:
    _configure_windows_console()

    parser = build_parser()
    if len(sys.argv) == 2 and sys.argv[1] == "completion" and not sys.stdout.isatty():
        generate_completion_script = cast(
            Callable[[argparse.ArgumentParser], str],
            importlib.import_module(
                "vibelign.cli.cli_completion"
            ).generate_completion_script,
        )
        print(generate_completion_script(parser))
        return

    args = parser.parse_args()
    func = cast(Callable[[object], None], args.func)
    func(args)
# === ANCHOR: CLI_RUNTIME_RUN_CLI_END ===


# === ANCHOR: CLI_RUNTIME_RUN_CLI_WITH_ARGS_START ===
def run_cli_with_args(
    build_parser: Callable[[], argparse.ArgumentParser], argv: Sequence[str]
# === ANCHOR: CLI_RUNTIME_RUN_CLI_WITH_ARGS_END ===
) -> object:
    parser = build_parser()
    args = parser.parse_args(list(argv))
    func = cast(Callable[[object], object], args.func)
    return func(args)
# === ANCHOR: CLI_RUNTIME_END ===
