# === ANCHOR: WATCH_REPORTER_START ===
from pathlib import Path
from datetime import datetime
import json
from typing import TypedDict


from vibelign.terminal_render import cli_print

print = cli_print


class WatchEvent(TypedDict, total=False):
    level: str
    message: str
    why: str
    action: str


# === ANCHOR: WATCH_REPORTER_EMIT_START ===
def emit(
    event: WatchEvent, json_mode: bool = False, log_path: Path | None = None
) -> None:
    if json_mode:
        line = json.dumps(event, ensure_ascii=False)
    else:
        line = f"[{event.get('level', 'INFO')}] {event.get('message', '')}"
        if event.get("why"):
            line += f"\n왜 중요한가: {event.get('why', '')}"
        if event.get("action"):
            line += f"\n권장 조치: {event.get('action', '')}"
    print(line, flush=True)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        with log_path.open("a", encoding="utf-8") as f:
            _ = f.write(f"{ts} {json.dumps(event, ensure_ascii=False)}\n")


# === ANCHOR: WATCH_REPORTER_EMIT_END ===
# === ANCHOR: WATCH_REPORTER_END ===
