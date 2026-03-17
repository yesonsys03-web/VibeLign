# === ANCHOR: WATCH_STATE_START ===
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json

@dataclass
# === ANCHOR: WATCH_STATE_FILESNAPSHOT_START ===
class FileSnapshot:
    path: str
    lines: int
    sha1: str
# === ANCHOR: WATCH_STATE_FILESNAPSHOT_END ===

# === ANCHOR: WATCH_STATE_HASH_TEXT_START ===
def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
# === ANCHOR: WATCH_STATE_HASH_TEXT_END ===

# === ANCHOR: WATCH_STATE_LOAD_STATE_START ===
def load_state(path: Path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: FileSnapshot(**v) for k, v in data.items()}
    except Exception:
        return {}
# === ANCHOR: WATCH_STATE_LOAD_STATE_END ===

# === ANCHOR: WATCH_STATE_SAVE_STATE_START ===
def save_state(path: Path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: asdict(v) for k, v in state.items()}, indent=2), encoding="utf-8")
# === ANCHOR: WATCH_STATE_SAVE_STATE_END ===
# === ANCHOR: WATCH_STATE_END ===
