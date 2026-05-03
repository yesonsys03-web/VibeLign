# === ANCHOR: TRIGGER_BASELINE_START ===
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast


_TRIGGER_WINDOW = timedelta(days=7)
_ENGAGED_TRIGGER_ACTIONS = {"accepted", "dismissed", "snoozed"}


@dataclass(frozen=True)
class TriggerIgnoredRate:
    shown: int = 0
    engaged: int = 0
    ignored: int = 0
    rate: float | None = None


def trigger_baseline_path(root: Path) -> Path:
    return root / ".vibelign" / "recovery" / "trigger_baseline.json"


def iter_memory_audit_events(root: Path) -> Iterator[dict[str, object]]:
    path = root / ".vibelign" / "memory_audit.jsonl"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            loaded = cast(object, json.loads(line))
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            loaded_dict = cast(dict[object, object], loaded)
            yield {key: value for key, value in loaded_dict.items() if isinstance(key, str)}


def summarize_trigger_ignored_rate(
    root: Path,
    *,
    now: datetime | None = None,
    window: timedelta = _TRIGGER_WINDOW,
) -> TriggerIgnoredRate:
    reference_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    events = sorted(
        _trigger_events_in_window(root, reference_time=reference_time, window=window),
        key=lambda item: item.timestamp,
    )
    shown = 0
    engaged = 0
    outstanding: Counter[tuple[str, str]] = Counter()
    for event in events:
        key = (event.trigger_id, event.source)
        if event.action == "shown":
            shown += 1
            outstanding[key] += 1
            continue
        if event.action in _ENGAGED_TRIGGER_ACTIONS and outstanding[key] > 0:
            outstanding[key] -= 1
            engaged += 1
    ignored = sum(outstanding.values())
    return TriggerIgnoredRate(
        shown=shown,
        engaged=engaged,
        ignored=ignored,
        rate=(ignored / shown) if shown else None,
    )


@dataclass(frozen=True)
class _TriggerAuditEvent:
    timestamp: datetime
    trigger_id: str
    action: str
    source: str


def _trigger_events_in_window(
    root: Path,
    *,
    reference_time: datetime,
    window: timedelta,
) -> Iterator[_TriggerAuditEvent]:
    start = reference_time - window
    for event in iter_memory_audit_events(root):
        parsed = _trigger_event(event)
        if parsed is None:
            continue
        if start <= parsed.timestamp <= reference_time:
            yield parsed


def _trigger_event(event: dict[str, object]) -> _TriggerAuditEvent | None:
    timestamp = _parse_timestamp(str(event.get("timestamp", "")))
    trigger = event.get("trigger")
    if timestamp is None or not isinstance(trigger, dict):
        return None
    trigger_dict = cast(dict[object, object], trigger)
    typed_trigger = {key: value for key, value in trigger_dict.items() if isinstance(key, str)}
    trigger_id = typed_trigger.get("id")
    action = typed_trigger.get("action")
    source = typed_trigger.get("source")
    if not isinstance(trigger_id, str) or not isinstance(action, str) or not isinstance(source, str):
        return None
    if action != "shown" and action not in _ENGAGED_TRIGGER_ACTIONS and action != "ignored":
        return None
    return _TriggerAuditEvent(
        timestamp=timestamp,
        trigger_id=trigger_id,
        action=action,
        source=source,
    )


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
# === ANCHOR: TRIGGER_BASELINE_END ===
