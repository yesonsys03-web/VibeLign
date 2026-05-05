# === ANCHOR: MEMORY_AUDIT_START ===
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast


AuditResult = Literal["success", "denied", "blocked", "aborted", "failed", "busy"]
CircuitBreakerState = Literal["active", "degraded"]
TriggerAction = Literal["shown", "accepted", "dismissed", "snoozed", "ignored"]


@dataclass(frozen=True)
class AuditPathsCount:
    in_zone: int = 0
    drift: int = 0
    total: int = 0


@dataclass(frozen=True)
class AuditRedaction:
    secret_hits: int = 0
    privacy_hits: int = 0
    summarized_fields: int = 0


@dataclass(frozen=True)
class AuditTrigger:
    id: str | None = None
    action: TriggerAction | None = None
    source: str | None = None


@dataclass(frozen=True)
class MemoryAuditEvent:
    event: str
    project_root_hash: str
    tool: str
    timestamp: str
    sequence_number: int = 0
    paths_count: AuditPathsCount = field(default_factory=AuditPathsCount)
    circuit_breaker_state: CircuitBreakerState = "active"
    redaction: object = field(default_factory=AuditRedaction)
    trigger: object = field(default_factory=AuditTrigger)
    result: AuditResult = "success"
    capability_grant_id: str | None = None
    sandwich_checkpoint_id: str | None = None
    plan_id: str | None = None
    candidate_id: str | None = None
    option_id: str | None = None
    recommendation_provider: str | None = None
    memory_proposal_id: str | None = None
    handoff_draft_id: str | None = None


def build_memory_audit_event(
    root: Path,
    *,
    event: str,
    tool: str = "vib-cli",
    paths_count: AuditPathsCount | None = None,
    circuit_breaker_state: CircuitBreakerState = "active",
    redaction: object | None = None,
    trigger: object | None = None,
    result: AuditResult = "success",
    capability_grant_id: str | None = None,
    sandwich_checkpoint_id: str | None = None,
    plan_id: str | None = None,
    candidate_id: str | None = None,
    option_id: str | None = None,
    recommendation_provider: str | None = None,
    memory_proposal_id: str | None = None,
    handoff_draft_id: str | None = None,
    sequence_number: int = 0,
) -> MemoryAuditEvent:
    return MemoryAuditEvent(
        event=_safe_label(event, fallback="memory_audit"),
        project_root_hash=_project_root_hash(root),
        tool=_safe_label(tool, fallback="unknown-tool"),
        timestamp=_utc_now(),
        sequence_number=max(sequence_number, 0),
        paths_count=_normalize_paths_count(paths_count),
        circuit_breaker_state=circuit_breaker_state,
        redaction=redaction or AuditRedaction(),
        trigger=_normalize_trigger(trigger),
        result=result,
        capability_grant_id=_safe_optional_id(capability_grant_id),
        sandwich_checkpoint_id=_safe_optional_id(sandwich_checkpoint_id),
        plan_id=_safe_optional_id(plan_id),
        candidate_id=_safe_optional_id(candidate_id),
        option_id=_safe_optional_id(option_id),
        recommendation_provider=_safe_optional_id(recommendation_provider),
        memory_proposal_id=_safe_optional_id(memory_proposal_id),
        handoff_draft_id=_safe_optional_id(handoff_draft_id),
    )


def append_memory_audit_event(path: Path, event: MemoryAuditEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _audit_append_lock(path):
        event_to_write = event if event.sequence_number > 0 else replace(event, sequence_number=_next_sequence_number(path))
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            _ = handle.write(json.dumps(memory_audit_event_to_dict(event_to_write), sort_keys=True) + "\n")


def memory_audit_event_to_dict(event: MemoryAuditEvent) -> dict[str, object]:
    return {
        "event": event.event,
        "project_root_hash": event.project_root_hash,
        "tool": event.tool,
        "timestamp": event.timestamp,
        "sequence_number": event.sequence_number,
        "capability_grant_id": event.capability_grant_id,
        "sandwich_checkpoint_id": event.sandwich_checkpoint_id,
        "plan_id": event.plan_id,
        "candidate_id": event.candidate_id,
        "option_id": event.option_id,
        "recommendation_provider": event.recommendation_provider,
        "memory_proposal_id": event.memory_proposal_id,
        "handoff_draft_id": event.handoff_draft_id,
        "paths_count": {
            "in_zone": event.paths_count.in_zone,
            "drift": event.paths_count.drift,
            "total": event.paths_count.total,
        },
        "circuit_breaker_state": event.circuit_breaker_state,
        "redaction": {
            "secret_hits": _count_value(event.redaction, "secret_hits"),
            "privacy_hits": _count_value(event.redaction, "privacy_hits"),
            "summarized_fields": _count_value(event.redaction, "summarized_fields"),
        },
        "trigger": _trigger_to_dict(event.trigger),
        "result": event.result,
    }


def memory_audit_path(root: Path) -> Path:
    return root / ".vibelign" / "memory_audit.jsonl"


def _next_sequence_number(path: Path) -> int:
    if not path.exists():
        return 1
    highest = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = cast("object", json.loads(line))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        values = cast("dict[object, object]", payload)
        sequence_number = values.get("sequence_number")
        if isinstance(sequence_number, int) and sequence_number > highest:
            highest = sequence_number
    return highest + 1


@contextmanager
def _audit_append_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f"{path.name}.lock")
    deadline = time.monotonic() + 5
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("timed out waiting for memory audit append lock")
            _remove_stale_lock(lock_path)
            time.sleep(0.01)
    try:
        os.close(descriptor)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _remove_stale_lock(lock_path: Path) -> None:
    try:
        age_seconds = time.time() - lock_path.stat().st_mtime
    except FileNotFoundError:
        return
    if age_seconds <= 30:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _project_root_hash(root: Path) -> str:
    normalized = str(root.resolve())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _normalize_paths_count(paths_count: AuditPathsCount | None) -> AuditPathsCount:
    if paths_count is None:
        return AuditPathsCount()
    in_zone = max(paths_count.in_zone, 0)
    drift = max(paths_count.drift, 0)
    total = max(paths_count.total, in_zone + drift)
    return AuditPathsCount(in_zone=in_zone, drift=drift, total=total)


def _count_value(source: object, name: str) -> int:
    value = getattr(source, name, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _normalize_trigger(trigger: object | None) -> AuditTrigger:
    if trigger is None:
        return AuditTrigger()
    return AuditTrigger(
        id=_safe_optional_id(getattr(trigger, "id", None)),
        action=_safe_trigger_action(getattr(trigger, "action", None)),
        source=_safe_optional_id(getattr(trigger, "source", None)),
    )


def _trigger_to_dict(trigger: object) -> dict[str, object]:
    return {
        "id": _safe_optional_id(getattr(trigger, "id", None)),
        "action": _safe_trigger_action(getattr(trigger, "action", None)),
        "source": _safe_optional_id(getattr(trigger, "source", None)),
    }


def _safe_trigger_action(value: object) -> TriggerAction | None:
    if value in {"shown", "accepted", "dismissed", "snoozed", "ignored"}:
        return cast(TriggerAction, value)
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_label(value: str, *, fallback: str = "unknown") -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in {"_", "-", ":"})[:80]
    return cleaned or fallback


def _safe_optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _safe_label(value, fallback="")
    return cleaned or None
# === ANCHOR: MEMORY_AUDIT_END ===
