# === ANCHOR: WATCH_STATE_START ===
from dataclasses import dataclass
from pathlib import Path
import hashlib, json
from typing import TypedDict, cast


class SnapshotPayload(TypedDict):
    path: str
    lines: int
    sha1: str


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
def load_state(path: Path) -> dict[str, FileSnapshot]:
    if not path.exists():
        return {}
    try:
        loaded = cast(object, json.loads(path.read_text(encoding="utf-8")))
        if not isinstance(loaded, dict):
            return {}
        data = cast(dict[str, object], loaded)
        state: dict[str, FileSnapshot] = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            payload = cast(dict[str, object], value)
            raw_path = payload.get("path")
            raw_lines = payload.get("lines")
            raw_sha1 = payload.get("sha1")
            if (
                isinstance(raw_path, str)
                and isinstance(raw_lines, int)
                and isinstance(raw_sha1, str)
            ):
                state[key] = FileSnapshot(path=raw_path, lines=raw_lines, sha1=raw_sha1)
        return state
    except Exception:
        return {}


# === ANCHOR: WATCH_STATE_LOAD_STATE_END ===


# === ANCHOR: WATCH_STATE_SAVE_STATE_START ===
def save_state(path: Path, state: dict[str, FileSnapshot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, SnapshotPayload] = {
        k: {"path": v.path, "lines": v.lines, "sha1": v.sha1} for k, v in state.items()
    }
    _ = path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# === ANCHOR: WATCH_STATE_SAVE_STATE_END ===
# === ANCHOR: WATCH_STATE_END ===
