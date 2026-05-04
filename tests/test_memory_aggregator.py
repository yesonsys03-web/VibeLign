import json
from pathlib import Path

from vibelign.core.memory.aggregator import (
    aggregate_p0_occurrences,
    p0_occurrence_summary_to_dict,
    verify_audit_integrity,
)
from vibelign.core.memory.audit import memory_audit_path


def test_p0_occurrence_aggregator_reports_zero_window(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 1,
                "timestamp": "2026-05-03T10:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )
    sandwich_summary = next(summary for summary in summaries if summary.slo_id == "sandwich_enforcement")
    payload = p0_occurrence_summary_to_dict(sandwich_summary)

    assert payload == {
        "slo_id": "sandwich_enforcement",
        "window_start": "2026-05-03T00:00:00Z",
        "window_end": "2026-05-04T00:00:00Z",
        "occurrences": 0,
        "sample_count": 1,
        "result": "pass",
        "corrupt_rows_count": 0,
        "warning": "",
    }


def test_p0_occurrence_aggregator_counts_actual_memory_summary_events(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        json.dumps(
            {
                "event": "memory_summary_read",
                "result": "success",
                "sequence_number": 1,
                "timestamp": "2026-05-03T10:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )
    redaction_summary = next(summary for summary in summaries if summary.slo_id == "redaction")

    assert redaction_summary.result == "pass"
    assert redaction_summary.sample_count == 1


def test_p0_occurrence_aggregator_marks_unsampled_slo_needs_review(tmp_path: Path) -> None:
    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )

    assert all(summary.result == "needs_review" for summary in summaries)
    assert all(summary.warning == "no audit samples for SLO" for summary in summaries)


def test_audit_integrity_rejects_sequence_gap_and_duplicate() -> None:
    review = verify_audit_integrity(
        [
            {"sequence_number": 1},
            {"sequence_number": 3},
            {"sequence_number": 3},
        ]
    )

    assert review.ok is False
    assert review.missing_sequence_numbers == [2]
    assert review.duplicate_sequence_numbers == [3]
    assert review.warning == "audit log needs review"


def test_aggregator_ignores_out_of_window_sequence_duplicates(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 1,
                "timestamp": "2026-01-01T00:00:00Z",
            },
            sort_keys=True,
        )
        + "\n"
        + json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 1,
                "timestamp": "2026-01-02T00:00:00Z",
            },
            sort_keys=True,
        )
        + "\n"
        + json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 2,
                "timestamp": "2026-05-03T10:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )
    sandwich_summary = next(summary for summary in summaries if summary.slo_id == "sandwich_enforcement")

    assert sandwich_summary.result == "pass"
    assert sandwich_summary.sample_count == 1
    assert sandwich_summary.warning == ""


def test_aggregator_ignores_out_of_window_corrupt_rows(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        '{"event":"recovery_apply","timestamp":"2026-01-01T00:00:00Z", not-json}\n'
        + json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 2,
                "timestamp": "2026-05-03T10:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )
    sandwich_summary = next(summary for summary in summaries if summary.slo_id == "sandwich_enforcement")

    assert sandwich_summary.result == "pass"
    assert sandwich_summary.corrupt_rows_count == 0
    assert sandwich_summary.warning == ""


def test_aggregator_quarantines_corrupt_rows_with_redaction(tmp_path: Path) -> None:
    audit_path = memory_audit_path(tmp_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _ = audit_path.write_text(
        "{not-json /Users/example/secret.py C:\\Users\\example\\secret.py}\n"
        + json.dumps(
            {
                "event": "recovery_apply",
                "result": "success",
                "sequence_number": 1,
                "timestamp": "2026-05-03T10:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summaries = aggregate_p0_occurrences(
        tmp_path,
        window_start="2026-05-03T00:00:00Z",
        window_end="2026-05-04T00:00:00Z",
    )
    sandwich_summary = next(summary for summary in summaries if summary.slo_id == "sandwich_enforcement")
    quarantine_text = (tmp_path / ".vibelign" / "recovery" / "memory_audit_corrupt.jsonl").read_text(
        encoding="utf-8"
    )

    assert sandwich_summary.result == "needs_review"
    assert sandwich_summary.corrupt_rows_count == 1
    assert sandwich_summary.warning == "audit log needs review"
    assert "<absolute-path>" in quarantine_text
    assert "/Users/example/secret.py" not in quarantine_text
    assert "C:\\Users\\example\\secret.py" not in quarantine_text
