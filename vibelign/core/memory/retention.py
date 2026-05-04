# === ANCHOR: MEMORY_RETENTION_START ===
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from vibelign.core.memory.audit import memory_audit_path

DEFAULT_RETENTION_DAYS = 90
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
MAX_ACTIVE_WINDOW_DAYS = 180


@dataclass(frozen=True)
class MemoryAuditRetentionResult:
    applied: bool
    retained_rows_count: int
    compacted_rows_count: int
    summary_path: str
    audit_path: str


def apply_memory_audit_retention(
    root: Path,
    *,
    now: str | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    active_window_start: str | None = None,
) -> MemoryAuditRetentionResult:
    audit_path = memory_audit_path(root)
    summary_path = _summary_path(root)
    if not audit_path.exists():
        return MemoryAuditRetentionResult(False, 0, 0, summary_path.as_posix(), audit_path.as_posix())

    rows = _read_rows(audit_path)
    if not rows:
        return MemoryAuditRetentionResult(False, 0, 0, summary_path.as_posix(), audit_path.as_posix())

    cutoff = _retention_cutoff(now, retention_days, active_window_start)
    retained = [row for row in rows if _row_timestamp(row) >= cutoff]
    compacted = [row for row in rows if _row_timestamp(row) < cutoff]
    if active_window_start is None:
        retained, size_compacted = _enforce_size_limit(retained, max_bytes)
        compacted = compacted + size_compacted
    if not compacted:
        return MemoryAuditRetentionResult(False, len(retained), 0, summary_path.as_posix(), audit_path.as_posix())

    _append_summary(summary_path, compacted)
    _write_rows(audit_path, retained)
    return MemoryAuditRetentionResult(True, len(retained), len(compacted), summary_path.as_posix(), audit_path.as_posix())


def memory_audit_retention_result_to_dict(result: MemoryAuditRetentionResult) -> dict[str, object]:
    return {
        "applied": result.applied,
        "retained_rows_count": result.retained_rows_count,
        "compacted_rows_count": result.compacted_rows_count,
        "summary_path": result.summary_path,
        "audit_path": result.audit_path,
    }


def _retention_cutoff(now: str | None, retention_days: int, active_window_start: str | None) -> datetime:
    current = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
    retention_cutoff = current - timedelta(days=max(retention_days, 0))
    if active_window_start is None:
        return retention_cutoff
    active_start = _parse_timestamp(active_window_start)
    active_floor = current - timedelta(days=MAX_ACTIVE_WINDOW_DAYS)
    protected_start = max(active_start, active_floor)
    return min(retention_cutoff, protected_start)


def _enforce_size_limit(rows: list[dict[str, object]], max_bytes: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if max_bytes <= 0:
        return [], rows
    retained = list(rows)
    compacted: list[dict[str, object]] = []
    while retained and _render_rows(retained) > max_bytes:
        compacted.append(retained.pop(0))
    return retained, compacted


def _append_summary(summary_path: Path, rows: list[dict[str, object]]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_summary(summary_path)
    existing.append(_build_count_summary(rows))
    _ = summary_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _build_count_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    counts: dict[str, int] = {}
    circuit_breaker_states: dict[str, int] = {}
    timestamps = [_string(row.get("timestamp")) for row in rows if _string(row.get("timestamp"))]
    for row in rows:
        event = _string(row.get("event")) or "unknown"
        result = _string(row.get("result")) or "unknown"
        key = f"{event}:{result}"
        counts[key] = counts.get(key, 0) + 1
        state = _string(row.get("circuit_breaker_state")) or "unknown"
        circuit_breaker_states[state] = circuit_breaker_states.get(state, 0) + 1
    return {
        "compacted_rows_count": len(rows),
        "window_start": min(timestamps) if timestamps else "",
        "window_end": max(timestamps) if timestamps else "",
        "counts": counts,
        "circuit_breaker_states": circuit_breaker_states,
        "p0_p1_summaries": _p0_p1_summaries(rows),
    }


def _p0_p1_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    mapping = {
        "sandwich_enforcement": {"recovery_apply"},
        "memory_as_instruction": {"memory_summary_read"},
        "redaction": {"memory_summary_read"},
        "drift_label": {"recovery_preview"},
        "stale_intent": {"memory_review_trigger_shown", "recovery_preview"},
    }
    summaries: list[dict[str, object]] = []
    for slo_id, event_names in mapping.items():
        samples = [row for row in rows if _string(row.get("event")) in event_names]
        occurrences = sum(1 for row in samples if _string(row.get("result")) != "success")
        result = "needs_review" if not samples else "pass" if occurrences == 0 else "fail"
        summaries.append(
            {
                "slo_id": slo_id,
                "occurrences": occurrences,
                "sample_count": len(samples),
                "result": result,
            }
        )
    return summaries


def _read_rows(audit_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        try:
            payload = cast("object", json.loads(line))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(cast("dict[str, object]", payload))
    return rows


def _write_rows(audit_path: Path, rows: list[dict[str, object]]) -> None:
    rendered = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    _ = audit_path.write_text(rendered, encoding="utf-8", newline="\n")


def _read_summary(summary_path: Path) -> list[dict[str, object]]:
    if not summary_path.exists():
        return []
    try:
        payload = cast("object", json.loads(summary_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items = cast("list[object]", payload)
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def _row_timestamp(row: dict[str, object]) -> datetime:
    timestamp = _string(row.get("timestamp"))
    return _parse_timestamp(timestamp) if timestamp else datetime.fromtimestamp(0, timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _render_rows(rows: list[dict[str, object]]) -> int:
    return len("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8"))


def _summary_path(root: Path) -> Path:
    return root / ".vibelign" / "recovery" / "memory_audit_retention_summary.json"


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""
# === ANCHOR: MEMORY_RETENTION_END ===
