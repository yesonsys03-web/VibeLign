from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json

@dataclass
class FileSnapshot:
    path: str
    lines: int
    sha1: str

def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def load_state(path: Path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: FileSnapshot(**v) for k, v in data.items()}
    except Exception:
        return {}

def save_state(path: Path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: asdict(v) for k, v in state.items()}, indent=2), encoding="utf-8")
