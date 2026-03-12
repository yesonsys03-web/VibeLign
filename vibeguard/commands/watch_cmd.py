from pathlib import Path

def run_watch_cmd(args):
    from vibeguard.core.watch_engine import run_watch
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
