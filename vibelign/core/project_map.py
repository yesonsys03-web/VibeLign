from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vibelign.core.meta_paths import MetaPaths


SUPPORTED_PROJECT_MAP_SCHEMA = 1


@dataclass(frozen=True)
class ProjectMapSnapshot:
    schema_version: int
    project_name: str
    entry_files: frozenset[str]
    ui_modules: frozenset[str]
    core_modules: frozenset[str]
    service_modules: frozenset[str]
    large_files: frozenset[str]
    file_count: int
    generated_at: Optional[str]

    def classify_path(self, rel_path: str) -> Optional[str]:
        if rel_path in self.entry_files:
            return "entry file"
        if rel_path in self.ui_modules:
            return "ui"
        if rel_path in self.service_modules:
            return "service"
        if rel_path in self.core_modules:
            return "logic"
        return None

    def anchor_priority(self, rel_path: str) -> int:
        score = 0
        if rel_path in self.large_files:
            score += 5
        if rel_path in self.entry_files:
            score += 4
        if rel_path in self.ui_modules:
            score += 3
        if rel_path in self.service_modules:
            score += 2
        if rel_path in self.core_modules:
            score += 2
        return score


def load_project_map(root: Path) -> tuple[Optional[ProjectMapSnapshot], Optional[str]]:
    meta = MetaPaths(root)
    if not meta.project_map_path.exists():
        return None, None
    try:
        payload = json.loads(meta.project_map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "invalid_project_map"

    schema_version = payload.get("schema_version")
    if schema_version != SUPPORTED_PROJECT_MAP_SCHEMA:
        return None, "unsupported_project_map_schema"

    def _values(name: str) -> frozenset[str]:
        raw = payload.get(name, [])
        if not isinstance(raw, list):
            return frozenset()
        return frozenset(str(item) for item in raw if isinstance(item, str))

    file_count = payload.get("file_count", 0)
    return (
        ProjectMapSnapshot(
            schema_version=SUPPORTED_PROJECT_MAP_SCHEMA,
            project_name=str(payload.get("project_name", root.name)),
            entry_files=_values("entry_files"),
            ui_modules=_values("ui_modules"),
            core_modules=_values("core_modules"),
            service_modules=_values("service_modules"),
            large_files=_values("large_files"),
            file_count=file_count if isinstance(file_count, int) else 0,
            generated_at=(
                str(payload.get("generated_at"))
                if isinstance(payload.get("generated_at"), str)
                else None
            ),
        ),
        None,
    )


def enrich_change_kind(
    snapshot: Optional[ProjectMapSnapshot], rel_path: str, fallback_kind: str
) -> str:
    if snapshot is None:
        return fallback_kind
    return snapshot.classify_path(rel_path) or fallback_kind
