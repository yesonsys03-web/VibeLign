# === ANCHOR: VIB_MEMORY_CMD_START ===
from __future__ import annotations

from argparse import Namespace
import json
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast

from vibelign.core.memory.store import (
    add_memory_decision,
    add_memory_relevant_file,
    ensure_memory_agent_fields,
    is_memory_read_only,
    load_memory_state,
    set_memory_active_intent,
    set_memory_next_action,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.core.schema_contracts import validate_memory_state_payload
from vibelign.terminal_render import cli_print

print = cli_print


class _MemoryReviewLike(Protocol):
    has_memory: bool
    active_intent: str
    next_action: str
    decisions: list[str]
    relevant_files: list[str]
    observed_context: list[str]
    verification: list[str]
    warnings: list[str]
    redaction: object
    suggestions: list[str]
    active_trigger_ids: list[str]


_ReviewMemory = Callable[[Path], _MemoryReviewLike]


def _memory_path() -> Path:
    root = resolve_project_root(Path.cwd())
    return MetaPaths(root).work_memory_path


def _print_lines(title: str, lines: list[str]) -> None:
    print(title)
    if not lines:
        print("- (none)")
        return
    for line in lines:
        print(f"- {line}")


def run_vib_memory_show(args: Namespace) -> None:
    path = _memory_path()
    _ = ensure_memory_agent_fields(path)
    state = load_memory_state(path)
    if getattr(args, "json", False):
        _audit_memory_summary_read(path)
        payload = _memory_state_payload(state)
        validate_memory_state_payload(payload)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print("VibeLign Memory")
    if state.downgrade_warning:
        print(f"Warning: {state.downgrade_warning}")
    active = state.active_intent.text if state.active_intent is not None else "(none)"
    next_action = state.next_action.text if state.next_action is not None else "(none)"
    print(f"Active intent: {active}")
    print(f"Next action: {next_action}")
    _print_lines("Decisions:", [item.text for item in state.decisions[-5:]])
    _print_lines(
        "Relevant files:",
        [f"{item.path} — {item.why} ({item.source})" for item in state.relevant_files[-5:]],
    )
    _print_lines("Verification:", _verification_lines(state))


def run_vib_memory_review(_: Namespace) -> None:
    path = _memory_path()
    review = _review_memory()(path)
    _audit_shown_triggers(path, review.active_trigger_ids)
    print("VibeLign Memory Review")
    if not review.has_memory:
        print("No memory yet.")
        _print_lines("Suggestions:", review.suggestions)
        return
    active = review.active_intent or "(none)"
    print(f"Active intent: {active}")
    print(f"Next action: {review.next_action or '(none)'}")
    _print_lines("Decisions:", review.decisions)
    _print_lines("Explicit relevant files:", review.relevant_files)
    _print_lines("Observed context:", review.observed_context)
    _print_lines("Next verification:", review.verification)
    _print_lines("Warnings:", review.warnings)
    secret_hits = int(getattr(review.redaction, "secret_hits", 0))
    privacy_hits = int(getattr(review.redaction, "privacy_hits", 0))
    summarized_fields = int(getattr(review.redaction, "summarized_fields", 0))
    print(f"Redaction: secrets={secret_hits}, privacy={privacy_hits}, summarized={summarized_fields}")
    _print_lines("Suggestions:", review.suggestions)


def run_vib_memory_decide(args: Namespace) -> None:
    path = _memory_path()
    decision = " ".join(getattr(args, "decision", []) or []).strip()
    if not decision:
        print("Usage: vib memory decide \"decision text\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; decision was not saved.")
        return
    add_memory_decision(path, decision)
    print("Memory decision saved.")


def run_vib_memory_intent(args: Namespace) -> None:
    path = _memory_path()
    intent = " ".join(getattr(args, "intent", []) or []).strip()
    if not intent:
        print("Usage: vib memory intent \"current goal\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; active intent was not saved.")
        return
    set_memory_active_intent(path, intent)
    print("Memory active intent saved.")


def run_vib_memory_next(args: Namespace) -> None:
    path = _memory_path()
    next_action = " ".join(getattr(args, "next_action", []) or []).strip()
    if not next_action:
        print("Usage: vib memory next \"next action\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; next action was not saved.")
        return
    set_memory_next_action(path, next_action, updated_by="vib memory next")
    print("Memory next action saved.")


def run_vib_memory_relevant(args: Namespace) -> None:
    path = _memory_path()
    rel_path = str(getattr(args, "path", "") or "").strip()
    why = " ".join(getattr(args, "why", []) or []).strip()
    if not rel_path or not why:
        print("Usage: vib memory relevant <path> \"why it matters\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; relevant file was not saved.")
        return
    add_memory_relevant_file(path, rel_path, why, source="explicit")
    print("Memory relevant file saved.")


def run_vib_memory_proposal_create(args: Namespace) -> None:
    from vibelign.core.memory.agent import build_handoff_summary_draft, handoff_draft_to_payload

    handoff_data: dict[str, object] = {}
    session_summary = str(getattr(args, "session_summary", "") or "").strip()
    first_next_action = str(getattr(args, "first_next_action", "") or "").strip()
    if session_summary:
        handoff_data["session_summary"] = session_summary
    if first_next_action:
        handoff_data["first_next_action"] = first_next_action
    relevant_files = _proposal_relevant_files(getattr(args, "relevant_file", None))
    verification = _proposal_string_list(getattr(args, "verification", None))
    risk_notes = _proposal_string_list(getattr(args, "risk_note", None))
    if relevant_files:
        handoff_data["relevant_files"] = relevant_files
    if verification:
        handoff_data["verification"] = verification
    if risk_notes:
        handoff_data["warnings"] = risk_notes
    draft = build_handoff_summary_draft(_memory_path(), handoff_data)
    print(json.dumps({"ok": True, "read_only": True, "draft": handoff_draft_to_payload(draft)}, ensure_ascii=False, sort_keys=True))


def _proposal_string_list(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _proposal_relevant_files(value: object) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for item in _proposal_string_list(value):
        if "::" in item:
            path, why = item.split("::", 1)
        elif " — " in item:
            path, why = item.split(" — ", 1)
        else:
            path, why = item, "Relevant to recent work."
        path = path.strip()
        why = why.strip()
        if path:
            entries.append({"path": path, "why": why or "Relevant to recent work."})
    return entries


def run_vib_memory_proposal_accept(args: Namespace) -> None:
    from vibelign.core.memory.agent import accept_handoff_draft_field

    draft = _draft_arg(args)
    field = _proposal_field_arg(args)
    if draft is None or field is None:
        print(json.dumps({"ok": False, "error": "--draft-json and --field are required"}, sort_keys=True))
        return
    result = accept_handoff_draft_field(_memory_path(), draft, field, accepted_by="vib memory proposal accept")
    print(json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def run_vib_memory_proposal_dismiss(args: Namespace) -> None:
    from vibelign.core.memory.agent import dismiss_handoff_draft_field

    draft = _draft_arg(args)
    field = _proposal_field_arg(args)
    if draft is None or field is None:
        print(json.dumps({"ok": False, "error": "--draft-json and --field are required"}, sort_keys=True))
        return
    result = dismiss_handoff_draft_field(_memory_path(), draft, field, dismissed_by="vib memory proposal dismiss")
    print(json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def run_vib_memory_proposal_undo(args: Namespace) -> None:
    from vibelign.core.memory.agent import undo_recent_handoff_acceptance

    proposal_hash = str(getattr(args, "proposal_hash", "") or "")
    if not proposal_hash:
        print(json.dumps({"ok": False, "error": "--proposal-hash is required"}, sort_keys=True))
        return
    result = undo_recent_handoff_acceptance(_memory_path(), proposal_hash, undone_by="vib memory proposal undo")
    print(json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True))


def _draft_arg(args: Namespace):
    from vibelign.core.memory.agent import handoff_draft_from_payload

    raw = str(getattr(args, "draft_json", "") or "")
    if not raw:
        return None
    try:
        return handoff_draft_from_payload(json.loads(raw))
    except json.JSONDecodeError:
        return None


def _proposal_field_arg(args: Namespace):
    from vibelign.core.memory.agent import HandoffDraftField

    field = str(getattr(args, "field", "") or "")
    if field in {"session_summary", "active_intent", "next_action", "relevant_files", "verification", "risk_notes"}:
        return cast(HandoffDraftField, field)
    return None


def _review_memory() -> _ReviewMemory:
    module = import_module("vibelign.core.memory.review")
    return cast(_ReviewMemory, getattr(module, "review_memory"))


def _audit_shown_triggers(path: Path, trigger_ids: list[str]) -> None:
    if not trigger_ids:
        return
    root = path.parent.parent
    module = import_module("vibelign.core.memory.audit")
    append_event = cast(Callable[..., None], getattr(module, "append_memory_audit_event"))
    build_event = cast(Callable[..., object], getattr(module, "build_memory_audit_event"))
    audit_path = cast(Callable[[Path], Path], getattr(module, "memory_audit_path"))
    audit_trigger = cast(type, getattr(module, "AuditTrigger"))
    for trigger_id in trigger_ids:
        append_event(
            audit_path(root),
            build_event(
                root,
                event="memory_review_trigger_shown",
                tool="vib-cli",
                trigger=audit_trigger(
                    id=trigger_id,
                    action="shown",
                    source="vib memory review",
                ),
            ),
        )


def _audit_memory_summary_read(path: Path) -> None:
    root = path.parent.parent
    module = import_module("vibelign.core.memory.audit")
    append_event = cast(Callable[..., None], getattr(module, "append_memory_audit_event"))
    build_event = cast(Callable[..., object], getattr(module, "build_memory_audit_event"))
    audit_path = cast(Callable[[Path], Path], getattr(module, "memory_audit_path"))
    append_event(
        audit_path(root),
        build_event(
            root,
            event="memory_summary_read",
            tool="vib-cli",
            result="success",
        ),
    )


def _verification_lines(state) -> list[str]:
    lines: list[str] = []
    for item in state.verification[-5:]:
        line = _dedupe_stale_labels(item.command)
        if item.stale and "(stale" not in line:
            line = f"{line} (stale)"
        lines.append(line)
    return lines


def _memory_state_payload(state) -> dict[str, object]:
    return {
        "schema_version": state.schema_version,
        "active_intent": _text_field_payload(state.active_intent),
        "next_action": _text_field_payload(state.next_action),
        "decisions": [_text_field_payload(item) for item in state.decisions],
        "relevant_files": [
            {
                "path": item.path,
                "why": item.why,
                "source": item.source,
                "last_updated": item.last_updated,
                "updated_by": item.updated_by,
                "stale": item.stale,
                "from_previous_intent": item.from_previous_intent,
                "accepted_by": item.accepted_by,
                "accepted_at": item.accepted_at,
            }
            for item in state.relevant_files
        ],
        "verification": [
            {
                "command": item.command,
                "result": item.result,
                "last_updated": item.last_updated,
                "updated_by": item.updated_by,
                "related_files": item.related_files,
                "stale": item.stale,
                "scope_unknown": item.scope_unknown,
            }
            for item in state.verification
        ],
        "risks": [_text_field_payload(item) for item in state.risks],
        "observed_context": [
            {
                "kind": item.kind,
                "summary": item.summary,
                "path": item.path,
                "timestamp": item.timestamp,
                "source_tool": item.source_tool,
            }
            for item in state.observed_context
        ],
        "archived_decisions": [_text_field_payload(item) for item in state.archived_decisions],
        "downgrade_warning": state.downgrade_warning,
    }


def _text_field_payload(field) -> dict[str, object] | None:
    if field is None:
        return None
    return {
        "text": field.text,
        "last_updated": field.last_updated,
        "updated_by": field.updated_by,
        "source": field.source,
        "stale": field.stale,
        "proposed": field.proposed,
        "from_previous_intent": field.from_previous_intent,
        "accepted_by": field.accepted_by,
        "accepted_at": field.accepted_at,
    }


def _dedupe_stale_labels(line: str) -> str:
    marker = " (stale: scope unknown)"
    while line.count(marker) > 1:
        line = line.replace(marker + marker, marker)
    return line

# === ANCHOR: VIB_MEMORY_CMD_END ===
