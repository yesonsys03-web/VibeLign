from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
from typing import cast

from vibelign.core.memory.audit import (
    append_memory_audit_event,
    build_memory_audit_event,
    memory_audit_path,
)
from vibelign.core.memory.redaction import build_redacted_memory_summary
from vibelign.core.memory.store import load_memory_state
from vibelign.core.meta_paths import MetaPaths


class TextContentFactory(Protocol):
    def __call__(self, *, type: str, text: str) -> object: ...


def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]


def handle_memory_summary_read(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    _ = arguments
    state = load_memory_state(MetaPaths(root).work_memory_path)
    summary = build_redacted_memory_summary(state)
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(
            root,
            event="memory_summary_read",
            tool="mcp",
            redaction=summary.redaction,
        ),
    )
    payload: dict[str, object] = {
        "ok": True,
        "source": ".vibelign/work_memory.json",
        "provenance": "redacted_typed_memory_summary",
        "read_only": True,
        "active_intent": summary.active_intent,
        "next_action": summary.next_action,
        "decisions": summary.decisions,
        "relevant_files": summary.relevant_files,
        "observed_context": summary.observed_context,
        "verification": summary.verification,
        "warnings": summary.warnings,
        "redaction": {
            "secret_hits": summary.redaction.secret_hits,
            "privacy_hits": summary.redaction.privacy_hits,
            "summarized_fields": summary.redaction.summarized_fields,
        },
    }
    if state.downgrade_warning:
        payload["warnings"] = summary.warnings + [state.downgrade_warning]
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def handle_handoff_draft_create(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.memory.agent import build_handoff_summary_draft, handoff_draft_to_payload

    draft = build_handoff_summary_draft(
        MetaPaths(root).work_memory_path,
        cast(dict[str, object], arguments.get("handoff_data") if isinstance(arguments.get("handoff_data"), dict) else arguments),
        provider=str(arguments.get("provider", "deterministic")),
    )
    payload = {"ok": True, "read_only": True, "draft": handoff_draft_to_payload(draft)}
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(root, event="handoff_draft_create", tool="mcp"),
    )
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def handle_handoff_draft_accept(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.memory.agent import HandoffDraftField, HandoffSummaryDraft, accept_handoff_draft_field

    draft = _draft_from_arguments(arguments)
    field = _draft_field(arguments.get("field"))
    if draft is None or field is None:
        return _text(text_content, json.dumps({"ok": False, "error": "draft and field are required"}, sort_keys=True))
    result = accept_handoff_draft_field(
        MetaPaths(root).work_memory_path,
        cast(HandoffSummaryDraft, draft),
        cast(HandoffDraftField, field),
        accepted_by=str(arguments.get("accepted_by", "mcp")),
    )
    _audit_handoff_action(root, "handoff_draft_accept", result.ok)
    return _text(text_content, json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def handle_handoff_draft_dismiss(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.memory.agent import HandoffDraftField, HandoffSummaryDraft, dismiss_handoff_draft_field

    draft = _draft_from_arguments(arguments)
    field = _draft_field(arguments.get("field"))
    if draft is None or field is None:
        return _text(text_content, json.dumps({"ok": False, "error": "draft and field are required"}, sort_keys=True))
    result = dismiss_handoff_draft_field(
        MetaPaths(root).work_memory_path,
        cast(HandoffSummaryDraft, draft),
        cast(HandoffDraftField, field),
        dismissed_by=str(arguments.get("dismissed_by", "mcp")),
    )
    _audit_handoff_action(root, "handoff_draft_dismiss", result.ok)
    return _text(text_content, json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def handle_handoff_draft_undo(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.memory.agent import undo_recent_handoff_acceptance

    proposal_hash = str(arguments.get("proposal_hash", ""))
    if not proposal_hash:
        return _text(text_content, json.dumps({"ok": False, "error": "proposal_hash is required"}, sort_keys=True))
    result = undo_recent_handoff_acceptance(
        MetaPaths(root).work_memory_path,
        proposal_hash,
        undone_by=str(arguments.get("undone_by", "mcp")),
    )
    _audit_handoff_action(root, "handoff_draft_undo", result.ok)
    return _text(text_content, json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def _draft_from_arguments(arguments: dict[str, object]) -> object | None:
    from vibelign.core.memory.agent import handoff_draft_from_payload

    return handoff_draft_from_payload(arguments.get("draft"))


def _draft_field(value: object) -> object | None:
    if value in {"session_summary", "active_intent", "next_action", "relevant_files", "verification", "risk_notes"}:
        return value
    return None


def _audit_handoff_action(root: Path, event: str, ok: bool) -> None:
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(root, event=event, tool="mcp", result="success" if ok else "denied"),
    )
