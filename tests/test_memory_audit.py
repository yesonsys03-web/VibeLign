import json
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast


@dataclass(frozen=True)
class _TestRedaction:
    secret_hits: int = 0
    privacy_hits: int = 0
    summarized_fields: int = 0


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
