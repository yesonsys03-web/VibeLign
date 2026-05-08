# === ANCHOR: CLI_RUNTIME_START ===
import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
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
    func = cast(Callable[[object], object], args.func)
    try:
        result = func(args)
    except Exception:
        _record_unhandled_cli_error()
        raise
    if isinstance(result, int):
        raise SystemExit(result)
# === ANCHOR: CLI_RUNTIME_RUN_CLI_END ===


def _record_unhandled_cli_error() -> None:
    try:
        from vibelign.core.error_log import record_cli_error
        from vibelign.core.project_root import resolve_project_root

        exc_type, exc_value, tb = sys.exc_info()
        if exc_type is None or exc_value is None:
            return
        record_cli_error(
            resolve_project_root(Path.cwd()),
            (exc_type, exc_value, tb),
            list(sys.argv),
        )
    except Exception as exc:
        _ = exc


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
