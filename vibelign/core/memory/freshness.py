# === ANCHOR: MEMORY_FRESHNESS_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from vibelign.core.memory.models import MemoryState, MemoryVerification


_STALE_INTENT_AGE = timedelta(hours=24)
_STALE_INTENT_COMMIT_EVENTS = 5
_CONFLICT_WINDOW = timedelta(seconds=60)
_OBSERVED_EDIT_DECISION_THRESHOLD = 3
TRIGGER_STALE_VERIFICATION = "stale_verification"
TRIGGER_STALE_INTENT = "stale_intent"
TRIGGER_STALE_RELEVANT_FILES = "stale_relevant_files"
TRIGGER_CONFLICT_DETECTED = "conflict_detected"
TRIGGER_MISSING_NEXT_ACTION = "missing_next_action"
TRIGGER_MISSING_DECISION_AFTER_OBSERVED_EDITS = "missing_decision_after_observed_edits"
TRIGGER_OBSERVED_EDIT_OUTSIDE_INTENT_ZONE = "observed_edit_outside_intent_zone"


@dataclass(frozen=True)
class MemoryFreshness:
    verification_freshness: str = ""
    stale_verification_commands: list[str] = field(default_factory=list)
    stale_intent: bool = False
    stale_relevant_files: list[str] = field(default_factory=list)
    conflicting_fields: list[str] = field(default_factory=list)
    missing_next_action: bool = False
    missing_decision_after_observed_edits: bool = False
    observed_edit_outside_intent_zone: list[str] = field(default_factory=list)
    active_trigger_ids: list[str] = field(default_factory=list)


def assess_memory_freshness(state: MemoryState) -> MemoryFreshness:
    stale_commands = [
        item.command.partition(" -> ")[0].strip()
        for item in state.verification
        if _is_stale_verification(state, item) and item.command.strip()
    ]
    stale_relevant_files = [
        item.path
        for item in state.relevant_files
        if item.path and (item.stale or item.from_previous_intent)
    ]
    stale_intent = _has_stale_intent(state)
    conflicting_fields = _conflicting_fields(state)
    missing_next_action = state.next_action is None or not state.next_action.text.strip()
    missing_decision_after_observed_edits = _missing_decision_after_observed_edits(state)
    observed_edit_outside_intent_zone = _observed_edit_outside_intent_zone(state)
    active_trigger_ids: list[str] = []
    if stale_commands:
        active_trigger_ids.append(TRIGGER_STALE_VERIFICATION)
    if stale_intent:
        active_trigger_ids.append(TRIGGER_STALE_INTENT)
    if stale_relevant_files:
        active_trigger_ids.append(TRIGGER_STALE_RELEVANT_FILES)
    if conflicting_fields:
        active_trigger_ids.append(TRIGGER_CONFLICT_DETECTED)
    if missing_next_action:
        active_trigger_ids.append(TRIGGER_MISSING_NEXT_ACTION)
    if missing_decision_after_observed_edits:
        active_trigger_ids.append(TRIGGER_MISSING_DECISION_AFTER_OBSERVED_EDITS)
    if observed_edit_outside_intent_zone:
        active_trigger_ids.append(TRIGGER_OBSERVED_EDIT_OUTSIDE_INTENT_ZONE)
    return MemoryFreshness(
        verification_freshness="stale" if stale_commands else "",
        stale_verification_commands=stale_commands,
        stale_intent=stale_intent,
        stale_relevant_files=stale_relevant_files,
        conflicting_fields=conflicting_fields,
        missing_next_action=missing_next_action,
        missing_decision_after_observed_edits=missing_decision_after_observed_edits,
        observed_edit_outside_intent_zone=observed_edit_outside_intent_zone,
        active_trigger_ids=active_trigger_ids,
    )


def _missing_decision_after_observed_edits(state: MemoryState) -> bool:
    if state.decisions:
        return False
    observed_edit_count = sum(1 for item in state.relevant_files if _is_observed_edit_file(item))
    return observed_edit_count >= _OBSERVED_EDIT_DECISION_THRESHOLD


def _observed_edit_outside_intent_zone(state: MemoryState) -> list[str]:
    observed_edit_items = [item for item in state.relevant_files if _is_observed_edit_file(item)]
    observed_edit_times = [
        (item, parsed)
        for item in observed_edit_items
        if item.path and (parsed := _parse_timestamp(item.last_updated)) is not None
    ]
    if not observed_edit_times:
        return []
    latest_time = max(parsed for _, parsed in observed_edit_times)
    latest_paths = {item.path for item, parsed in observed_edit_times if parsed == latest_time}
    zone_paths = {
        item.path
        for item in state.relevant_files
        if item.path and item.source == "explicit"
    }
    zone_paths.update(
        item.path
        for item, parsed in observed_edit_times
        if item.path and parsed < latest_time
    )
    if not zone_paths:
        return []
    return sorted(path for path in latest_paths if path not in zone_paths)


def _is_observed_edit_file(item: object) -> bool:
    return bool(
        getattr(item, "updated_by", "") == "memory_observer"
        or getattr(item, "why", "").startswith("observed edit")
    )


def _conflicting_fields(state: MemoryState) -> list[str]:
    candidates = {
        "decisions": [item.last_updated for item in state.decisions],
        "relevant_files": [item.last_updated for item in state.relevant_files],
        "verification": [item.last_updated for item in state.verification],
        "observed_context": [item.timestamp for item in state.observed_context],
        "risks": [item.last_updated for item in state.risks],
    }
    return [field_name for field_name, timestamps in candidates.items() if _has_close_timestamps(timestamps)]


def _has_close_timestamps(values: list[str]) -> bool:
    parsed = sorted(item for item in (_parse_timestamp(value) for value in values) if item is not None)
    if len(parsed) < 2:
        return False
    previous = parsed[0]
    for current in parsed[1:]:
        if current - previous <= _CONFLICT_WINDOW:
            return True
        previous = current
    return False


def _is_stale_verification(state: MemoryState, verification: MemoryVerification) -> bool:
    if verification.stale or verification.scope_unknown:
        return True
    verification_time = _parse_timestamp(verification.last_updated)
    if verification_time is None or not verification.related_files:
        return False
    active_intent_time = _active_intent_timestamp(state)
    if active_intent_time is not None and active_intent_time > verification_time:
        return True
    related_paths = set(verification.related_files)
    for event in state.observed_context:
        if event.path not in related_paths:
            continue
        event_time = _parse_timestamp(event.timestamp)
        if event_time is not None and event_time > verification_time:
            return True
    latest_observed_edit_time = _latest_observed_edit_time(state)
    if latest_observed_edit_time is not None and latest_observed_edit_time > verification_time:
        return True
    return False


def _active_intent_timestamp(state: MemoryState) -> datetime | None:
    if state.active_intent is None:
        return None
    return _parse_timestamp(state.active_intent.last_updated)


def _latest_observed_edit_time(state: MemoryState) -> datetime | None:
    timestamps = [
        _parse_timestamp(item.last_updated)
        for item in state.relevant_files
        if _is_observed_edit_file(item)
    ]
    parsed = [item for item in timestamps if item is not None]
    if not parsed:
        return None
    return max(parsed)


def _has_stale_intent(state: MemoryState) -> bool:
    if state.active_intent is not None and state.active_intent.stale:
        return True
    if state.next_action is not None and state.next_action.stale:
        return True
    intent_time = _intent_timestamp(state)
    if intent_time is None:
        return False
    if _now() - intent_time > _STALE_INTENT_AGE:
        return True
    return _commit_events_after(state, intent_time) >= _STALE_INTENT_COMMIT_EVENTS


def _intent_timestamp(state: MemoryState) -> datetime | None:
    candidates: list[datetime | None] = []
    if state.active_intent is not None:
        candidates.append(_parse_timestamp(state.active_intent.last_updated))
    if state.next_action is not None:
        candidates.append(_parse_timestamp(state.next_action.last_updated))
    parsed = [item for item in candidates if item is not None]
    if not parsed:
        return None
    return max(parsed)


def _commit_events_after(state: MemoryState, timestamp: datetime) -> int:
    count = 0
    for event in state.observed_context:
        if event.kind != "commit":
            continue
        event_time = _parse_timestamp(event.timestamp)
        if event_time is not None and event_time > timestamp:
            count += 1
    return count


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)
# === ANCHOR: MEMORY_FRESHNESS_END ===
