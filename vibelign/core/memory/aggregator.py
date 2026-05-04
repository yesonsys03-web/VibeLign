# === ANCHOR: MEMORY_AGGREGATOR_START ===
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

from vibelign.core.memory.audit import memory_audit_path

AggregationResult = Literal["pass", "fail", "needs_review"]

_P0_SLO_EVENTS = {
    "sandwich_enforcement": {"recovery_apply"},
    "memory_as_instruction": {"memory_summary_read"},
    "redaction": {"memory_summary_read"},
    "drift_label": {"recovery_preview"},
    "stale_intent": {"memory_review_trigger_shown", "recovery_preview"},
}


@dataclass(frozen=True)
class P0OccurrenceSummary:
    slo_id: str
    window_start: str
    window_end: str
    occurrences: int
    sample_count: int
    result: AggregationResult
    corrupt_rows_count: int = 0
    warning: str = ""


@dataclass(frozen=True)
class AuditIntegrityReview:
    ok: bool
    corrupt_rows_count: int = 0
    duplicate_sequence_numbers: list[int] | None = None
    missing_sequence_numbers: list[int] | None = None
    warning: str = ""


def aggregate_p0_occurrences(root: Path, *, window_start: str, window_end: str) -> list[P0OccurrenceSummary]:
    audit_path = memory_audit_path(root)
    rows, corrupt_row_timestamps = _read_audit_rows(root, audit_path)
    summaries: list[P0OccurrenceSummary] = []
    window_rows = [row for row in rows if _is_in_window(_string(row.get("timestamp")), window_start, window_end)]
    window_corrupt_rows_count = sum(
        1 for timestamp in corrupt_row_timestamps if not timestamp or _is_in_window(timestamp, window_start, window_end)
    )
    integrity = verify_audit_integrity(window_rows, corrupt_rows_count=window_corrupt_rows_count)

    for slo_id, event_names in _P0_SLO_EVENTS.items():
        samples = [row for row in window_rows if _string(row.get("event")) in event_names]
        occurrences = sum(1 for row in samples if _string(row.get("result")) != "success")
        result: AggregationResult = "pass" if occurrences == 0 else "fail"
        warning = ""
        if not samples:
            result = "needs_review"
            warning = "no audit samples for SLO"
        if not integrity.ok:
            result = "needs_review"
            warning = integrity.warning or "audit log needs review"
        summaries.append(
            P0OccurrenceSummary(
                slo_id=slo_id,
                window_start=window_start,
                window_end=window_end,
                occurrences=occurrences,
                sample_count=len(samples),
                result=result,
                corrupt_rows_count=window_corrupt_rows_count,
                warning=warning,
            )
        )
    return summaries


def p0_occurrence_summary_to_dict(summary: P0OccurrenceSummary) -> dict[str, object]:
    return {
        "slo_id": summary.slo_id,
        "window_start": summary.window_start,
        "window_end": summary.window_end,
        "occurrences": summary.occurrences,
        "sample_count": summary.sample_count,
        "result": summary.result,
        "corrupt_rows_count": summary.corrupt_rows_count,
        "warning": summary.warning,
    }


def verify_audit_integrity(
    rows: list[dict[str, object]],
    *,
    corrupt_rows_count: int = 0,
) -> AuditIntegrityReview:
    sequence_numbers = [row.get("sequence_number") for row in rows]
    valid_numbers = sorted(number for number in sequence_numbers if isinstance(number, int) and number > 0)
    duplicates = sorted({number for number in valid_numbers if valid_numbers.count(number) > 1})
    missing: list[int] = []
    if valid_numbers:
        expected = set(range(valid_numbers[0], valid_numbers[-1] + 1))
        missing = sorted(expected.difference(valid_numbers))
    ok = corrupt_rows_count == 0 and not duplicates and not missing and len(valid_numbers) == len(rows)
    warning = "" if ok else "audit log needs review"
    return AuditIntegrityReview(
        ok=ok,
        corrupt_rows_count=corrupt_rows_count,
        duplicate_sequence_numbers=duplicates,
        missing_sequence_numbers=missing,
        warning=warning,
    )


def _read_audit_rows(root: Path, audit_path: Path) -> tuple[list[dict[str, object]], list[str]]:
    if not audit_path.exists():
        return [], []
    rows: list[dict[str, object]] = []
    corrupt_rows: list[str] = []
    corrupt_row_timestamps: list[str] = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        try:
            payload = cast("object", json.loads(line))
        except json.JSONDecodeError:
            corrupt_rows.append(_redact_sensitive_paths(line))
            corrupt_row_timestamps.append(_timestamp_from_corrupt_row(line))
            continue
        if isinstance(payload, dict):
            rows.append(cast("dict[str, object]", payload))
        else:
            corrupt_rows.append(_redact_sensitive_paths(line))
            corrupt_row_timestamps.append(_timestamp_from_corrupt_row(line))
    _write_corrupt_rows(root, corrupt_rows)
    return rows, corrupt_row_timestamps


def _write_corrupt_rows(root: Path, corrupt_rows: list[str]) -> None:
    if not corrupt_rows:
        return
    quarantine_path = root / ".vibelign" / "recovery" / "memory_audit_corrupt.jsonl"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    payloads = [{"raw": row} for row in corrupt_rows]
    rendered = "".join(json.dumps(payload, sort_keys=True) + "\n" for payload in payloads)
    _ = quarantine_path.write_text(rendered, encoding="utf-8", newline="\n")


def _is_in_window(timestamp: str, window_start: str, window_end: str) -> bool:
    if not timestamp:
        return False
    parsed = _parse_timestamp(timestamp)
    return _parse_timestamp(window_start) <= parsed <= _parse_timestamp(window_end)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _redact_sensitive_paths(value: str) -> str:
    redacted = re.sub(r"[A-Za-z]:\\[^\"'\s]+", "<absolute-path>", value)
    redacted = re.sub(r"/[^\"'\s]+", "<absolute-path>", redacted)
    return redacted


def _timestamp_from_corrupt_row(value: str) -> str:
    match = re.search(r'"timestamp"\s*:\s*"([^"]+)"', value)
    return match.group(1) if match else ""


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""
# === ANCHOR: MEMORY_AGGREGATOR_END ===
