import json
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from collections.abc import Callable, Iterator
from typing import Protocol, cast


class _TriggerIgnoredRateLike(Protocol):
    shown: int
    engaged: int
    ignored: int
    rate: float | None


def _module():
    return import_module("vibelign.core.recovery.trigger_baseline")


def _iter_events() -> Callable[[Path], Iterator[dict[str, object]]]:
    module = _module()
    return cast(Callable[[Path], Iterator[dict[str, object]]], getattr(module, "iter_memory_audit_events"))


def _summarize() -> Callable[..., _TriggerIgnoredRateLike]:
    module = _module()
    return cast(Callable[..., _TriggerIgnoredRateLike], getattr(module, "summarize_trigger_ignored_rate"))


def _baseline_path() -> Callable[[Path], Path]:
    module = _module()
    return cast(Callable[[Path], Path], getattr(module, "trigger_baseline_path"))


def _write_snapshot() -> Callable[..., dict[str, object]]:
    module = _module()
    return cast(Callable[..., dict[str, object]], getattr(module, "write_trigger_baseline_snapshot"))


def _write_audit_lines(root: Path, rows: list[object]) -> None:
    path = root / ".vibelign" / "memory_audit.jsonl"
    path.parent.mkdir(parents=True)
    lines = [json.dumps(row) if isinstance(row, dict) else str(row) for row in rows]
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trigger_row(timestamp: str, trigger_id: str, action: str, source: str = "vibmemoryreview") -> dict[str, object]:
    return {
        "event": f"memory_review_trigger_{action}",
        "timestamp": timestamp,
        "trigger": {"id": trigger_id, "action": action, "source": source},
    }


def test_iter_memory_audit_events_ignores_blank_and_malformed_lines(tmp_path: Path) -> None:
    root = tmp_path
    _write_audit_lines(
        root,
        [
            _trigger_row("2026-05-03T00:00:00Z", "stale_intent", "shown"),
            "",
            "not json",
            ["not", "object"],
        ],
    )

    events = list(_iter_events()(root))

    assert len(events) == 1
    assert events[0]["event"] == "memory_review_trigger_shown"


def test_summarize_trigger_ignored_rate_counts_engagements(tmp_path: Path) -> None:
    root = tmp_path
    _write_audit_lines(
        root,
        [
            _trigger_row("2026-05-03T00:00:00Z", "stale_intent", "shown"),
            _trigger_row("2026-05-03T00:01:00Z", "stale_intent", "snoozed"),
            _trigger_row("2026-05-03T00:02:00Z", "missing_next_action", "shown"),
            _trigger_row("2026-05-03T00:03:00Z", "missing_next_action", "dismissed"),
            _trigger_row("2026-05-03T00:04:00Z", "patch_outside_intent_zone", "shown"),
        ],
    )

    summary = _summarize()(root, now=datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc))

    assert summary.shown == 3
    assert summary.engaged == 2
    assert summary.ignored == 1
    assert summary.rate == 1 / 3


def test_summarize_trigger_ignored_rate_filters_window_and_bad_rows(tmp_path: Path) -> None:
    root = tmp_path
    _write_audit_lines(
        root,
        [
            _trigger_row("2026-04-20T00:00:00Z", "old_trigger", "shown"),
            _trigger_row("2026-05-03T00:00:00Z", "stale_intent", "shown"),
            _trigger_row("not-a-time", "stale_intent", "dismissed"),
            _trigger_row("2026-05-03T00:01:00Z", "stale_intent", "execute"),
            {"event": "memory_summary_read", "timestamp": "2026-05-03T00:02:00Z"},
        ],
    )

    summary = _summarize()(root, now=datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc))

    assert summary.shown == 1
    assert summary.engaged == 0
    assert summary.ignored == 1
    assert summary.rate == 1.0


def test_summarize_trigger_ignored_rate_leaves_repeated_shown_unmatched(tmp_path: Path) -> None:
    root = tmp_path
    _write_audit_lines(
        root,
        [
            _trigger_row("2026-05-03T00:00:00Z", "stale_intent", "shown"),
            _trigger_row("2026-05-03T00:01:00Z", "stale_intent", "shown"),
            _trigger_row("2026-05-03T00:02:00Z", "stale_intent", "dismissed"),
        ],
    )

    summary = _summarize()(root, now=datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc))

    assert summary.shown == 2
    assert summary.engaged == 1
    assert summary.ignored == 1
    assert summary.rate == 0.5


def test_trigger_baseline_path_targets_local_recovery_snapshot(tmp_path: Path) -> None:
    path = _baseline_path()(tmp_path)

    assert path == tmp_path / ".vibelign" / "recovery" / "trigger_baseline.json"
    assert not path.exists()


def test_write_trigger_baseline_snapshot_logs_tuning_recommendation(tmp_path: Path) -> None:
    root = tmp_path
    _write_audit_lines(
        root,
        [
            _trigger_row("2026-05-03T00:00:00Z", "stale_intent", "shown"),
            _trigger_row("2026-05-03T00:01:00Z", "stale_intent", "dismissed"),
            _trigger_row("2026-05-03T00:02:00Z", "missing_next_action", "shown"),
            _trigger_row("2026-05-03T00:03:00Z", "patch_outside_intent_zone", "shown"),
        ],
    )

    snapshot = _write_snapshot()(root, now=datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc))
    payload = json.loads(_baseline_path()(root).read_text(encoding="utf-8"))
    rendered = json.dumps(payload, sort_keys=True)

    assert snapshot == payload
    assert payload["schema_version"] == 1
    assert payload["baseline_window_days"] == 7
    assert payload["ignored_prompt_rate_7d"] == 2 / 3
    assert payload["shown_prompt_count_7d"] == 3
    assert payload["ignored_prompt_count_7d"] == 2
    assert payload["tuning_recommendation"] == "trigger prompts ignored above 30%; review trigger thresholds"
    assert "stale_intent" not in rendered
    assert "missing_next_action" not in rendered
