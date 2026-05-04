import json
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast


@dataclass(frozen=True)
class _TestRedaction:
    secret_hits: int = 0
    privacy_hits: int = 0
    summarized_fields: int = 0


@dataclass(frozen=True)
class _TestTrigger:
    id: str | None = None
    action: str | None = None
    source: str | None = None


class _AuditPathsCountLike(Protocol):
    in_zone: int
    drift: int
    total: int


class _MemoryAuditEventLike(Protocol):
    event: str
    project_root_hash: str
    tool: str
    timestamp: str
    paths_count: _AuditPathsCountLike
    redaction: object


def _audit_module():
    return import_module("vibelign.core.memory.audit")


def _build_event() -> Callable[..., _MemoryAuditEventLike]:
    module = _audit_module()
    return cast(Callable[..., _MemoryAuditEventLike], getattr(module, "build_memory_audit_event"))


def _event_to_dict() -> Callable[[_MemoryAuditEventLike], dict[str, object]]:
    module = _audit_module()
    return cast(Callable[[_MemoryAuditEventLike], dict[str, object]], getattr(module, "memory_audit_event_to_dict"))


def test_memory_audit_event_contains_counts_not_raw_paths(tmp_path: Path) -> None:
    module = _audit_module()
    paths_count = getattr(module, "AuditPathsCount")(in_zone=2, drift=1, total=3)
    event = _build_event()(
        tmp_path,
        event="memory_summary_read",
        paths_count=paths_count,
        redaction=_TestRedaction(secret_hits=1, privacy_hits=2, summarized_fields=3),
    )

    payload = _event_to_dict()(event)
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["event"] == "memory_summary_read"
    assert payload["project_root_hash"] != str(tmp_path)
    assert payload["paths_count"] == {"in_zone": 2, "drift": 1, "total": 3}
    assert payload["redaction"] == {
        "secret_hits": 1,
        "privacy_hits": 2,
        "summarized_fields": 3,
    }
    assert str(tmp_path) not in rendered
    assert payload["trigger"] == {"id": None, "action": None, "source": None}


def test_memory_audit_append_writes_jsonl(tmp_path: Path) -> None:
    module = _audit_module()
    audit_path = getattr(module, "memory_audit_path")(tmp_path)
    event = _build_event()(tmp_path, event="recovery_preview", result="success")

    getattr(module, "append_memory_audit_event")(audit_path, event)

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "recovery_preview"
    assert payload["result"] == "success"
    assert payload["sequence_number"] == 1


def test_memory_audit_append_assigns_monotonic_sequence_numbers(tmp_path: Path) -> None:
    module = _audit_module()
    audit_path = getattr(module, "memory_audit_path")(tmp_path)
    first = _build_event()(tmp_path, event="recovery_preview", result="success")
    second = _build_event()(tmp_path, event="recovery_apply", result="aborted")

    getattr(module, "append_memory_audit_event")(audit_path, first)
    getattr(module, "append_memory_audit_event")(audit_path, second)

    payloads = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert [payload["sequence_number"] for payload in payloads] == [1, 2]
    assert payloads[1]["result"] == "aborted"


def test_memory_audit_accepts_operational_result_taxonomy(tmp_path: Path) -> None:
    results = ["success", "denied", "busy", "aborted", "failed"]

    payloads = [
        _event_to_dict()(_build_event()(tmp_path, event="recovery_apply", result=result))
        for result in results
    ]

    assert [payload["result"] for payload in payloads] == results


def test_memory_audit_append_lock_preserves_unique_sequence_numbers(tmp_path: Path) -> None:
    module = _audit_module()
    audit_path = getattr(module, "memory_audit_path")(tmp_path)

    def append_one(index: int) -> None:
        event = _build_event()(tmp_path, event=f"recovery_apply_{index}", result="success")
        getattr(module, "append_memory_audit_event")(audit_path, event)

    with ThreadPoolExecutor(max_workers=4) as executor:
        _ = list(executor.map(append_one, range(20)))

    payloads = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    sequence_numbers = sorted(payload["sequence_number"] for payload in payloads)
    assert sequence_numbers == list(range(1, 21))
    assert b"\r\n" not in audit_path.read_bytes()


def test_memory_audit_sanitizes_labels_and_optional_ids(tmp_path: Path) -> None:
    event = _build_event()(
        tmp_path,
        event="memory summary read; rm -rf /",
        tool="vib cli && bad",
        capability_grant_id="grant id / secret",
        sandwich_checkpoint_id="ckpt_123 /tmp/raw",
    )
    payload = _event_to_dict()(event)

    assert payload["event"] == "memorysummaryreadrm-rf"
    assert payload["tool"] == "vibclibad"
    assert payload["capability_grant_id"] == "grantidsecret"
    assert payload["sandwich_checkpoint_id"] == "ckpt_123tmpraw"


def test_memory_audit_uses_safe_fallback_for_blank_labels(tmp_path: Path) -> None:
    event = _build_event()(tmp_path, event="///", tool="   ")
    payload = _event_to_dict()(event)

    assert payload["event"] == "memory_audit"
    assert payload["tool"] == "unknown-tool"


def test_memory_audit_normalizes_paths_total(tmp_path: Path) -> None:
    module = _audit_module()
    paths_count = getattr(module, "AuditPathsCount")(in_zone=3, drift=2, total=1)
    event = _build_event()(tmp_path, event="memory_summary_read", paths_count=paths_count)
    payload = _event_to_dict()(event)

    assert payload["paths_count"] == {"in_zone": 3, "drift": 2, "total": 5}


def test_memory_audit_event_contains_sanitized_trigger_metadata(tmp_path: Path) -> None:
    event = _build_event()(
        tmp_path,
        event="memory_review_trigger_dismissed",
        trigger=_TestTrigger(
            id="stale verification / raw path",
            action="dismissed",
            source="vib memory review && bad",
        ),
    )

    payload = _event_to_dict()(event)

    assert payload["trigger"] == {
        "id": "staleverificationrawpath",
        "action": "dismissed",
        "source": "vibmemoryreviewbad",
    }


def test_memory_audit_event_drops_unknown_trigger_action(tmp_path: Path) -> None:
    event = _build_event()(
        tmp_path,
        event="memory_review_trigger_action",
        trigger=_TestTrigger(id="stale_intent", action="execute", source="vib-cli"),
    )

    payload = _event_to_dict()(event)

    assert payload["trigger"] == {
        "id": "stale_intent",
        "action": None,
        "source": "vib-cli",
    }


def test_memory_audit_trigger_schema_drops_unknown_raw_fields(tmp_path: Path) -> None:
    event = _build_event()(
        tmp_path,
        event="memory_review_trigger_shown",
        trigger={
            "id": "missing_next_action",
            "action": "shown",
            "source": "vib memory review",
            "raw_path": str(tmp_path / "secret.py"),
            "memory_text": "redacted fixture text",
        },
    )

    payload = _event_to_dict()(event)
    rendered = json.dumps(payload, sort_keys=True)

    assert set(cast(dict[str, object], payload["trigger"]).keys()) == {"id", "action", "source"}
    assert "raw_path" not in rendered
    assert "memory_text" not in rendered
    assert "redacted fixture text" not in rendered
    assert str(tmp_path) not in rendered
