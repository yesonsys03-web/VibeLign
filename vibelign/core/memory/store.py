# === ANCHOR: MEMORY_STORE_START ===
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Callable, Literal, Protocol, cast

from vibelign.core.memory.models import (
    MEMORY_SCHEMA_VERSION,
    MemoryObservedContext,
    MemoryRelevantFile,
    MemorySource,
    MemoryState,
    MemoryTextField,
    MemoryVerification,
)
from vibelign.core.work_memory import (
    RelevantFileEntry,
    WorkMemoryEvent,
    WorkMemorySummary,
    WorkMemoryState,
    build_transfer_summary,
    default_work_memory_state,
    load_work_memory,
    prune_work_memory_state,
)


class _MemoryFreshnessLike(Protocol):
    verification_freshness: str
    stale_verification_commands: list[str]
    stale_intent: bool
    stale_relevant_files: list[str]


_AssessMemoryFreshness = Callable[[MemoryState], _MemoryFreshnessLike]


_MEMORY_STATE_FIELDS = {
    "schema_version",
    "active_intent",
    "decisions",
    "relevant_files",
    "verification",
    "risks",
    "next_action",
    "observed_context",
    "archived_decisions",
}
_LEGACY_WORK_MEMORY_FIELDS = {
    "updated_at",
    "recent_events",
    "warnings",
    "verification_updated_at",
}
_MAX_MEMORY_DECISIONS = 50
_MAX_MEMORY_RELEVANT_FILES = 100
_MAX_MEMORY_OBSERVED_CONTEXT = 200
_MAX_MEMORY_VERIFICATION_PER_SCOPE = 30
_AUTO_ESTIMATED_HANDOFF_WARNING = (
    "⚠️ 이 핸드오프는 자동 추정값입니다. work_memory.json 직접 확인 필수."
)


# === ANCHOR: MEMORY_STORE__LOAD_MEMORY_STATE_START ===
def load_memory_state(path: Path) -> MemoryState:
    raw = _read_raw_object(path)
    if raw is not None and _schema_version(raw) > MEMORY_SCHEMA_VERSION:
        legacy_state = _legacy_state_from_raw(raw)
        migrated = _migrate_legacy_state(legacy_state)
        return compact_memory_state(MemoryState(
            schema_version=_schema_version(raw),
            active_intent=migrated.active_intent,
            decisions=migrated.decisions,
            relevant_files=migrated.relevant_files,
            verification=migrated.verification,
            risks=migrated.risks,
            next_action=migrated.next_action,
            observed_context=migrated.observed_context,
            archived_decisions=migrated.archived_decisions,
            unknown_fields=_unknown_fields(raw),
            read_only=True,
            downgrade_warning=(
                f"memory schema_version={_schema_version(raw)} is newer than this VibeLign supports — "
                "upgrade or run with --legacy-readonly"
            ),
        ))
    if raw is not None and _looks_like_current_memory_state(raw):
        return compact_memory_state(_memory_state_from_raw(raw))
    return compact_memory_state(_migrate_legacy_state(load_work_memory(path), unknown_fields=_unknown_fields(raw or {})))
# === ANCHOR: MEMORY_STORE__LOAD_MEMORY_STATE_END ===


def build_handoff_summary(path: Path) -> WorkMemorySummary | None:
    memory_state = load_memory_state(path)
    summary = (
        _summary_from_memory_state(memory_state)
        if memory_state.read_only
        else build_transfer_summary(path) or _summary_from_memory_state(memory_state)
    )
    if summary is None:
        if not memory_state.downgrade_warning:
            return None
        return {
            "warnings": [memory_state.downgrade_warning],
            "state_references": [".vibelign/work_memory.json"],
        }
    _merge_memory_state_summary(summary, memory_state)
    if not memory_state.decisions and not memory_state.verification:
        summary["handoff_assurance_warning"] = _AUTO_ESTIMATED_HANDOFF_WARNING
    if memory_state.downgrade_warning:
        warnings = list(summary.get("warnings", []))
        if memory_state.downgrade_warning not in warnings:
            warnings.append(memory_state.downgrade_warning)
        summary["warnings"] = warnings
    return summary


def is_memory_read_only(path: Path) -> bool:
    return load_memory_state(path).read_only


def ensure_memory_agent_fields(
    path: Path,
    *,
    updated_by: str = "vib memory agent",
) -> bool:
    state = load_memory_state(path)
    if state.read_only:
        return False

    active_intent = state.active_intent
    next_action = state.next_action
    changed = False
    now = _utc_now()

    if active_intent is None:
        active_text = _agent_active_intent(state)
        if active_text:
            active_intent = MemoryTextField(
                text=active_text,
                last_updated=now,
                updated_by=updated_by,
                source="system",
                proposed=True,
            )
            changed = True

    if _agent_can_replace_next_action(next_action):
        next_text = _agent_next_action(state)
        if next_text and (next_action is None or next_action.text != next_text):
            next_action = MemoryTextField(
                text=next_text,
                last_updated=now,
                updated_by=updated_by,
                source="system",
                proposed=True,
            )
            changed = True

    if not changed:
        return False
    save_memory_state(path, replace(state, active_intent=active_intent, next_action=next_action))
    return True


def save_memory_state(path: Path, state: MemoryState) -> None:
    if state.read_only or state.schema_version > MEMORY_SCHEMA_VERSION:
        raise ValueError("memory schema is newer than this VibeLign supports; refusing to write")
    compacted = compact_memory_state(state)
    payload = _memory_state_to_raw(compacted)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    _ = tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _ = tmp_path.replace(path)


def add_memory_decision(path: Path, message: str, *, updated_by: str = "vib memory decide") -> None:
    text = _string(message)
    if not text:
        return
    state = load_memory_state(path)
    now = _utc_now()
    decision = MemoryTextField(
        text=text,
        last_updated=now,
        updated_by=updated_by,
        source="explicit",
    )
    decisions = [item for item in state.decisions if item.text != text] + [decision]
    active_intent = state.active_intent or replace(decision, proposed=True)
    save_memory_state(path, replace(state, decisions=decisions, active_intent=active_intent))


def set_memory_active_intent(
    path: Path,
    message: str,
    *,
    updated_by: str = "vib memory intent",
) -> None:
    text = _string(message)
    if not text:
        return
    state = load_memory_state(path)
    active_intent = MemoryTextField(
        text=text,
        last_updated=_utc_now(),
        updated_by=updated_by,
        source="explicit",
        proposed=False,
    )
    save_memory_state(path, replace(state, active_intent=active_intent))


def set_memory_next_action(path: Path, message: str, *, updated_by: str = "vib transfer --handoff") -> None:
    text = _string(message)
    if not text:
        return
    state = load_memory_state(path)
    next_action = MemoryTextField(
        text=text,
        last_updated=_utc_now(),
        updated_by=updated_by,
        source="explicit",
    )
    save_memory_state(path, replace(state, next_action=next_action))


def add_memory_relevant_file(
    path: Path,
    rel_path: str,
    why: str,
    *,
    source: str = "explicit",
    updated_by: str = "vib memory relevant",
) -> None:
    safe_path = _safe_relative_path(rel_path)
    reason = _string(why)
    if not safe_path or not reason:
        return
    state = load_memory_state(path)
    relevant_file = MemoryRelevantFile(
        path=safe_path,
        why=reason,
        source="explicit" if source == "explicit" else "observed",
        last_updated=_utc_now(),
        updated_by=updated_by,
    )
    relevant_files = [
        item for item in state.relevant_files if item.path != safe_path
    ] + [relevant_file]
    save_memory_state(path, replace(state, relevant_files=relevant_files))


def add_memory_verification(
    path: Path,
    message: str,
    *,
    updated_by: str = "vib transfer --handoff",
) -> None:
    text = _string(message)
    if not text:
        return
    state = load_memory_state(path)
    key = _verification_key(text)
    verification = MemoryVerification(
        command=text,
        last_updated=_utc_now(),
        updated_by=updated_by,
        scope_unknown=True,
    )
    verification_items = [
        item for item in state.verification if _verification_key(item.command) != key
    ] + [verification]
    save_memory_state(path, replace(state, verification=verification_items))


def add_memory_observed_context(
    path: Path,
    *,
    kind: str,
    summary: str,
    context_path: str = "",
    source_tool: str = "legacy_work_memory",
) -> None:
    event_kind = _string(kind) or "event"
    text = _string(summary)
    safe_path = _safe_relative_path(context_path) if context_path else ""
    if not text:
        return
    state = load_memory_state(path)
    event = MemoryObservedContext(
        kind=event_kind,
        summary=text,
        path=safe_path,
        timestamp=_utc_now(),
        source_tool=_string(source_tool) or "legacy_work_memory",
    )
    save_memory_state(
        path,
        replace(state, observed_context=state.observed_context + [event]),
    )


def compact_memory_state(state: MemoryState) -> MemoryState:
    compacted = state
    if len(compacted.decisions) > _MAX_MEMORY_DECISIONS:
        overflow_count = len(compacted.decisions) - _MAX_MEMORY_DECISIONS
        archived_overflow = [
            replace(decision, from_previous_intent=True)
            for decision in compacted.decisions[:overflow_count]
        ]
        compacted = replace(
            compacted,
            decisions=compacted.decisions[overflow_count:],
            archived_decisions=compacted.archived_decisions + archived_overflow,
        )
    if len(compacted.relevant_files) > _MAX_MEMORY_RELEVANT_FILES:
        compacted = replace(
            compacted,
            relevant_files=compacted.relevant_files[-_MAX_MEMORY_RELEVANT_FILES:],
        )
    if len(compacted.observed_context) > _MAX_MEMORY_OBSERVED_CONTEXT:
        compacted = replace(
            compacted,
            observed_context=compacted.observed_context[-_MAX_MEMORY_OBSERVED_CONTEXT:],
        )
    verification = _compact_verification(compacted.verification)
    if len(verification) != len(compacted.verification):
        compacted = replace(compacted, verification=verification)
    return compacted


def _compact_verification(items: list[MemoryVerification]) -> list[MemoryVerification]:
    counts_by_scope: dict[tuple[str, ...], int] = {}
    kept_reversed: list[MemoryVerification] = []
    for item in reversed(items):
        scope = _verification_scope_key(item)
        count = counts_by_scope.get(scope, 0)
        if count >= _MAX_MEMORY_VERIFICATION_PER_SCOPE:
            continue
        counts_by_scope[scope] = count + 1
        kept_reversed.append(item)
    kept_reversed.reverse()
    return kept_reversed


def _verification_scope_key(item: MemoryVerification) -> tuple[str, ...]:
    if not item.related_files:
        return ("__scope_unknown__",)
    return tuple(sorted(set(item.related_files)))


def _memory_state_to_raw(state: MemoryState) -> dict[str, object]:
    payload: dict[str, object] = {
        key: value
        for key, value in state.unknown_fields.items()
        if key not in _LEGACY_WORK_MEMORY_FIELDS
    }
    payload.update(
        {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "active_intent": _text_field_to_raw(state.active_intent),
            "decisions": [_text_field_to_raw(item) for item in state.decisions],
            "relevant_files": [_relevant_file_to_raw(item) for item in state.relevant_files],
            "verification": [_verification_to_raw(item) for item in state.verification],
            "risks": [_text_field_to_raw(item) for item in state.risks],
            "next_action": _text_field_to_raw(state.next_action),
            "observed_context": [_observed_context_to_raw(item) for item in state.observed_context],
            "archived_decisions": [_text_field_to_raw(item) for item in state.archived_decisions],
        }
    )
    return payload


def _text_field_to_raw(value: MemoryTextField | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "text": value.text,
        "last_updated": value.last_updated,
        "updated_by": value.updated_by,
        "source": value.source,
        "stale": value.stale,
        "proposed": value.proposed,
        "from_previous_intent": value.from_previous_intent,
        "accepted_by": value.accepted_by,
        "accepted_at": value.accepted_at,
    }


def _relevant_file_to_raw(value: MemoryRelevantFile) -> dict[str, object]:
    return {
        "path": value.path,
        "why": value.why,
        "source": value.source,
        "last_updated": value.last_updated,
        "updated_by": value.updated_by,
        "stale": value.stale,
        "from_previous_intent": value.from_previous_intent,
        "accepted_by": value.accepted_by,
        "accepted_at": value.accepted_at,
    }


def _verification_to_raw(value: MemoryVerification) -> dict[str, object]:
    return {
        "command": value.command,
        "result": value.result,
        "last_updated": value.last_updated,
        "updated_by": value.updated_by,
        "related_files": value.related_files,
        "stale": value.stale,
        "scope_unknown": value.scope_unknown,
    }


def _observed_context_to_raw(value: MemoryObservedContext) -> dict[str, object]:
    return {
        "kind": value.kind,
        "summary": value.summary,
        "path": value.path,
        "timestamp": value.timestamp,
        "source_tool": value.source_tool,
    }


def _read_raw_object(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return {
        str(key): value for key, value in cast(dict[object, object], loaded).items()
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _schema_version(raw: dict[str, object]) -> int:
    value = raw.get("schema_version", MEMORY_SCHEMA_VERSION)
    return value if isinstance(value, int) else MEMORY_SCHEMA_VERSION


def _unknown_fields(raw: dict[str, object]) -> dict[str, object]:
    known_fields = _MEMORY_STATE_FIELDS | _LEGACY_WORK_MEMORY_FIELDS
    return {key: value for key, value in raw.items() if key not in known_fields}


def _looks_like_current_memory_state(raw: dict[str, object]) -> bool:
    typed_slots = (
        "active_intent",
        "next_action",
        "risks",
        "observed_context",
        "archived_decisions",
    )
    if any(key in raw for key in typed_slots):
        return True
    if any(_list_contains_dict(raw.get(key)) for key in ("decisions", "verification")):
        return True
    return _relevant_files_include_typed_metadata(raw.get("relevant_files"))


def _list_contains_dict(value: object) -> bool:
    return isinstance(value, list) and any(isinstance(item, dict) for item in cast(list[object], value))


def _relevant_files_include_typed_metadata(value: object) -> bool:
    if not isinstance(value, list):
        return False
    typed_keys = {"last_updated", "updated_by", "stale", "from_previous_intent"}
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        if any(key in raw for key in typed_keys):
            return True
    return False


def _memory_state_from_raw(raw: dict[str, object]) -> MemoryState:
    legacy_state = _legacy_state_from_raw(raw)
    decisions = _memory_text_field_list(raw.get("decisions"))
    active_intent = _memory_text_field(raw.get("active_intent")) or _active_intent_from_decisions(decisions)
    return MemoryState(
        schema_version=_schema_version(raw),
        active_intent=active_intent,
        decisions=decisions,
        relevant_files=_memory_relevant_file_list(raw.get("relevant_files")),
        verification=_memory_verification_list(raw.get("verification")),
        risks=_memory_text_field_list(raw.get("risks")) + _migrate_warnings(legacy_state),
        next_action=_memory_text_field(raw.get("next_action")),
        observed_context=(
            _memory_observed_context_list(raw.get("observed_context"))
            + _migrate_observed_context(legacy_state)
        ),
        archived_decisions=_memory_text_field_list(raw.get("archived_decisions")),
        unknown_fields=_unknown_fields(raw),
    )


def _memory_text_field(value: object) -> MemoryTextField | None:
    if isinstance(value, str):
        text = _string(value)
        return MemoryTextField(text=text, source="legacy") if text else None
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    text = _string(raw.get("text"))
    if not text:
        return None
    source = _memory_source(raw.get("source"))
    return MemoryTextField(
        text=text,
        last_updated=_string(raw.get("last_updated")),
        updated_by=_string(raw.get("updated_by")) or "legacy_work_memory",
        source=source,
        stale=raw.get("stale") is True,
        proposed=raw.get("proposed") is True,
        from_previous_intent=raw.get("from_previous_intent") is True,
        accepted_by=_string(raw.get("accepted_by")),
        accepted_at=_string(raw.get("accepted_at")),
    )


def _memory_text_field_list(value: object) -> list[MemoryTextField]:
    if not isinstance(value, list):
        return []
    fields: list[MemoryTextField] = []
    for item in cast(list[object], value):
        field = _memory_text_field(item)
        if field is not None:
            fields.append(field)
    return fields


def _memory_source(value: object) -> MemorySource:
    source = _string(value)
    if source == "explicit":
        return "explicit"
    if source == "observed":
        return "observed"
    if source == "system":
        return "system"
    if source == "llm_proposed":
        return "llm_proposed"
    return "legacy"


def _active_intent_from_decisions(decisions: list[MemoryTextField]) -> MemoryTextField | None:
    if not decisions:
        return None
    latest = decisions[-1]
    return MemoryTextField(
        text=latest.text,
        last_updated=latest.last_updated,
        updated_by=latest.updated_by,
        source=latest.source,
        stale=latest.stale,
        proposed=True,
        from_previous_intent=latest.from_previous_intent,
        accepted_by=latest.accepted_by,
        accepted_at=latest.accepted_at,
    )


def _memory_relevant_file_list(value: object) -> list[MemoryRelevantFile]:
    if not isinstance(value, list):
        return []
    files: list[MemoryRelevantFile] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        path = _safe_relative_path(raw.get("path"))
        if not path:
            continue
        source = _string(raw.get("source"))
        files.append(
            MemoryRelevantFile(
                path=path,
                why=_string(raw.get("why")) or "Relevant to recent work.",
                source=_memory_relevant_file_source(source),
                last_updated=_string(raw.get("last_updated")),
                updated_by=_string(raw.get("updated_by")) or "legacy_work_memory",
                stale=raw.get("stale") is True,
                from_previous_intent=raw.get("from_previous_intent") is True,
                accepted_by=_string(raw.get("accepted_by")),
                accepted_at=_string(raw.get("accepted_at")),
            )
        )
    return files


def _memory_relevant_file_source(value: str) -> Literal["explicit", "observed", "llm_proposed"]:
    if value == "explicit":
        return "explicit"
    if value == "llm_proposed":
        return "llm_proposed"
    return "observed"


def _memory_verification_list(value: object) -> list[MemoryVerification]:
    if not isinstance(value, list):
        return []
    items: list[MemoryVerification] = []
    for item in cast(list[object], value):
        if isinstance(item, str):
            command = _string(item)
            if command:
                items.append(MemoryVerification(command=command, stale=True, scope_unknown=True))
            continue
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        command = _string(raw.get("command"))
        if not command:
            continue
        items.append(
            MemoryVerification(
                command=command,
                result=_string(raw.get("result")),
                last_updated=_string(raw.get("last_updated")),
                updated_by=_string(raw.get("updated_by")) or "legacy_work_memory",
                related_files=_safe_path_list(raw.get("related_files")),
                stale=raw.get("stale") is True,
                scope_unknown=raw.get("scope_unknown") is True,
            )
        )
    return items


def _safe_path_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths: list[str] = []
    for item in cast(list[object], value):
        path = _safe_relative_path(item)
        if path:
            paths.append(path)
    return paths


def _memory_observed_context_list(value: object) -> list[MemoryObservedContext]:
    if not isinstance(value, list):
        return []
    contexts: list[MemoryObservedContext] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        kind = _string(raw.get("kind")) or "event"
        summary = _string(raw.get("summary")) or "(no details)"
        path = _safe_relative_path(raw.get("path"))
        if raw.get("path") and not path:
            continue
        contexts.append(
            MemoryObservedContext(
                kind=kind,
                summary=summary,
                path=path,
                timestamp=_string(raw.get("timestamp")),
                source_tool=_string(raw.get("source_tool")) or "legacy_work_memory",
            )
        )
    return contexts


def _legacy_state_from_raw(raw: dict[str, object]) -> WorkMemoryState:
    state = default_work_memory_state()
    state["updated_at"] = _string(raw.get("updated_at"))
    state["verification_updated_at"] = _string(raw.get("verification_updated_at"))
    state["recent_events"] = _event_list(raw.get("recent_events"))
    state["relevant_files"] = _relevant_file_list(raw.get("relevant_files"))
    state["warnings"] = _event_list(raw.get("warnings"))
    state["decisions"] = _string_list(raw.get("decisions"))
    state["verification"] = _string_list(raw.get("verification"))
    state["next_action"] = _string(raw.get("next_action"))
    return prune_work_memory_state(state)


def _event_list(value: object) -> list[WorkMemoryEvent]:
    if not isinstance(value, list):
        return []
    events: list[WorkMemoryEvent] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        raw_path = raw.get("path")
        path = _safe_relative_path(raw_path)
        if raw_path and not path:
            continue
        event: WorkMemoryEvent = {
            "time": _string(raw.get("time")),
            "kind": _string(raw.get("kind")),
            "path": path,
            "message": _string(raw.get("message")),
            "action": _string(raw.get("action")),
        }
        if any(event.values()):
            events.append(event)
    return events


def _relevant_file_list(value: object) -> list[RelevantFileEntry]:
    if not isinstance(value, list):
        return []
    entries: list[RelevantFileEntry] = []
    for item in cast(list[object], value):
        if isinstance(item, str):
            path = _safe_relative_path(item)
            if path:
                entries.append(
                    {"path": path, "why": "Recently touched by watch.", "source": "watch"}
                )
            continue
        if not isinstance(item, dict):
            continue
        raw = cast(dict[object, object], item)
        path = _safe_relative_path(raw.get("path"))
        if not path:
            continue
        source = _string(raw.get("source"))
        entries.append(
            {
                "path": path,
                "why": _string(raw.get("why")) or "Relevant to recent work.",
                "source": source if source in {"explicit", "watch"} else "watch",
            }
        )
    return entries


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string(item) for item in cast(list[object], value) if _string(item)]


def _string(value: object) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _safe_relative_path(value: object) -> str:
    text = _string(value).replace("\\", "/")
    parts = [part for part in text.split("/") if part]
    if not text or text.startswith("/") or ".." in parts or _looks_like_windows_absolute(text):
        return ""
    return text


def _looks_like_windows_absolute(value: str) -> bool:
    return len(value) >= 3 and value[1:3] == ":/" and value[0].isalpha()


def _summary_from_memory_state(memory_state: MemoryState) -> WorkMemorySummary | None:
    summary: WorkMemorySummary = {"state_references": [".vibelign/work_memory.json"]}
    if memory_state.active_intent is not None:
        summary["active_intent"] = memory_state.active_intent.text
    if memory_state.next_action is not None:
        summary["first_next_action"] = memory_state.next_action.text
        summary["concrete_next_steps"] = [memory_state.next_action.text]
    changed_files = _memory_changed_files(memory_state)
    if changed_files:
        summary["changed_files"] = changed_files[:5]
        latest_paths = ", ".join(f"`{item}`" for item in changed_files[:3])
        summary["session_summary"] = (
            f"현재 세션에서 {latest_paths} 등 {len(changed_files)}개 파일에 대한 작업 기록을 남겼습니다."
        )
    relevant_files = _explicit_relevant_files(memory_state)
    if relevant_files:
        summary["relevant_files"] = relevant_files[:5]
    recent_events = _recent_event_lines(memory_state)
    if recent_events:
        summary["recent_events"] = recent_events[:5]
    verification = _verification_lines(memory_state)
    if verification:
        summary["verification"] = verification[-3:]
    freshness = _verification_freshness(memory_state)
    if freshness:
        _set_summary_value(summary, "verification_freshness", freshness)
    risks = [risk.text for risk in memory_state.risks if risk.text]
    if risks:
        summary["warnings"] = risks[:5]
    return summary


def _merge_memory_state_summary(summary: WorkMemorySummary, memory_state: MemoryState) -> None:
    if memory_state.active_intent is not None:
        summary["active_intent"] = memory_state.active_intent.text
    if memory_state.next_action is not None:
        summary["first_next_action"] = memory_state.next_action.text
        summary["concrete_next_steps"] = [memory_state.next_action.text]
    relevant_files = _explicit_relevant_files(memory_state)
    if relevant_files:
        summary["relevant_files"] = relevant_files[:5]
    verification = _verification_lines(memory_state)
    if verification:
        summary["verification"] = verification[-3:]
    freshness = _verification_freshness(memory_state)
    if freshness:
        _set_summary_value(summary, "verification_freshness", freshness)


def _memory_changed_files(memory_state: MemoryState) -> list[str]:
    paths: list[str] = []
    for event in memory_state.observed_context:
        if event.path and event.path not in paths:
            paths.append(event.path)
    for entry in memory_state.relevant_files:
        if entry.path and entry.path not in paths:
            paths.append(entry.path)
    return paths


def _agent_active_intent(memory_state: MemoryState) -> str:
    if memory_state.decisions:
        return memory_state.decisions[-1].text
    paths = _memory_changed_files(memory_state)
    if paths:
        latest = ", ".join(paths[:3])
        return f"최근 작업 파일을 이어서 정리하는 중입니다: {latest}"
    if memory_state.verification:
        return "최근 검증 결과를 바탕으로 작업 상태를 이어받는 중입니다."
    if memory_state.risks:
        return f"최근 경고를 확인하는 중입니다: {_latest_risk_text(memory_state)}"
    return ""


def _agent_next_action(memory_state: MemoryState) -> str:
    if memory_state.risks:
        return f"다음에 할 일: {_latest_risk_text(memory_state)}"
    for verification in reversed(memory_state.verification):
        if verification.command and (verification.stale or verification.scope_unknown):
            command = _dedupe_stale_labels(verification.command.partition(" -> ")[0].strip())
            return f"최신 상태 확인이 필요합니다. 다시 실행하세요: {command}"
    paths = _memory_changed_files(memory_state)
    if paths:
        latest = ", ".join(paths[:3])
        return f"{latest} 변경 내용을 확인하고 vib guard로 안전 상태를 점검하세요."
    if memory_state.verification:
        return "마지막 확인 결과를 검토하고 다음 수정 범위를 정하세요."
    return ""


def _agent_can_replace_next_action(field: MemoryTextField | None) -> bool:
    if field is None:
        return True
    return (
        field.proposed
        and field.source == "system"
        and field.text == "경고 내용을 먼저 확인하고 필요한 파일만 수정하거나 복구하세요."
    )


def _latest_risk_text(memory_state: MemoryState) -> str:
    for risk in reversed(memory_state.risks):
        if risk.text:
            return risk.text
    return "경고 내용을 확인하고 필요한 파일만 수정하거나 복구하세요."


def _explicit_relevant_files(memory_state: MemoryState) -> list[RelevantFileEntry]:
    return [
        {"path": entry.path, "why": entry.why}
        for entry in memory_state.relevant_files
        if entry.source == "explicit" and entry.path
    ]


def _recent_event_lines(memory_state: MemoryState) -> list[str]:
    lines: list[str] = []
    for event in memory_state.observed_context:
        path = event.path or "(unknown)"
        summary = event.summary or "(no details)"
        line = f"{event.kind}: {path} — {summary}"
        if line not in lines:
            lines.append(line)
    return lines


def _verification_lines(memory_state: MemoryState) -> list[str]:
    lines: list[str] = []
    for verification in memory_state.verification:
        line = verification.command
        if verification.result:
            line = f"{line} -> {verification.result}"
        line = _dedupe_stale_labels(line)
        if verification.stale and "(stale" not in line:
            reason = "scope unknown" if verification.scope_unknown else "stale"
            line = f"{line} (stale: {reason})"
        lines.append(line)
    return lines


def _verification_freshness(memory_state: MemoryState) -> str | None:
    return _assess_memory_freshness()(memory_state).verification_freshness or None


def _assess_memory_freshness() -> _AssessMemoryFreshness:
    module = import_module("vibelign.core.memory.freshness")
    return cast(_AssessMemoryFreshness, getattr(module, "assess_memory_freshness"))


def _set_summary_value(summary: WorkMemorySummary, key: str, value: object) -> None:
    cast(dict[str, object], cast(object, summary))[key] = value


def _dedupe_stale_labels(line: str) -> str:
    marker = " (stale: scope unknown)"
    while line.count(marker) > 1:
        line = line.replace(marker + marker, marker)
    return line


def _verification_key(value: str) -> str:
    command, _, _result = value.partition(" -> ")
    if command.startswith("uv run python -m py_compile"):
        return "uv run python -m py_compile"
    return command.strip() or value.strip()


def _migrate_legacy_state(
    state: WorkMemoryState,
    *,
    unknown_fields: dict[str, object] | None = None,
) -> MemoryState:
    updated_at = state.get("updated_at", "")
    decisions = [
        MemoryTextField(text=item, last_updated=updated_at, source="explicit")
        for item in state.get("decisions", [])
    ]
    active_intent = (
        MemoryTextField(
            text=decisions[-1].text,
            last_updated=decisions[-1].last_updated,
            source="explicit",
            proposed=True,
        )
        if decisions
        else None
    )
    return MemoryState(
        active_intent=active_intent,
        decisions=decisions,
        relevant_files=_migrate_relevant_files(state),
        verification=_migrate_verification(state),
        risks=_migrate_warnings(state),
        next_action=_migrate_next_action(state),
        observed_context=_migrate_observed_context(state),
        unknown_fields=unknown_fields or {},
    )


def _migrate_relevant_files(state: WorkMemoryState) -> list[MemoryRelevantFile]:
    updated_at = state.get("updated_at", "")
    migrated: list[MemoryRelevantFile] = []
    for entry in state.get("relevant_files", []):
        source = "explicit" if entry.get("source") == "explicit" else "observed"
        migrated.append(
            MemoryRelevantFile(
                path=entry.get("path", ""),
                why=entry.get("why", "Relevant to recent work."),
                source=source,
                last_updated=updated_at,
            )
        )
    return migrated


def _migrate_verification(state: WorkMemoryState) -> list[MemoryVerification]:
    updated_at = state.get("verification_updated_at") or state.get("updated_at", "")
    return [
        MemoryVerification(
            command=item,
            last_updated=updated_at,
            stale=True,
            scope_unknown=True,
        )
        for item in state.get("verification", [])
    ]


def _migrate_warnings(state: WorkMemoryState) -> list[MemoryTextField]:
    risks: list[MemoryTextField] = []
    for warning in state.get("warnings", []):
        message = warning.get("message", "")
        path = warning.get("path", "")
        text = f"{path} — {message}" if path else message
        if text:
            risks.append(
                MemoryTextField(
                    text=text,
                    last_updated=warning.get("time", ""),
                    source="observed",
                    stale=True,
                )
            )
    return risks


def _migrate_next_action(state: WorkMemoryState) -> MemoryTextField | None:
    text = state.get("next_action", "")
    if not text:
        return None
    return MemoryTextField(
        text=text,
        last_updated=state.get("updated_at", ""),
        source="explicit",
    )


def _migrate_observed_context(state: WorkMemoryState) -> list[MemoryObservedContext]:
    contexts: list[MemoryObservedContext] = []
    for event in state.get("recent_events", []):
        contexts.append(
            MemoryObservedContext(
                kind=event.get("kind", "event") or "event",
                summary=event.get("message", "") or "(no details)",
                path=event.get("path", ""),
                timestamp=event.get("time", ""),
            )
        )
    return contexts
# === ANCHOR: MEMORY_STORE_END ===
