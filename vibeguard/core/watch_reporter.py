from pathlib import Path
from datetime import datetime
import json

def emit(event, json_mode=False, log_path: Path | None = None):
    if json_mode:
        line = json.dumps(event, ensure_ascii=False)
    else:
        line = f"[{event.get('level', 'INFO')}] {event.get('message', '')}"
        if event.get("why"):
            line += f"\n왜 중요한가: {event['why']}"
        if event.get("action"):
            line += f"\n권장 조치: {event['action']}"
    print(line)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{ts} {json.dumps(event, ensure_ascii=False)}\n")
