# === ANCHOR: WATCH_CMD_START ===
from pathlib import Path


from vibelign.terminal_render import cli_print
print = cli_print

# === ANCHOR: WATCH_CMD_RUN_WATCH_CMD_START ===
def run_watch_cmd(args):
    from vibelign.core.watch_engine import run_watch
    try:
        run_watch({
            "strict": args.strict,
            "write_log": args.write_log,
            "json": args.json,
            "debounce_ms": args.debounce_ms,
            "root": str(Path.cwd()),
        })
    except RuntimeError as e:
        print(str(e))
# === ANCHOR: WATCH_CMD_RUN_WATCH_CMD_END ===
# === ANCHOR: WATCH_CMD_END ===
