# === ANCHOR: MEMORY_AGENT_START ===
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

from vibelign.core.memory.models import (
    MemoryRelevantFile,
    MemoryState,
    MemoryTextField,
    MemoryVerification,
)
from vibelign.core.memory.store import load_memory_state, save_memory_state


HandoffDraftField = Literal[
    "session_summary",
    "active_intent",
    "next_action",
    "relevant_files",
    "verification",
    "risk_notes",
]
HandoffDraftAction = Literal["accepted", "dismissed", "undone"]


@dataclass(frozen=True)
class MemoryRecommendation:
    field: HandoffDraftField
    value: object
    reason: str
    proposal_hash: str
    source: str = "llm_proposed"


@dataclass(frozen=True)
class HandoffSummaryDraft:
    draft_id: str
    context_hash: str
    provider: str
    recommendations: tuple[MemoryRecommendation, ...] = ()
    should_write_memory: bool = False


@dataclass(frozen=True)
class HandoffDraftActionResult:
    ok: bool
    action: HandoffDraftAction
    field: HandoffDraftField
    proposal_hash: str
    message: str = ""


def build_handoff_summary_draft(
    memory_path: Path,
    handoff_data: dict[str, object],
    *,
    provider: str = "deterministic",
) -> HandoffSummaryDraft:
    state = load_memory_state(memory_path)
    context_packet = _context_packet(state, handoff_data)
    context_hash = _stable_hash(context_packet)
    recommendations = tuple(_recommendations(context_hash, state, handoff_data))
    return HandoffSummaryDraft(
        draft_id=f"draft_{context_hash[:12]}",
        context_hash=context_hash,
        provider=_safe_label(provider) or "deterministic",
        recommendations=recommendations,
        should_write_memory=False,
    )


def handoff_draft_to_payload(draft: HandoffSummaryDraft) -> dict[str, object]:
    return {
        "draft_id": draft.draft_id,
        "context_hash": draft.context_hash,
        "provider": draft.provider,
        "should_write_memory": draft.should_write_memory,
        "recommendations": [
            {
                "field": item.field,
                "value": item.value,
                "reason": item.reason,
                "proposal_hash": item.proposal_hash,
                "source": item.source,
            }
            for item in draft.recommendations
        ],
    }


def handoff_draft_from_payload(payload: object) -> HandoffSummaryDraft | None:
    if not isinstance(payload, dict):
        return None
    raw = cast(dict[object, object], payload)
    recommendations: list[MemoryRecommendation] = []
    raw_items = raw.get("recommendations")
    if isinstance(raw_items, list):
        for item in cast(list[object], raw_items):
            if not isinstance(item, dict):
                continue
            rec = cast(dict[object, object], item)
            field = rec.get("field")
            proposal_hash = _text(rec.get("proposal_hash"))
            if field not in {"session_summary", "active_intent", "next_action", "relevant_files", "verification", "risk_notes"} or not proposal_hash:
                continue
            recommendations.append(
                MemoryRecommendation(
                    field=cast(HandoffDraftField, field),
                    value=rec.get("value"),
                    reason=_text(rec.get("reason")),
                    proposal_hash=proposal_hash,
                    source=_text(rec.get("source")) or "llm_proposed",
                )
            )
    return HandoffSummaryDraft(
        draft_id=_text(raw.get("draft_id")),
        context_hash=_text(raw.get("context_hash")),
        provider=_text(raw.get("provider")) or "deterministic",
        recommendations=tuple(recommendations),
        should_write_memory=False,
    )


def accept_handoff_draft_field(
    memory_path: Path,
    draft: HandoffSummaryDraft,
    field: HandoffDraftField,
    *,
    accepted_by: str = "vib memory agent",
) -> HandoffDraftActionResult:
    recommendation = _find_recommendation(draft, field)
    if recommendation is None:
        return HandoffDraftActionResult(False, "accepted", field, "", "proposal not found")
    state = load_memory_state(memory_path)
    accepted = _accepted_proposals(state)
    if recommendation.proposal_hash in {item.get("proposal_hash") for item in accepted}:
        return HandoffDraftActionResult(True, "accepted", field, recommendation.proposal_hash, "already accepted")
    now = _utc_now()
    updated = _apply_recommendation(state, recommendation, accepted_by=accepted_by, accepted_at=now)
    updated = _record_proposal_action(
        updated,
        recommendation,
        action="accepted",
        actor=accepted_by,
        acted_at=now,
        before=_field_snapshot(state, field),
    )
    save_memory_state(memory_path, updated)
    return HandoffDraftActionResult(True, "accepted", field, recommendation.proposal_hash)


def dismiss_handoff_draft_field(
    memory_path: Path,
    draft: HandoffSummaryDraft,
    field: HandoffDraftField,
    *,
    dismissed_by: str = "vib memory agent",
) -> HandoffDraftActionResult:
    recommendation = _find_recommendation(draft, field)
    if recommendation is None:
        return HandoffDraftActionResult(False, "dismissed", field, "", "proposal not found")
    state = load_memory_state(memory_path)
    updated = _record_proposal_action(
        state,
        recommendation,
        action="dismissed",
        actor=dismissed_by,
        acted_at=_utc_now(),
        before=None,
    )
    save_memory_state(memory_path, updated)
    return HandoffDraftActionResult(True, "dismissed", field, recommendation.proposal_hash)


def undo_recent_handoff_acceptance(
    memory_path: Path,
    proposal_hash: str,
    *,
    undone_by: str = "vib memory agent",
) -> HandoffDraftActionResult:
    state = load_memory_state(memory_path)
    accepted = _accepted_proposals(state)
    target = next((item for item in accepted if item.get("proposal_hash") == proposal_hash), None)
    if target is None:
        return HandoffDraftActionResult(False, "undone", "session_summary", proposal_hash, "accepted proposal not found")
    field = cast(HandoffDraftField, str(target.get("field") or "session_summary"))
    restored = _restore_field_snapshot(state, field, target.get("before"))
    remaining = [item for item in accepted if item.get("proposal_hash") != proposal_hash]
    unknown = dict(restored.unknown_fields)
    unknown["recently_accepted_proposals"] = remaining
    history = _proposal_history(restored)
    history.append({"proposal_hash": proposal_hash, "field": field, "action": "undone", "actor": _safe_label(undone_by), "acted_at": _utc_now()})
    unknown["handoff_proposal_history"] = history
    save_memory_state(memory_path, replace(restored, unknown_fields=unknown))
    return HandoffDraftActionResult(True, "undone", field, proposal_hash)


def _recommendations(
    context_hash: str,
    state: MemoryState,
    handoff_data: dict[str, object],
) -> list[MemoryRecommendation]:
    items: list[MemoryRecommendation] = []
    for field, value, reason in (
        ("session_summary", _text(handoff_data.get("session_summary")), "handoff summary draft from current git/memory context"),
        ("active_intent", _text(handoff_data.get("active_intent")) or _text(handoff_data.get("session_summary")), "active intent inferred from handoff summary"),
        ("next_action", _text(handoff_data.get("first_next_action")), "next action supplied or inferred for continuation"),
        ("relevant_files", _relevant_files(handoff_data.get("relevant_files")), "explicit handoff relevant files"),
        ("verification", _string_list(handoff_data.get("verification")), "handoff verification snapshot"),
        ("risk_notes", _string_list(handoff_data.get("warnings")), "handoff warnings and risk notes"),
    ):
        if _empty_value(value):
            continue
        proposal_hash = _stable_hash({"context_hash": context_hash, "field": field, "value": value})
        if _is_dismissed(state, context_hash, proposal_hash):
            continue
        items.append(MemoryRecommendation(cast(HandoffDraftField, field), value, reason, proposal_hash))
    return items


def _apply_recommendation(
    state: MemoryState,
    recommendation: MemoryRecommendation,
    *,
    accepted_by: str,
    accepted_at: str,
) -> MemoryState:
    if recommendation.field == "session_summary":
        return replace(
            state,
            observed_context=[
                *state.observed_context,
                _accepted_summary_context(recommendation.value, accepted_by, accepted_at),
            ],
        )
    if recommendation.field == "active_intent":
        return replace(state, active_intent=_accepted_text_field(recommendation.value, accepted_by, accepted_at))
    if recommendation.field == "next_action":
        return replace(state, next_action=_accepted_text_field(recommendation.value, accepted_by, accepted_at))
    if recommendation.field == "risk_notes":
        risks = _accepted_text_fields(recommendation.value, accepted_by, accepted_at)
        return replace(state, risks=_merge_text_fields(state.risks, risks))
    if recommendation.field == "relevant_files":
        files = _accepted_relevant_files(recommendation.value, accepted_by, accepted_at)
        return replace(state, relevant_files=_merge_relevant_files(state.relevant_files, files))
    if recommendation.field == "verification":
        verification = [
            MemoryVerification(command=item, last_updated=accepted_at, updated_by=accepted_by)
            for item in _string_list(recommendation.value)
        ]
        return replace(state, verification=_merge_verification(state.verification, verification))
    return state


def _accepted_text_field(value: object, accepted_by: str, accepted_at: str) -> MemoryTextField:
    return MemoryTextField(
        text=_text(value),
        last_updated=accepted_at,
        updated_by=accepted_by,
        source="llm_proposed",
        proposed=False,
        accepted_by=accepted_by,
        accepted_at=accepted_at,
    )


def _accepted_text_fields(value: object, accepted_by: str, accepted_at: str) -> list[MemoryTextField]:
    return [_accepted_text_field(item, accepted_by, accepted_at) for item in _string_list(value)]


def _accepted_relevant_files(value: object, accepted_by: str, accepted_at: str) -> list[MemoryRelevantFile]:
    files: list[MemoryRelevantFile] = []
    for entry in _relevant_files(value):
        path = entry.get("path", "")
        why = entry.get("why", "Relevant to recent work.")
        if path:
            files.append(MemoryRelevantFile(path=path, why=why, source="llm_proposed", last_updated=accepted_at, updated_by=accepted_by, accepted_by=accepted_by, accepted_at=accepted_at))
    return files


def _accepted_summary_context(value: object, accepted_by: str, accepted_at: str):
    from vibelign.core.memory.models import MemoryObservedContext

    return MemoryObservedContext(
        kind="handoff_summary",
        summary=_text(value),
        path="",
        timestamp=accepted_at,
        source_tool=accepted_by,
    )


def _field_snapshot(state: MemoryState, field: HandoffDraftField) -> object:
    if field == "active_intent":
        return _text_field_snapshot(state.active_intent)
    if field == "next_action":
        return _text_field_snapshot(state.next_action)
    if field == "risk_notes":
        return [_text_field_snapshot(item) for item in state.risks]
    if field == "relevant_files":
        return [item.__dict__ for item in state.relevant_files]
    if field == "verification":
        return [item.__dict__ for item in state.verification]
    if field == "session_summary":
        return [item.__dict__ for item in state.observed_context]
    return None


def _restore_field_snapshot(state: MemoryState, field: HandoffDraftField, snapshot: object) -> MemoryState:
    if field == "active_intent":
        return replace(state, active_intent=_text_field_from_snapshot(snapshot))
    if field == "next_action":
        return replace(state, next_action=_text_field_from_snapshot(snapshot))
    if field == "session_summary":
        return replace(state, observed_context=_observed_context_list_from_snapshot(snapshot))
    if field == "risk_notes":
        return replace(state, risks=_text_field_list_from_snapshot(snapshot))
    if field == "relevant_files":
        return replace(state, relevant_files=_relevant_file_list_from_snapshot(snapshot))
    if field == "verification":
        return replace(state, verification=_verification_list_from_snapshot(snapshot))
    return state


def _text_field_snapshot(field: MemoryTextField | None) -> dict[str, object] | None:
    return None if field is None else dict(field.__dict__)


def _text_field_from_snapshot(snapshot: object) -> MemoryTextField | None:
    if not isinstance(snapshot, dict):
        return None
    raw = cast(dict[object, object], snapshot)
    text = _text(raw.get("text"))
    if not text:
        return None
    return MemoryTextField(
        text=text,
        last_updated=_text(raw.get("last_updated")),
        updated_by=_text(raw.get("updated_by")) or "legacy_work_memory",
        source="explicit" if raw.get("source") == "explicit" else "llm_proposed",
        stale=raw.get("stale") is True,
        proposed=raw.get("proposed") is True,
        from_previous_intent=raw.get("from_previous_intent") is True,
        accepted_by=_text(raw.get("accepted_by")),
        accepted_at=_text(raw.get("accepted_at")),
    )


def _text_field_list_from_snapshot(snapshot: object) -> list[MemoryTextField]:
    if not isinstance(snapshot, list):
        return []
    return [field for field in (_text_field_from_snapshot(item) for item in snapshot) if field is not None]


def _relevant_file_list_from_snapshot(snapshot: object) -> list[MemoryRelevantFile]:
    if not isinstance(snapshot, list):
        return []
    files: list[MemoryRelevantFile] = []
    for item in cast(list[object], snapshot):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        path = _text(raw.get("path"))
        if not path:
            continue
        source = raw.get("source")
        files.append(
            MemoryRelevantFile(
                path=path,
                why=_text(raw.get("why")) or "Relevant to recent work.",
                source="explicit" if source == "explicit" else ("llm_proposed" if source == "llm_proposed" else "observed"),
                last_updated=_text(raw.get("last_updated")),
                updated_by=_text(raw.get("updated_by")) or "legacy_work_memory",
                stale=raw.get("stale") is True,
                from_previous_intent=raw.get("from_previous_intent") is True,
                accepted_by=_text(raw.get("accepted_by")),
                accepted_at=_text(raw.get("accepted_at")),
            )
        )
    return files


def _verification_list_from_snapshot(snapshot: object) -> list[MemoryVerification]:
    if not isinstance(snapshot, list):
        return []
    items: list[MemoryVerification] = []
    for item in cast(list[object], snapshot):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        command = _text(raw.get("command"))
        if not command:
            continue
        related = raw.get("related_files")
        items.append(
            MemoryVerification(
                command=command,
                result=_text(raw.get("result")),
                last_updated=_text(raw.get("last_updated")),
                updated_by=_text(raw.get("updated_by")) or "legacy_work_memory",
                related_files=[_text(value) for value in cast(list[object], related) if _text(value)] if isinstance(related, list) else [],
                stale=raw.get("stale") is True,
                scope_unknown=raw.get("scope_unknown") is True,
            )
        )
    return items


def _observed_context_list_from_snapshot(snapshot: object):
    from vibelign.core.memory.models import MemoryObservedContext

    if not isinstance(snapshot, list):
        return []
    contexts: list[MemoryObservedContext] = []
    for item in cast(list[object], snapshot):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        contexts.append(
            MemoryObservedContext(
                kind=_text(raw.get("kind")),
                summary=_text(raw.get("summary")),
                path=_text(raw.get("path")),
                timestamp=_text(raw.get("timestamp")),
                source_tool=_text(raw.get("source_tool")) or "legacy_work_memory",
            )
        )
    return contexts


def _record_proposal_action(
    state: MemoryState,
    recommendation: MemoryRecommendation,
    *,
    action: HandoffDraftAction,
    actor: str,
    acted_at: str,
    before: object,
) -> MemoryState:
    unknown = dict(state.unknown_fields)
    history = _proposal_history(state)
    row: dict[str, object] = {
        "proposal_hash": recommendation.proposal_hash,
        "field": recommendation.field,
        "context_hash": recommendation.proposal_hash[:16],
        "action": action,
        "actor": _safe_label(actor),
        "acted_at": acted_at,
    }
    history.append(row)
    unknown["handoff_proposal_history"] = history[-100:]
    if action == "accepted":
        accepted = _accepted_proposals(state)
        accepted.append({**row, "before": before})
        unknown["recently_accepted_proposals"] = accepted[-100:]
    if action == "dismissed":
        dismissed = _dismissed_proposals(state)
        dismissed.append(row)
        unknown["handoff_dismissals"] = dismissed[-100:]
    return replace(state, unknown_fields=unknown)


def _merge_text_fields(existing: list[MemoryTextField], incoming: list[MemoryTextField]) -> list[MemoryTextField]:
    texts = {item.text for item in incoming}
    return [item for item in existing if item.text not in texts] + incoming


def _merge_relevant_files(existing: list[MemoryRelevantFile], incoming: list[MemoryRelevantFile]) -> list[MemoryRelevantFile]:
    paths = {item.path for item in incoming}
    return [item for item in existing if item.path not in paths] + incoming


def _merge_verification(existing: list[MemoryVerification], incoming: list[MemoryVerification]) -> list[MemoryVerification]:
    commands = {item.command for item in incoming}
    return [item for item in existing if item.command not in commands] + incoming


def _find_recommendation(draft: HandoffSummaryDraft, field: HandoffDraftField) -> MemoryRecommendation | None:
    return next((item for item in draft.recommendations if item.field == field), None)


def _context_packet(state: MemoryState, handoff_data: dict[str, object]) -> dict[str, object]:
    return {
        "active_intent": state.active_intent.text if state.active_intent else "",
        "next_action": state.next_action.text if state.next_action else "",
        "decisions": [item.text for item in state.decisions[-5:]],
        "handoff": handoff_data,
    }


def _is_dismissed(state: MemoryState, context_hash: str, proposal_hash: str) -> bool:
    _ = context_hash
    return proposal_hash in {str(item.get("proposal_hash")) for item in _dismissed_proposals(state)}


def _accepted_proposals(state: MemoryState) -> list[dict[str, object]]:
    return _dict_list(state.unknown_fields.get("recently_accepted_proposals"))


def _dismissed_proposals(state: MemoryState) -> list[dict[str, object]]:
    return _dict_list(state.unknown_fields.get("handoff_dismissals"))


def _proposal_history(state: MemoryState) -> list[dict[str, object]]:
    return _dict_list(state.unknown_fields.get("handoff_proposal_history"))


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _relevant_files(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    files: list[dict[str, str]] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        path = _text(raw.get("path"))
        why = _text(raw.get("why")) or "Relevant to recent work."
        if path:
            files.append({"path": path, "why": why})
    return files


def _string_list(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if not isinstance(value, list):
        return []
    return [_text(item) for item in cast(list[object], value) if _text(item)]


def _empty_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return not value
    return False


def _stable_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_label(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch.isalnum() or ch in {"_", "-", ":"})[:80]


def _text(value: object) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# === ANCHOR: MEMORY_AGENT_END ===
