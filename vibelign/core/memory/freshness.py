# === ANCHOR: MEMORY_FRESHNESS_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from vibelign.core.memory.models import MemoryState


_STALE_INTENT_AGE = timedelta(hours=24)
_STALE_INTENT_COMMIT_EVENTS = 5


@dataclass(frozen=True)
class MemoryFreshness:
    verification_freshness: str = ""
    stale_verification_commands: list[str] = field(default_factory=list)
    stale_intent: bool = False
    stale_relevant_files: list[str] = field(default_factory=list)


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
    return MemoryFreshness(
        verification_freshness="stale" if stale_commands else "",
        stale_verification_commands=stale_commands,
        stale_intent=stale_intent,
        stale_relevant_files=stale_relevant_files,
    )


def _is_stale_verification(state: MemoryState, verification) -> bool:
    if verification.stale:
        return True
    verification_time = _parse_timestamp(verification.last_updated)
    if verification_time is None or not verification.related_files:
        return False
    related_paths = set(verification.related_files)
    for event in state.observed_context:
        if event.path not in related_paths:
            continue
        event_time = _parse_timestamp(event.timestamp)
        if event_time is not None and event_time > verification_time:
            return True
    return False


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
    candidates = []
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
