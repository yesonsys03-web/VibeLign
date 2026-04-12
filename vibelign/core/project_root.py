# === ANCHOR: PROJECT_ROOT_START ===
from __future__ import annotations

from pathlib import Path


# === ANCHOR: PROJECT_ROOT_FIND_PARENT_VIBELIGN_ROOT_START ===
def find_parent_vibelign_root(start: Path) -> Path | None:
    current = start.resolve()
    home = Path.home().resolve()
    for candidate in (current, *current.parents):
        if candidate == home:
            break
        if (candidate / ".vibelign").exists():
            return candidate
    return None
# === ANCHOR: PROJECT_ROOT_FIND_PARENT_VIBELIGN_ROOT_END ===


# === ANCHOR: PROJECT_ROOT_RESOLVE_PROJECT_ROOT_START ===
def resolve_project_root(start: Path) -> Path:
    import os
    env_root = os.environ.get("VIBELIGN_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return find_parent_vibelign_root(start) or start.resolve()
# === ANCHOR: PROJECT_ROOT_RESOLVE_PROJECT_ROOT_END ===
# === ANCHOR: PROJECT_ROOT_END ===
