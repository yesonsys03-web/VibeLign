# === ANCHOR: MEMORY_AUDIT_START ===
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


AuditResult = Literal["success", "blocked", "error"]
CircuitBreakerState = Literal["active", "degraded"]


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
class MemoryAuditEvent:
    event: str
    project_root_hash: str
    tool: str
    timestamp: str
    paths_count: AuditPathsCount = field(default_factory=AuditPathsCount)
    circuit_breaker_state: CircuitBreakerState = "active"
    redaction: object = field(default_factory=AuditRedaction)
    result: AuditResult = "success"
    capability_grant_id: str | None = None
    sandwich_checkpoint_id: str | None = None


def build_memory_audit_event(
    root: Path,
    *,
    event: str,
    tool: str = "vib-cli",
    paths_count: AuditPathsCount | None = None,
    circuit_breaker_state: CircuitBreakerState = "active",
    redaction: object | None = None,
    result: AuditResult = "success",
    capability_grant_id: str | None = None,
    sandwich_checkpoint_id: str | None = None,
) -> MemoryAuditEvent:
    return MemoryAuditEvent(
        event=_safe_label(event, fallback="memory_audit"),
        project_root_hash=_project_root_hash(root),
        tool=_safe_label(tool, fallback="unknown-tool"),
        timestamp=_utc_now(),
        paths_count=_normalize_paths_count(paths_count),
        circuit_breaker_state=circuit_breaker_state,
        redaction=redaction or AuditRedaction(),
        result=result,
        capability_grant_id=_safe_optional_id(capability_grant_id),
        sandwich_checkpoint_id=_safe_optional_id(sandwich_checkpoint_id),
    )


def append_memory_audit_event(path: Path, event: MemoryAuditEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(memory_audit_event_to_dict(event), sort_keys=True) + "\n")


def memory_audit_event_to_dict(event: MemoryAuditEvent) -> dict[str, object]:
    return {
        "event": event.event,
        "project_root_hash": event.project_root_hash,
        "tool": event.tool,
        "timestamp": event.timestamp,
        "capability_grant_id": event.capability_grant_id,
        "sandwich_checkpoint_id": event.sandwich_checkpoint_id,
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
        "result": event.result,
    }


def memory_audit_path(root: Path) -> Path:
    return root / ".vibelign" / "memory_audit.jsonl"


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
