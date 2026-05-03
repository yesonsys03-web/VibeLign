# === ANCHOR: WORK_MEMORY_START ===
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, cast


SCHEMA_VERSION = 1
MAX_RECENT_EVENTS = 20
MAX_RELEVANT_FILES = 10
MAX_WARNINGS = 10
MAX_DECISIONS = 5
MAX_VERIFICATION = 3
MAX_TEXT_LENGTH = 400
MAX_RECENT_EVENTS_SUMMARY = 5
MAX_RELEVANT_FILES_SUMMARY = 5
MAX_WARNINGS_SUMMARY = 5
MAX_VERIFICATION_SUMMARY = 3
WORK_MEMORY_EXCLUDED_DIRS = {
    ".omc",
    ".vibelign",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".pnpm-store",
    "__pycache__",
    "coverage",
    "out",
    "bin",
    "obj",
}
WORK_MEMORY_EXCLUDED_DIR_SUFFIXES = (".egg-info",)
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:/")


# === ANCHOR: WORK_MEMORY_WORKMEMORYEVENT_START ===
class WorkMemoryEvent(TypedDict, total=False):
    time: str
    kind: str
    path: str
    message: str
    action: str
# === ANCHOR: WORK_MEMORY_WORKMEMORYEVENT_END ===


# === ANCHOR: WORK_MEMORY_RELEVANTFILEENTRY_START ===
class RelevantFileEntry(TypedDict, total=False):
    path: str
    why: str
    # v2.0.37: "explicit" (transfer_set_relevant) vs "watch" (mcp_dispatch capture).
    # 핸드오프 Relevant files 섹션은 "explicit" 만 노출. legacy entry 는 "watch" 로 fallback.
    source: str
# === ANCHOR: WORK_MEMORY_RELEVANTFILEENTRY_END ===


# === ANCHOR: WORK_MEMORY_WORKMEMORYSTATE_START ===
class WorkMemoryState(TypedDict):
    schema_version: int
    updated_at: str
    recent_events: list[WorkMemoryEvent]
    relevant_files: list[RelevantFileEntry]
    warnings: list[WorkMemoryEvent]
    decisions: list[str]
    verification: list[str]
    next_action: str
    # v2.0.37: verification 만 갱신되는 별도 timestamp.
    # 핸드오프 freshness 라벨 계산용 — updated_at 은 모든 mutation 에 갱신되므로 부적절.
    verification_updated_at: str
# === ANCHOR: WORK_MEMORY_WORKMEMORYSTATE_END ===


# === ANCHOR: WORK_MEMORY_WORKMEMORYSUMMARY_START ===
class WorkMemorySummary(TypedDict, total=False):
    active_intent: str
    session_summary: str
    first_next_action: str
    concrete_next_steps: list[str]
    unfinished_work: str
    changed_files: list[str]
    change_details: list[str]
    relevant_files: list[RelevantFileEntry]
    recent_events: list[str]
    warnings: list[str]
    verification: list[str]
    state_references: list[str]
# === ANCHOR: WORK_MEMORY_WORKMEMORYSUMMARY_END ===


# === ANCHOR: WORK_MEMORY__UTC_NOW_START ===
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# === ANCHOR: WORK_MEMORY__UTC_NOW_END ===


# === ANCHOR: WORK_MEMORY__TRUNCATE_TEXT_START ===
def _truncate_text(value: object, limit: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
# === ANCHOR: WORK_MEMORY__TRUNCATE_TEXT_END ===


def _warn_work_memory_failure(operation: str, path: Path, error: Exception) -> None:
    print(f"[WARN] work memory {operation} failed for {path}: {error}", file=sys.stderr)


# === ANCHOR: WORK_MEMORY__SAFE_RELATIVE_PATH_START ===
def _safe_relative_path(value: object) -> str:
    text = _truncate_text(value, 200).replace("\\", "/")
    if not text:
        return ""
    parts = [part for part in text.split("/") if part]
    if text.startswith("/") or _WINDOWS_DRIVE_RE.match(text) or ".." in parts:
        return ""
    if _is_excluded_memory_path(parts):
        return ""
    return text
# === ANCHOR: WORK_MEMORY__SAFE_RELATIVE_PATH_END ===


def _is_excluded_memory_path(parts: list[str]) -> bool:
    for part in parts:
        normalized = part.lower()
        if normalized in WORK_MEMORY_EXCLUDED_DIRS:
            return True
        if any(normalized.endswith(suffix) for suffix in WORK_MEMORY_EXCLUDED_DIR_SUFFIXES):
            return True
    return False


# === ANCHOR: WORK_MEMORY__NORMALIZE_EVENT_START ===
def _normalize_event(raw: object) -> WorkMemoryEvent | None:
    if not isinstance(raw, dict):
        return None
    payload = cast(dict[object, object], raw)
    event: WorkMemoryEvent = {
        "time": _truncate_text(payload.get("time"), 64),
        "kind": _truncate_text(payload.get("kind"), 32),
        "path": _safe_relative_path(payload.get("path")),
        "message": _truncate_text(payload.get("message")),
        "action": _truncate_text(payload.get("action")),
    }
    if payload.get("path") and not event["path"]:
        return None
    if not any(event.values()):
        return None
    return event
# === ANCHOR: WORK_MEMORY__NORMALIZE_EVENT_END ===


# === ANCHOR: WORK_MEMORY__NORMALIZE_RELEVANT_FILE_START ===
def _normalize_relevant_file(raw: object) -> RelevantFileEntry | None:
    if isinstance(raw, str):
        path = _safe_relative_path(raw)
        return (
            {"path": path, "why": "Recently touched by watch.", "source": "watch"}
            if path
            else None
        )
    if not isinstance(raw, dict):
        return None
    payload = cast(dict[object, object], raw)
    path = _safe_relative_path(payload.get("path"))
    why = _truncate_text(payload.get("why"))
    if not path:
        return None
    raw_source = payload.get("source")
    source = raw_source if raw_source in ("explicit", "watch") else "watch"
    return {
        "path": path,
        "why": why or "Relevant to recent work.",
        "source": cast(str, source),
    }
# === ANCHOR: WORK_MEMORY__NORMALIZE_RELEVANT_FILE_END ===


# === ANCHOR: WORK_MEMORY__NORMALIZE_STRING_LIST_START ===
def _normalize_string_list(raw: object, limit: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    items: list[str] = []
    for value in cast(list[object], raw):
        text = _truncate_text(value)
        if text:
            items.append(text)
    return items[:limit]
# === ANCHOR: WORK_MEMORY__NORMALIZE_STRING_LIST_END ===


# === ANCHOR: WORK_MEMORY__WARNING_SUMMARY_LINE_START ===
def _warning_summary_line(warning: WorkMemoryEvent) -> str:
    path = warning.get("path") or "(unknown)"
    message = warning.get("message") or "(warning)"
    action = warning.get("action") or ""
    line = f"{path} — {message}"
    return f"{line} → {action}" if action else line
# === ANCHOR: WORK_MEMORY__WARNING_SUMMARY_LINE_END ===


# === ANCHOR: WORK_MEMORY__PRUNE_EVENTS_START ===
def _prune_events(events: list[WorkMemoryEvent], limit: int) -> list[WorkMemoryEvent]:
    return events[-limit:]
# === ANCHOR: WORK_MEMORY__PRUNE_EVENTS_END ===


# === ANCHOR: WORK_MEMORY__PRUNE_RELEVANT_FILES_START ===
def _prune_relevant_files(entries: list[RelevantFileEntry]) -> list[RelevantFileEntry]:
    deduped: list[RelevantFileEntry] = []
    seen: set[str] = set()
    for entry in reversed(entries):
        path = entry.get("path", "")
        if not path or path in seen:
            continue
        seen.add(path)
        source_raw = entry.get("source", "watch")
        source = source_raw if source_raw in ("explicit", "watch") else "watch"
        deduped.append(
            {
                "path": _truncate_text(path, 200),
                "why": _truncate_text(entry.get("why", "")),
                "source": source,
            }
        )
        if len(deduped) >= MAX_RELEVANT_FILES:
            break
    deduped.reverse()
    return deduped
# === ANCHOR: WORK_MEMORY__PRUNE_RELEVANT_FILES_END ===


# === ANCHOR: WORK_MEMORY_DEFAULT_WORK_MEMORY_STATE_START ===
def default_work_memory_state() -> WorkMemoryState:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": "",
        "recent_events": [],
        "relevant_files": [],
        "warnings": [],
        "decisions": [],
        "verification": [],
        "next_action": "",
        "verification_updated_at": "",
    }
# === ANCHOR: WORK_MEMORY_DEFAULT_WORK_MEMORY_STATE_END ===


# === ANCHOR: WORK_MEMORY_PRUNE_WORK_MEMORY_STATE_START ===
def prune_work_memory_state(state: WorkMemoryState) -> WorkMemoryState:
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at"] = _truncate_text(state.get("updated_at"), 64)
    state["recent_events"] = _prune_events(state.get("recent_events", []), MAX_RECENT_EVENTS)
    state["relevant_files"] = _prune_relevant_files(state.get("relevant_files", []))
    state["warnings"] = _prune_events(state.get("warnings", []), MAX_WARNINGS)
    state["decisions"] = _normalize_string_list(state.get("decisions"), MAX_DECISIONS)
    state["verification"] = _normalize_string_list(
        state.get("verification"), MAX_VERIFICATION
    )
    state["next_action"] = _truncate_text(state.get("next_action"))
    return state
# === ANCHOR: WORK_MEMORY_PRUNE_WORK_MEMORY_STATE_END ===


# === ANCHOR: WORK_MEMORY_LOAD_WORK_MEMORY_START ===
def load_work_memory(path: Path) -> WorkMemoryState:
    if not path.exists():
        return default_work_memory_state()
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:
        _warn_work_memory_failure("load", path, exc)
        return default_work_memory_state()
    if not isinstance(raw, dict):
        return default_work_memory_state()
    payload = cast(dict[object, object], raw)
    state = default_work_memory_state()
    state["updated_at"] = _truncate_text(payload.get("updated_at"), 64)
    recent_events_raw = payload.get("recent_events", [])
    if isinstance(recent_events_raw, list):
        for item in cast(list[object], recent_events_raw):
            normalized = _normalize_event(item)
            if normalized is not None:
                state["recent_events"].append(normalized)
    relevant_files_raw = payload.get("relevant_files", [])
    if isinstance(relevant_files_raw, list):
        for item in cast(list[object], relevant_files_raw):
            normalized_file = _normalize_relevant_file(item)
            if normalized_file is not None:
                state["relevant_files"].append(normalized_file)
    warnings_raw = payload.get("warnings", [])
    if isinstance(warnings_raw, list):
        for item in cast(list[object], warnings_raw):
            normalized_warning = _normalize_event(item)
            if normalized_warning is not None:
                state["warnings"].append(normalized_warning)
    state["decisions"] = _normalize_string_list(payload.get("decisions"), MAX_DECISIONS)
    state["verification"] = _normalize_string_list(
        payload.get("verification"), MAX_VERIFICATION
    )
    state["next_action"] = _truncate_text(payload.get("next_action"))
    state["verification_updated_at"] = _truncate_text(
        payload.get("verification_updated_at"), 64
    )
    return prune_work_memory_state(state)
# === ANCHOR: WORK_MEMORY_LOAD_WORK_MEMORY_END ===


# === ANCHOR: WORK_MEMORY_SAVE_WORK_MEMORY_START ===
def save_work_memory(path: Path, state: WorkMemoryState) -> None:
    pruned = prune_work_memory_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    _ = tmp_path.write_text(
        json.dumps(pruned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _ = tmp_path.replace(path)
# === ANCHOR: WORK_MEMORY_SAVE_WORK_MEMORY_END ===


# === ANCHOR: WORK_MEMORY__APPEND_RELEVANT_FILE_START ===
def _append_relevant_file(
    entries: list[RelevantFileEntry], path: str, why: str, source: str = "watch",
# === ANCHOR: WORK_MEMORY__APPEND_RELEVANT_FILE_END ===
) -> list[RelevantFileEntry]:
    rel_path = _safe_relative_path(path)
    rel_why = _truncate_text(why)
    if not rel_path:
        return entries
    src = source if source in ("explicit", "watch") else "watch"
    updated = [entry for entry in entries if entry.get("path") != rel_path]
    updated.append(
        {
            "path": rel_path,
            "why": rel_why or "Relevant to recent work.",
            "source": src,
        }
    )
    return _prune_relevant_files(updated)


# === ANCHOR: WORK_MEMORY_ADD_RELEVANT_FILE_START ===
def add_relevant_file(
    path: Path, file_path: str, why: str, source: str = "watch",
) -> None:
    """Public 진입점 — relevant_files 에 entry 추가 (dedup, 절대/제외경로 차단).

    Why: 기존 _append_relevant_file 은 record_event 내부 헬퍼였음.
         MCP 도구·hook 등 외부 호출자가 직접 부를 public API.
    """
    state = load_work_memory(path)
    state["relevant_files"] = _append_relevant_file(
        state["relevant_files"], file_path, why, source=source,
    )
    state["updated_at"] = _utc_now()
    save_work_memory(path, state)
# === ANCHOR: WORK_MEMORY_ADD_RELEVANT_FILE_END ===


# === ANCHOR: WORK_MEMORY_RECORD_EVENT_START ===
def record_event(
    path: Path,
    *,
    kind: str,
    rel_path: str,
    message: str,
    action: str = "",
    relevant_reason: str = "",
# === ANCHOR: WORK_MEMORY_RECORD_EVENT_END ===
) -> None:
    safe_rel_path = _safe_relative_path(rel_path)
    if not safe_rel_path:
        return
    try:
        state = load_work_memory(path)
        event: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": _truncate_text(kind, 32),
            "path": safe_rel_path,
            "message": _truncate_text(message),
            "action": _truncate_text(action),
        }
        state["recent_events"].append(event)
        state["relevant_files"] = _append_relevant_file(
            state["relevant_files"],
            safe_rel_path,
            relevant_reason or f"Recently {event['kind']} in watch.",
        )
        state["updated_at"] = event["time"]
        save_work_memory(path, state)
    except Exception as exc:
        _warn_work_memory_failure("record_event", path, exc)
        return


# === ANCHOR: WORK_MEMORY_RECORD_WARNING_START ===
def record_warning(
    path: Path,
    *,
    rel_path: str,
    message: str,
    action: str = "",
# === ANCHOR: WORK_MEMORY_RECORD_WARNING_END ===
) -> None:
    safe_rel_path = _safe_relative_path(rel_path)
    if not safe_rel_path:
        return
    try:
        state = load_work_memory(path)
        warning: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": "warning",
            "path": safe_rel_path,
            "message": _truncate_text(message),
            "action": _truncate_text(action),
        }
        state["warnings"].append(warning)
        state["recent_events"].append(warning)
        state["relevant_files"] = _append_relevant_file(
            state["relevant_files"],
            safe_rel_path,
            "Watch raised a warning for this file.",
        )
        state["updated_at"] = warning["time"]
        save_work_memory(path, state)
    except Exception as exc:
        _warn_work_memory_failure("record_warning", path, exc)
        return


# === ANCHOR: WORK_MEMORY_RECORD_COMMIT_START ===
def record_commit(path: Path, sha: str, message: str) -> None:
    """recent_events 에 kind="commit" entry 추가. decisions[] 는 건드리지 않음.

    Why: commit 메시지는 사실(fact) 이지 의사결정(decision) 이 아님.
         decisions[-1] → active_intent 매핑이 release commit 으로 오염되지 않도록
         별도 bucket (recent_events) 으로 격리한다. multi-line / 한글 / 이모지 안전.
    """
    text = _truncate_text(message)
    if not text:
        return
    short = (sha or "")[:12] or "unknown"
    try:
        state = load_work_memory(path)
        event: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": "commit",
            "path": f"git/{short}",
            "message": text,
            "action": "",
        }
        state["recent_events"].append(event)
        state["updated_at"] = event["time"]
        save_work_memory(path, state)
    except Exception as exc:
        _warn_work_memory_failure("record_commit", path, exc)
        return
# === ANCHOR: WORK_MEMORY_RECORD_COMMIT_END ===


# === ANCHOR: WORK_MEMORY_RECORD_CHECKPOINT_START ===
def record_checkpoint(path: Path, message: str) -> None:
    """recent_events 에 kind="checkpoint" entry 추가. decisions/relevant_files 는 건드리지 않음.

    Why: checkpoint_create 는 파일 변경이 아니라 state-save fact 이므로 record_event 의
         파일 경로/relevant_files 경로와 분리한다.
    """
    text = _truncate_text(message)
    if not text:
        return
    try:
        state = load_work_memory(path)
        event: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": "checkpoint",
            "path": "checkpoint",
            "message": text,
            "action": "",
        }
        state["recent_events"].append(event)
        state["updated_at"] = event["time"]
        save_work_memory(path, state)
    except Exception as exc:
        _warn_work_memory_failure("record_checkpoint", path, exc)
        return
# === ANCHOR: WORK_MEMORY_RECORD_CHECKPOINT_END ===


# === ANCHOR: WORK_MEMORY_ADD_VERIFICATION_START ===
def add_verification(path: Path, message: str) -> None:
    state = load_work_memory(path)
    text = _truncate_text(message)
    if not text:
        return
    key = _verification_key(text)
    state["verification"] = [
        item for item in state["verification"] if _verification_key(item) != key
    ] + [text]
    now = _utc_now()
    state["updated_at"] = now
    state["verification_updated_at"] = now
    save_work_memory(path, state)
# === ANCHOR: WORK_MEMORY_ADD_VERIFICATION_END ===


def _verification_key(value: str) -> str:
    command, _, _result = value.partition(" -> ")
    if command.startswith("uv run python -m py_compile"):
        return "uv run python -m py_compile"
    return command.strip() or value.strip()


# === ANCHOR: WORK_MEMORY_ADD_DECISION_START ===
def add_decision(path: Path, message: str) -> None:
    state = load_work_memory(path)
    text = _truncate_text(message)
    if not text:
        return
    state["decisions"] = [item for item in state["decisions"] if item != text] + [text]
    state["updated_at"] = _utc_now()
    save_work_memory(path, state)
# === ANCHOR: WORK_MEMORY_ADD_DECISION_END ===


def set_next_action(path: Path, message: str) -> None:
    state = load_work_memory(path)
    text = _truncate_text(message)
    if not text:
        return
    state["next_action"] = text
    state["updated_at"] = _utc_now()
    save_work_memory(path, state)


# === ANCHOR: WORK_MEMORY__IS_SYNTHETIC_EVENT_PATH_START ===
def _is_synthetic_event_path(rel_path: str) -> bool:
    """recent_events 의 sentinel path 여부 (record_commit/record_checkpoint 출처).

    Why: 이 path 들은 실제 수정 파일이 아니라 synthetic event marker.
         changed_files 사용자 출력에 들어가면 진짜 파일 경로를 evict 하므로
         aggregator 에서 거른다. (recent_events / change_details 에는 그대로 둔다.)
    """
    return rel_path == "checkpoint" or rel_path.startswith("git/")
# === ANCHOR: WORK_MEMORY__IS_SYNTHETIC_EVENT_PATH_END ===


# === ANCHOR: WORK_MEMORY_BUILD_TRANSFER_SUMMARY_START ===
def build_transfer_summary(path: Path) -> WorkMemorySummary | None:
    state = load_work_memory(path)
    has_content = any(
        [
            state["recent_events"],
            state["relevant_files"],
            state["warnings"],
            state["decisions"],
            state["verification"],
        ]
    )
    if not has_content:
        return None

    changed_files: list[str] = []
    for event in state["recent_events"]:
        rel_path = event.get("path", "")
        if not rel_path or _is_synthetic_event_path(rel_path):
            continue
        if rel_path not in changed_files:
            changed_files.append(rel_path)
    for entry in state["relevant_files"]:
        rel_path = entry.get("path", "")
        if rel_path not in changed_files:
            changed_files.append(rel_path)

    warning_lines: list[str] = []
    for warning in reversed(state["warnings"]):
        line = _warning_summary_line(warning)
        if line not in warning_lines:
            warning_lines.append(line)
        if len(warning_lines) >= MAX_WARNINGS_SUMMARY:
            break
    warning_lines.reverse()
    recent_event_lines: list[str] = []
    change_detail_lines: list[str] = []
    for event in reversed(state["recent_events"]):
        line = f"{event.get('kind') or 'event'}: {event.get('path') or '(unknown)'} — {event.get('message') or '(no details)'}"
        if line not in recent_event_lines:
            recent_event_lines.append(line)
        if event.get("kind") != "warning":
            detail = f"{event.get('path') or '(unknown)'} — {event.get('kind') or 'event'}: {event.get('message') or '(no details)'}"
            action = event.get("action") or ""
            if action:
                detail += f" → {action}"
            if detail not in change_detail_lines:
                change_detail_lines.append(detail)
        if len(recent_event_lines) >= MAX_RECENT_EVENTS_SUMMARY:
            break
    recent_event_lines.reverse()
    change_detail_lines.reverse()
    # v2.0.37: 핸드오프 Relevant files 섹션은 명시 등록 (transfer_set_relevant) 만 노출.
    # watch 자동 캡처는 Supporting watch context (recent_events) 로 이미 흐르므로 중복 제거.
    explicit_relevant = [
        entry for entry in state["relevant_files"] if entry.get("source") == "explicit"
    ]
    relevant_files = explicit_relevant[-MAX_RELEVANT_FILES_SUMMARY:]
    latest_action = next(
        (
            event.get("action", "")
            for event in reversed(state["warnings"] + state["recent_events"])
            if event.get("action")
        ),
        "",
    )

    latest_paths = ", ".join(f"`{item}`" for item in changed_files[:3])
    kind_counts: dict[str, int] = {}
    for event in state["recent_events"]:
        kind = event.get("kind", "event") or "event"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    kind_summary = ", ".join(
        f"{kind} {count}건" for kind, count in sorted(kind_counts.items())
    )
    summary_parts: list[str] = []
    if latest_paths:
        summary_parts.append(
            f"현재 세션에서 {latest_paths} 등 {len(changed_files)}개 파일에 대한 작업 기록을 남겼습니다"
        )
    else:
        summary_parts.append("현재 세션에서 작업 기억을 갱신했습니다")
    if kind_summary:
        summary_parts.append(f"기록된 이벤트는 {kind_summary}입니다")
    if warning_lines:
        summary_parts.append(
            f"경고 {len(warning_lines)}건이 있어 Warnings / risks를 확인해야 합니다"
        )
    session_summary = ". ".join(summary_parts).strip() + "."

    summary: WorkMemorySummary = {
        "session_summary": _truncate_text(session_summary),
        "changed_files": changed_files[:MAX_RELEVANT_FILES],
        "change_details": change_detail_lines[:MAX_RECENT_EVENTS_SUMMARY],
        "relevant_files": relevant_files,
        "recent_events": recent_event_lines,
        "warnings": warning_lines,
        "verification": state["verification"][-MAX_VERIFICATION_SUMMARY:],
        "state_references": [".vibelign/work_memory.json"],
    }
    next_action = state.get("next_action") or latest_action
    if next_action:
        summary["first_next_action"] = _truncate_text(next_action)
        summary["concrete_next_steps"] = [_truncate_text(next_action)]
    if state["decisions"]:
        summary["active_intent"] = state["decisions"][-1]
    if warning_lines:
        summary["unfinished_work"] = _truncate_text("; ".join(warning_lines[:2]))
    return summary
# === ANCHOR: WORK_MEMORY_BUILD_TRANSFER_SUMMARY_END ===
# === ANCHOR: WORK_MEMORY_END ===
