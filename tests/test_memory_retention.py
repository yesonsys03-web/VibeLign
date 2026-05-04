import json
from pathlib import Path
from typing import cast

from vibelign.core.memory.audit import memory_audit_path
from vibelign.core.memory.retention import apply_memory_audit_retention, memory_audit_retention_result_to_dict


def test_memory_audit_retention_rolls_old_rows_into_count_summary(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        _row("recovery_apply", "denied", 1, "2026-01-01T00:00:00Z")
        + _row("recovery_apply", "success", 2, "2026-05-01T00:00:00Z"),
        encoding="utf-8",
    )

    result = apply_memory_audit_retention(tmp_path, now="2026-05-04T00:00:00Z", retention_days=90)
    payload = memory_audit_retention_result_to_dict(result)
    retained_rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    summary_path = tmp_path / ".vibelign" / "recovery" / "memory_audit_retention_summary.json"
    summaries = cast(list[dict[str, object]], json.loads(summary_path.read_text(encoding="utf-8")))

    assert payload["applied"] is True
    assert payload["retained_rows_count"] == 1
    assert payload["compacted_rows_count"] == 1
    assert [row["sequence_number"] for row in retained_rows] == [2]
    assert summaries[-1]["compacted_rows_count"] == 1
    assert summaries[-1]["counts"] == {"recovery_apply:denied": 1}
    assert summaries[-1]["circuit_breaker_states"] == {"unknown": 1}
    p0_summaries = cast(list[dict[str, object]], summaries[-1]["p0_p1_summaries"])
    sandwich_summary = next(item for item in p0_summaries if item["slo_id"] == "sandwich_enforcement")
    assert sandwich_summary == {
        "slo_id": "sandwich_enforcement",
        "occurrences": 1,
        "sample_count": 1,
        "result": "fail",
    }
    assert b"\r\n" not in audit_path.read_bytes()
    assert b"\r\n" not in summary_path.read_bytes()


def test_memory_audit_retention_preserves_active_p0_window(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        _row("recovery_apply", "denied", 1, "2025-10-01T00:00:00Z")
        + _row("recovery_apply", "success", 2, "2026-01-15T00:00:00Z")
        + _row("recovery_apply", "success", 3, "2026-05-01T00:00:00Z"),
        encoding="utf-8",
    )

    result = apply_memory_audit_retention(
        tmp_path,
        now="2026-05-04T00:00:00Z",
        retention_days=90,
        active_window_start="2026-01-01T00:00:00Z",
    )
    retained_rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]

    assert result.applied is True
    assert result.compacted_rows_count == 1
    assert [row["sequence_number"] for row in retained_rows] == [2, 3]
    assert all("\r" not in line for line in audit_path.read_text(encoding="utf-8").splitlines())


def _row(event: str, result: str, sequence_number: int, timestamp: str) -> str:
    return json.dumps(
        {
            "event": event,
            "result": result,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        },
        sort_keys=True,
    ) + "\n"
