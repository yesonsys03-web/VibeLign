from __future__ import annotations

from pathlib import Path


def find_parent_vibelign_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".vibelign").exists():
            return candidate
    return None


def resolve_project_root(start: Path) -> Path:
    return find_parent_vibelign_root(start) or start.resolve()
