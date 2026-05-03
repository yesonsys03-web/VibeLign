# === ANCHOR: RECOVERY_INTENT_ZONE_START ===
from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from .models import DriftCandidate, IntentZoneEntry, IntentZoneSource


# === ANCHOR: RECOVERY_INTENT_ZONE__BUILD_INTENT_ZONE_START ===
def build_intent_zone(
    *,
    explicit_relevant_paths: Iterable[str] = (),
    recent_patch_paths: Iterable[str] = (),
    changed_paths: Iterable[str] = (),
    project_map_categories: dict[str, str] | None = None,
    anchor_intents_by_path: dict[str, list[str]] | None = None,
) -> tuple[list[IntentZoneEntry], list[DriftCandidate]]:
    categories = project_map_categories or {}
    anchor_intents = anchor_intents_by_path or {}
    zone_by_path: dict[str, IntentZoneEntry] = {}
    for path in explicit_relevant_paths:
        _add_zone_entry(zone_by_path, path, "explicit", "explicit relevant_files entry")
    for path in recent_patch_paths:
        _add_zone_entry(zone_by_path, path, "recent_patch_target", "recent patch target")

    zone_categories = {
        categories[path]
        for path in zone_by_path
        if path in categories
    }
    for path in changed_paths:
        category = categories.get(path)
        if category and category in zone_categories:
            _add_zone_entry(
                zone_by_path,
                path,
                "project_map_category",
                f"same project-map category as intent zone: {category}",
            )

    zone_anchor_intents = {
        intent
        for path in zone_by_path
        for intent in anchor_intents.get(path, [])
    }
    for path in changed_paths:
        shared_intents = zone_anchor_intents.intersection(anchor_intents.get(path, []))
        if shared_intents:
            _add_zone_entry(
                zone_by_path,
                path,
                "anchor_co_occurrence",
                f"shares anchor intent with intent zone: {sorted(shared_intents)[0]}",
            )

    if not zone_by_path:
        for path in changed_paths:
            _add_zone_entry(zone_by_path, path, "diff_fallback", "no intent context found; recommendations based on raw diff only")
        return list(zone_by_path.values()), []

    drift_candidates = [
        DriftCandidate(
            path=path,
            why_outside_zone="not in explicit relevant files, recent patch targets, matching project-map category, or shared anchor intent",
        )
        for path in _unique_paths(changed_paths)
        if path not in zone_by_path
    ]
    return list(zone_by_path.values()), drift_candidates
# === ANCHOR: RECOVERY_INTENT_ZONE__BUILD_INTENT_ZONE_END ===


def _add_zone_entry(
    zone_by_path: dict[str, IntentZoneEntry],
    raw_path: str,
    source: str,
    reason: str,
) -> None:
    path = raw_path.replace("\\", "/").strip()
    if path and path not in zone_by_path:
        zone_by_path[path] = IntentZoneEntry(
            path=path,
            source=cast(IntentZoneSource, source),
            reason=reason,
        )


def _unique_paths(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw_path in paths:
        path = raw_path.replace("\\", "/").strip()
        if path and path not in seen:
            seen.add(path)
            result.append(path)
    return result

# === ANCHOR: RECOVERY_INTENT_ZONE_END ===
