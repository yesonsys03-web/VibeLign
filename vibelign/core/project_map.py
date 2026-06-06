# === ANCHOR: PROJECT_MAP_START ===
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from vibelign.core.meta_paths import MetaPaths


SUPPORTED_PROJECT_MAP_SCHEMA = 3


@dataclass(frozen=True)
# === ANCHOR: PROJECT_MAP_PROJECTMAPSNAPSHOT_START ===
class ProjectMapSnapshot:
    schema_version: int
    project_name: str
    entry_files: frozenset[str]
    ui_modules: frozenset[str]
    core_modules: frozenset[str]
    service_modules: frozenset[str]
    large_files: frozenset[str]
    file_count: int
    generated_at: str | None
    anchor_index: dict[str, list[str]] = field(default_factory=dict)
    tree: list[str] = field(default_factory=list)
    files: dict[str, dict[str, object]] = field(default_factory=dict)

    # === ANCHOR: PROJECT_MAP_CLASSIFY_PATH_START ===
    def classify_path(self, rel_path: str) -> str | None:
        if rel_path in self.entry_files:
            return "entry file"
        if rel_path in self.ui_modules:
            return "ui"
        if rel_path in self.service_modules:
            return "service"
        if rel_path in self.core_modules:
            return "logic"
        file_entry = self.files.get(rel_path)
        if isinstance(file_entry, dict):
            category = file_entry.get("category")
            if category == "entry":
                return "entry file"
            if category == "ui":
                return "ui"
            if category == "service":
                return "service"
            if category == "core":
                return "logic"
        return None

    # === ANCHOR: PROJECT_MAP_CLASSIFY_PATH_END ===

    # === ANCHOR: PROJECT_MAP_ANCHOR_PRIORITY_START ===
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
        # === ANCHOR: PROJECT_MAP_PROJECTMAPSNAPSHOT_END ===
        if rel_path in self.core_modules:
            score += 2
        return score

    # === ANCHOR: PROJECT_MAP_ANCHOR_PRIORITY_END ===


# === ANCHOR: PROJECT_MAP_LOAD_PROJECT_MAP_START ===
def load_project_map(root: Path) -> tuple[ProjectMapSnapshot | None, str | None]:
    meta = MetaPaths(root)
    if not meta.project_map_path.exists():
        return None, None
    try:
        loaded = cast(
            object, json.loads(meta.project_map_path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError):
        return None, "invalid_project_map"
    if not isinstance(loaded, dict):
        return None, "invalid_project_map"
    payload = cast(dict[str, object], loaded)

    schema_version = payload.get("schema_version")
    if schema_version not in (1, 2, 3):
        return None, "unsupported_project_map_schema"
    from vibelign.core.anchor_tools import rehydrate_anchor_spans

    # === ANCHOR: PROJECT_MAP__VALUES_START ===
    def _values(name: str) -> frozenset[str]:
        raw = payload.get(name, [])
        if not isinstance(raw, list):
            return frozenset()
        return frozenset(
            str(item) for item in cast(list[object], raw) if isinstance(item, str)
        )

    # === ANCHOR: PROJECT_MAP__VALUES_END ===

    file_count = payload.get("file_count", 0)
    raw_anchor_index = payload.get("anchor_index", {})
    anchor_index = (
        {
            key: [
                str(item) for item in cast(list[object], value) if isinstance(item, str)
            ]
            for key, value in cast(dict[str, object], raw_anchor_index).items()
            if isinstance(value, list)
        }
        if isinstance(raw_anchor_index, dict)
        else {}
    )
    raw_tree = payload.get("tree", [])
    tree = (
        [str(item) for item in cast(list[object], raw_tree)]
        if isinstance(raw_tree, list)
        else []
    )
    raw_files = payload.get("files", {})
    files: dict[str, dict[str, object]] = (
        {
            key: cast(dict[str, object], value)
            for key, value in cast(dict[str, object], raw_files).items()
            if isinstance(value, dict)
        }
        if isinstance(raw_files, dict)
        else {}
    )

    # 슬림화: project_map.json 은 anchor_spans 만 저장하고(압축 "NAME:start-end" 형식),
    # files[].anchors 와 최상위 anchor_index 는 저장하지 않는다. 로드 시 압축 span 을
    # 객체({name,start,end})로 복원하고 anchors/anchor_index 를 파생해, 소비처
    # (structure_planner / recovery.signals)가 그대로 동작하게 한다.
    # 구버전 맵(객체 span / 키 보유)도 그대로 호환한다.
    for entry in files.values():
        raw_spans = entry.get("anchor_spans")
        spans = rehydrate_anchor_spans(
            cast(list[object], raw_spans) if isinstance(raw_spans, list) else []
        )
        entry["anchor_spans"] = spans
        existing = entry.get("anchors")
        if isinstance(existing, list) and existing:
            continue
        entry["anchors"] = [
            name for span in spans if isinstance((name := span.get("name")), str)
        ]
    if not anchor_index:
        anchor_index = {
            path: cast(list[str], anchors_val)
            for path, entry in files.items()
            if isinstance((anchors_val := entry.get("anchors")), list) and anchors_val
        }

    return (
        ProjectMapSnapshot(
            schema_version=schema_version,
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
            anchor_index=anchor_index,
            tree=tree,
            files=files,
        ),
        # === ANCHOR: PROJECT_MAP_LOAD_PROJECT_MAP_END ===
        None,
    )


# === ANCHOR: PROJECT_MAP_ENRICH_CHANGE_KIND_START ===
def enrich_change_kind(
    snapshot: ProjectMapSnapshot | None,
    rel_path: str,
    fallback_kind: str,
    # === ANCHOR: PROJECT_MAP_ENRICH_CHANGE_KIND_END ===
) -> str:
    if fallback_kind == "command":
        return fallback_kind
    if snapshot is None:
        return fallback_kind
    return snapshot.classify_path(rel_path) or fallback_kind


# === ANCHOR: PROJECT_MAP_END ===
