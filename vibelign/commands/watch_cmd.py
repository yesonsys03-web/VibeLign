# === ANCHOR: WATCH_CMD_START ===
from argparse import Namespace
from pathlib import Path
from collections.abc import Callable
from typing import cast


from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: WATCH_CMD_RUN_WATCH_CMD_START ===
def run_watch_cmd(args: Namespace) -> None:
    from vibelign.core import watch_engine as watch_engine_mod

    run_watch_obj = cast(object, watch_engine_mod.run_watch)
    run_watch = cast(Callable[[dict[str, object]], None], run_watch_obj)
    try:
        run_watch(
            {
                "strict": bool(getattr(args, "strict", False)),
                "write_log": bool(getattr(args, "write_log", False)),
                "json": bool(getattr(args, "json", False)),
                "debounce_ms": int(getattr(args, "debounce_ms", 0) or 0),
                "root": str(Path.cwd()),
            }
        )
    except RuntimeError as e:
        print(str(e))


# === ANCHOR: WATCH_CMD_RUN_WATCH_CMD_END ===
# === ANCHOR: WATCH_CMD_END ===
