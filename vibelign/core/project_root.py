# === ANCHOR: PROJECT_ROOT_START ===
from __future__ import annotations

from pathlib import Path


# === ANCHOR: PROJECT_ROOT_FIND_PARENT_VIBELIGN_ROOT_START ===
def find_parent_vibelign_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".vibelign").exists():
            return candidate
    return None
# === ANCHOR: PROJECT_ROOT_FIND_PARENT_VIBELIGN_ROOT_END ===


# === ANCHOR: PROJECT_ROOT_RESOLVE_PROJECT_ROOT_START ===
def resolve_project_root(start: Path) -> Path:
    return find_parent_vibelign_root(start) or start.resolve()
# === ANCHOR: PROJECT_ROOT_RESOLVE_PROJECT_ROOT_END ===
# === ANCHOR: PROJECT_ROOT_END ===
