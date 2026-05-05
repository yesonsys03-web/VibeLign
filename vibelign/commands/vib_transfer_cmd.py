# === ANCHOR: VIB_TRANSFER_CMD_START ===
# vibelign/commands/vib_transfer_cmd.py

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from typing import Protocol, TypedDict, cast

from vibelign.commands import transfer_git_context
from vibelign.core.checkpoint_engine.router import list_checkpoints, friendly_time
from vibelign.core.project_root import resolve_project_root
from vibelign.core.structure_policy import (
    HANDOFF_KEY_FILE_NAMES,
    HANDOFF_SKIP_EXTENSIONS,
    TRANSFER_TREE_IGNORED_DIRS,
)
from vibelign.terminal_render import (
    clack_intro,
    clack_step,
    clack_success,
    clack_info,
    clack_outro,
)

# PROJECT_CONTEXT.md 에 추가되는 마커 (중복 생성 방지용)
_TRANSFER_MARKER = "<!-- VibeLign Transfer Context -->"
_HANDOFF_CHANGE_DISPLAY_LIMIT = 30

_SKIP_DIRS = set(TRANSFER_TREE_IGNORED_DIRS)
_SKIP_EXTS = set(HANDOFF_SKIP_EXTENSIONS)
_KEY_FILE_NAMES = set(HANDOFF_KEY_FILE_NAMES)


class CheckpointSummary(TypedDict):
    time: str
    message: str
    id: str


class DecisionContext(TypedDict):
    tried: str
    blocked_by: str
    switched_to: str


class HandoffData(TypedDict, total=False):
    generated_at: str
    source: str
    quality: str
    active_intent: str | None
    session_summary: str | None
    changed_files: list[str]
    change_details: list[str]
    completed_work: str | None
    unfinished_work: str | None
    first_next_action: str | None
    concrete_next_steps: list[str]
    decision_context: DecisionContext | None
    latest_checkpoint: str | None
    latest_checkpoint_note: str | None
    recent_git_context: list[str]
    relevant_files: list[dict[str, str]]
    recent_events: list[str]
    warnings: list[str]
    verification: list[str]
    verification_to_persist: list[str]
    decision_notes: list[str]
    state_references: list[str]
    changed_file_count: int
    first_next_action_confirmed: bool
    # v2.0.37: top-of-handoff dense block + section restructure
    working_tree_details: list[str]
    supporting_watch_context: list[str]
    done_when: str | None
    verification_freshness: str | None


class TransferArgs(Protocol):
    compact: bool
    full: bool
    handoff: bool
    no_prompt: bool
    print_mode: bool
    dry_run: bool
    out: str | None
    session_summary: str | None
    first_next_action: str | None
    verification: list[str] | None
    decision: list[str] | None
    ai: bool


_TIMESTAMP_PATTERN = re.compile(r"\s*\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)\s*$")


def _clean_checkpoint_message(msg: str) -> str:
    for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
        if msg.startswith(prefix):
            msg = msg[len(prefix) :]
            break
    msg = _TIMESTAMP_PATTERN.sub("", msg).strip()
    if msg.startswith("{") or len(msg) > 200:
        return "(자동 저장)"
    return msg or "(메시지 없음)"


def _read_json_object(path: Path) -> dict[str, object] | None:
    try:
        raw_obj = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None
    if not isinstance(raw_obj, dict):
        return None
    raw = cast(dict[object, object], raw_obj)
    normalized: dict[str, object] = {}
    for key, value in raw.items():
        normalized[str(key)] = value
    return normalized


def _normalize_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    normalized: dict[str, object] = {}
    for key, item in raw.items():
        normalized[str(key)] = item
    return normalized


def _handoff_text(value: object, default: str = "(not provided)") -> str:
    return value if isinstance(value, str) and value else default


def _handoff_markdown_text(value: str) -> str:
    return " ".join(value.split()).replace("`", "'")


def _handoff_files(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    raw_items = cast(list[object], value)
    items: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            items.append(item)
    return items


def _handoff_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in cast(list[object], value):
        if isinstance(item, str) and item:
            items.append(_handoff_markdown_text(item))
    return items


def _handoff_relevant_files(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    entries: list[dict[str, str]] = []
    for item in cast(list[object], value):
        normalized = _normalize_object_dict(item)
        if normalized is None:
            continue
        path = normalized.get("path")
        why = normalized.get("why")
        if isinstance(path, str) and path:
            entries.append(
                {
                    "path": _handoff_markdown_text(path),
                    "why": _handoff_markdown_text(why)
                    if isinstance(why, str) and why
                    else "Relevant to recent work.",
                }
            )
    return entries


def _handoff_decision_context(value: object) -> DecisionContext | None:
    normalized = _normalize_object_dict(value)
    if normalized is None:
        return None
    return {
        "tried": _handoff_text(normalized.get("tried")),
        "blocked_by": _handoff_text(normalized.get("blocked_by")),
        "switched_to": _handoff_text(normalized.get("switched_to")),
    }


def _arg_bool(args: object, name: str) -> bool:
    value = getattr(args, name, False)
    return value if isinstance(value, bool) else False


def _arg_text(args: object, name: str) -> str | None:
    value = getattr(args, name, None)
    return value if isinstance(value, str) else None


def _arg_text_list(args: object, name: str) -> list[str]:
    value = getattr(args, name, None)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _get_changed_files(root: Path) -> list[str]:
    return transfer_git_context.get_changed_files(root)


def _get_working_tree_change_details(root: Path) -> list[str]:
    return transfer_git_context.get_working_tree_change_details(root)


def _get_working_tree_summary(root: Path) -> transfer_git_context.WorkingTreeSummary:
    return transfer_git_context.get_working_tree_summary(root)


def _detect_project_name(root: Path) -> str:
    """프로젝트 이름 감지."""
    # pyproject.toml에서 name 읽기
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'name\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1)

    # package.json에서 name 읽기
    pkg_json = root / "package.json"
    if pkg_json.exists():
        data = _read_json_object(pkg_json)
        name = data.get("name") if data is not None else None
        if isinstance(name, str):
            return name

    # 폴더 이름 사용
    return root.name


def _detect_tech_stack(root: Path) -> list[str]:
    """기술 스택 자동 감지."""
    stack: list[str] = []
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        stack.append("Python")
    if (root / "package.json").exists():
        pkg = root / "package.json"
        text = pkg.read_text(encoding="utf-8", errors="ignore")
        if "react" in text.lower():
            stack.append("React")
        elif "vue" in text.lower():
            stack.append("Vue")
        elif "next" in text.lower():
            stack.append("Next.js")
        else:
            stack.append("Node.js")
    if (root / "go.mod").exists():
        stack.append("Go")
    if (root / "Cargo.toml").exists():
        stack.append("Rust")
    if (root / "pom.xml").exists() or (root / "build.gradle").exists():
        stack.append("Java")
    if not stack:
        stack.append("(자동 감지 실패 — 직접 입력 권장)")
    return stack


def _build_file_tree(root: Path, max_depth: int = 3) -> str:
    """파일 트리 생성 (핵심 파일만, 최대 깊이 제한)."""
    lines: list[str] = []

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        entries = [
            e
            for e in entries
            if e.name not in _SKIP_DIRS
            and e.suffix not in _SKIP_EXTS
            and not e.name.startswith(".")
        ]
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)
            else:
                # 핵심 파일 표시
                marker = "  ⭐" if entry.name in _KEY_FILE_NAMES else ""
                lines.append(f"{prefix}{connector}{entry.name}{marker}")

    lines.append(f"{root.name}/")
    _walk(root, "", 1)
    return "\n".join(lines)


def _get_recent_checkpoints(root: Path, n: int = 5) -> list[CheckpointSummary]:
    """최근 N개 체크포인트 가져오기."""
    try:
        checkpoints = list_checkpoints(root)
        recent = checkpoints[:n]  # 최신 순 (list_checkpoints는 이미 최신순)
        result: list[CheckpointSummary] = []
        for cp in recent:
            result.append(
                {
                    "time": friendly_time(cp.created_at),
                    "message": _clean_checkpoint_message(cp.message),
                    "id": cp.checkpoint_id,
                }
            )
        return result
    except Exception:
        return []


def get_recent_checkpoints(root: Path, n: int = 5) -> list[CheckpointSummary]:
    return _get_recent_checkpoints(root, n=n)


def _read_agents_md(root: Path) -> str:
    """AGENTS.md 핵심 내용 읽기 (Core Rules + Module boundaries까지, Two Modification Modes 전)."""
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        return "(AGENTS.md 없음 — `vib start` 실행 권장)"

    text = agents_path.read_text(encoding="utf-8", errors="ignore")

    # Core Rules부터 Two Modification Modes 직전까지 (중간의 ## Module boundaries 등 포함)
    m = re.search(
        r"## Core Rules\n(.*?)(?=\n## Two Modification Modes|\Z)",
        text,
        re.DOTALL,
    )
    if m:
        rules_text = m.group(1).strip()
        # 핸드오프 본문이 과도해지지 않도록 상한
        lines = rules_text.split("\n")[:40]
        return "\n".join(lines)

    # 없으면 앞 20줄만
    lines = text.split("\n")[:20]
    return "\n".join(lines)


def _detect_run_commands(root: Path) -> list[str]:
    """실행 방법 자동 감지."""
    commands: list[str] = []

    # Python
    if (root / "pyproject.toml").exists():
        commands.append("pip install -e .  # 개발 설치")
    elif (root / "requirements.txt").exists():
        commands.append("pip install -r requirements.txt")

    # Node
    if (root / "package.json").exists():
        pkg = root / "package.json"
        data = _read_json_object(pkg)
        scripts = data.get("scripts") if data is not None else None
        normalized_scripts = _normalize_object_dict(scripts)
        if normalized_scripts is not None:
            if "dev" in normalized_scripts:
                commands.append("npm run dev")
            elif "start" in normalized_scripts:
                commands.append("npm start")
        else:
            commands.append("npm install && npm start")

    if not commands:
        commands.append("(실행 방법을 직접 입력하세요)")

    return commands


def _estimate_tokens(text: str) -> int:
    """대략적인 토큰 수 추정 (4자 = 1 token)."""
    return len(text) // 4


def _build_handoff_block(data: HandoffData) -> str:
    """Session Handoff 블록 생성 (v2.0.37 재구성: top dense block + git/watch 분리)."""
    lines: list[str] = []
    lines.append("## Session Handoff")
    lines.append(
        "> ⚠️ This block is session-specific and time-sensitive. Read this first."
    )
    lines.append("")
    lines.append(f"Generated: {_handoff_text(data.get('generated_at'), '')}")
    lines.append(
        f"Handoff source: {_handoff_text(data.get('source'), 'file_fallback')}"
    )
    lines.append(
        f"Handoff quality: {_handoff_text(data.get('quality'), 'auto-drafted')}"
    )

    cp_ref = _handoff_text(data.get("latest_checkpoint"))
    cp_note = _handoff_text(data.get("latest_checkpoint_note"), "")
    if cp_note and cp_ref != "(not provided)":
        cp_ref = f"{cp_ref} ({cp_note})"
    lines.append(f"Latest checkpoint: {cp_ref}")
    lines.append("")

    # v2.0.37: 정적 patch rules 4줄 → 1줄 reference. 상세는 AGENTS.md / AI_DEV_SYSTEM_SINGLE_FILE.md.
    lines.append(
        "Patch rules: see AGENTS.md / AI_DEV_SYSTEM_SINGLE_FILE.md (intent/source/destination/behavior split, anchor-only edits)."
    )
    lines.append("")

    concrete_next_steps = _build_concrete_next_steps(data)

    # v2.0.37: 맨 위 dense 4 슬롯 — 다음 AI 가 30초 안에 작업 파일/상태/첫 행동/완료 조건 파악
    primary, status, next_action_line, done_when = _build_top_dense_slots(
        data, concrete_next_steps
    )
    lines.append(f"- **Primary work item**: {primary}")
    lines.append(f"- **Working tree truth**: {status}")
    lines.append(f"- **Next action**: {next_action_line}")
    if done_when:
        lines.append(f"- **Done when**: {done_when}")
    lines.append("")

    active_intent = _handoff_text(data.get("active_intent"), "") or _infer_active_intent(
        data
    )
    if active_intent:
        lines.append("### Active intent")
        lines.append(active_intent)
        lines.append("")

    unfinished = _handoff_text(data.get("unfinished_work"), "")
    lines.append("### Concrete next steps")
    if unfinished:
        lines.append(f"- 미완료: {unfinished}")
    for item in concrete_next_steps[:5]:
        lines.append(f"- {item}")
    lines.append("")

    # v2.0.37: git status 만 (Live working changes + Code change details 의 git 부분 통합)
    working_tree_details = _handoff_lines(data.get("working_tree_details"))
    lines.append("### Working tree truth")
    if working_tree_details:
        for item in working_tree_details[:_HANDOFF_CHANGE_DISPLAY_LIMIT]:
            lines.append(f"- {item}")
    else:
        lines.append("- (no uncommitted git-tracked changes)")
    lines.append("")

    # v2.0.37: work_memory recent_events 중 git status 에 없는 것만 (commit / past-watch 등)
    supporting = _handoff_lines(data.get("supporting_watch_context"))
    if supporting:
        lines.append("### Supporting watch context")
        lines.append("(work_memory recent_events; secondary signal — verify before acting)")
        for item in supporting[:_HANDOFF_CHANGE_DISPLAY_LIMIT]:
            lines.append(f"- {item}")
        lines.append("")

    verification = _handoff_lines(data.get("verification"))
    freshness = _handoff_text(data.get("verification_freshness"), "")
    freshness_label = f" [Freshness: {freshness}]" if freshness else ""
    lines.append(f"### Verification snapshot{freshness_label}")
    if verification:
        for item in verification[-3:]:
            lines.append(f"- {item}")
        if freshness == "stale":
            lines.append("- ⚠️ Required rerun before commit: working tree changed since last verification")
    else:
        lines.append(
            "- Not recorded in work memory. Rerun the relevant tests/build before committing."
        )
    lines.append("")

    relevant_files = _handoff_relevant_files(data.get("relevant_files"))
    if relevant_files:
        lines.append("### Relevant files")
        lines.append("(explicit picks via transfer_set_relevant; not auto-watch)")
        for entry in relevant_files[:5]:
            lines.append(f"- `{entry['path']}` — {entry['why']}")
        lines.append("")

    recent_git_context = _handoff_lines(data.get("recent_git_context"))
    if recent_git_context:
        lines.append("### Recent git context")
        for item in recent_git_context[:5]:
            lines.append(f"- {item}")
        lines.append("")

    changed = _working_tree_paths(data)
    changed_count = len(changed)
    lines.append("### 변경 파일")
    if changed:
        files_str = ", ".join(f"`{f}`" for f in changed[:5])
        total = changed_count
        if total > 5:
            files_str += f" … (+{total - 5})"
        lines.append(files_str)
    else:
        lines.append("(not provided)")
    lines.append("")

    warnings = _handoff_lines(data.get("warnings"))
    if warnings:
        primary_warnings, secondary_warnings = _partition_warnings_for_display(data, warnings)
        lines.append("### Warnings / risks")
        for item in primary_warnings[:5]:
            lines.append(f"- {item}")
        lines.append("")
        if secondary_warnings:
            lines.append("### Additional watch warnings")
            lines.append("(secondary signal — act on these only if they match current git-truth work)")
            for item in secondary_warnings[:5]:
                lines.append(f"- {item}")
            lines.append("")

    dc = _handoff_decision_context(data.get("decision_context"))
    if dc:
        lines.append("### Decision context")
        lines.append(f"- 시도: {dc.get('tried') or '(not provided)'}")
        lines.append(f"- 막힌 이유: {dc.get('blocked_by') or '(not provided)'}")
        lines.append(f"- 새 방향: {dc.get('switched_to') or '(not provided)'}")
        lines.append("")

    state_references = _handoff_lines(data.get("state_references"))
    if state_references:
        lines.append("### State references")
        lines.append(
            "새 AI는 PROJECT_CONTEXT.md를 먼저 읽은 뒤, 전체 구조화 작업 기록을 이어받기 위해 아래 상태 파일도 확인하세요."
        )
        lines.append("`.vibelign/work_memory.json` is the canonical source for accepted memory, verification, relevant files, risks, and recent events.")
        for item in state_references[:3]:
            lines.append(f"- `{item}`")

    lines.append("")
    return "\n".join(lines)


def _build_top_dense_slots(
    data: HandoffData, concrete_next_steps: list[str]
) -> tuple[str, str, str, str]:
    """Top-of-handoff dense 4 슬롯: Primary work item / Working tree truth / Next action / Done when.

    Why: 다음 AI 가 30초 안에 "작업 파일 / 진짜 상태 / 첫 행동 / 완료 조건" 파악할 수 있어야 함.
    v2.0.38: dense 슬롯은 git status 만 본다 (사용자 평가의 "git 이 진실, work_memory 는 보조"
    원칙). work_memory 가 잡은 vendored / build artifact 가 Primary 로 끼어드는 것을 방지.
    """
    wt_details = _handoff_lines(data.get("working_tree_details"))
    wt_paths = _working_tree_paths(data)
    total = len(wt_paths)

    if wt_paths:
        lead = wt_paths[0]
        if total > 1:
            primary = f"`{lead}` (+{total - 1} supporting changes)"
        else:
            primary = f"`{lead}`"
    else:
        primary = "(none)"

    if total > 0:
        kind_counts: dict[str, int] = {}
        for detail in wt_details:
            for marker in ("untracked", "added", "modified", "deleted", "renamed"):
                if f"— {marker}" in detail or f"— {marker} " in detail:
                    kind_counts[marker] = kind_counts.get(marker, 0) + 1
                    break
        if kind_counts:
            breakdown = ", ".join(
                f"{kind} {count}" for kind, count in sorted(kind_counts.items())
            )
            status = f"{total} files ({breakdown})"
        else:
            status = f"{total} files"
    else:
        status = "clean working tree"

    next_action = _handoff_text(data.get("first_next_action"), "")
    if not next_action or _is_handoff_reading_instruction(next_action) or _is_generic_watch_action(next_action):
        steps = concrete_next_steps
        next_action = next(
            (s for s in steps if s and not _is_generic_watch_action(s)), ""
        )
    if not next_action:
        next_action = _default_next_action_for_dense_slot(wt_paths, data)

    done_when = _handoff_text(data.get("done_when"), "")

    return primary, status, next_action, done_when


def _working_tree_paths(data: HandoffData) -> list[str]:
    wt_details = _handoff_lines(data.get("working_tree_details"))
    wt_paths: list[str] = []
    for line in wt_details:
        path = _detail_path(line)
        if path and path not in wt_paths:
            wt_paths.append(path)
    return sorted(wt_paths, key=lambda path: _primary_work_item_priority(path, wt_details))


def _primary_work_item_priority(path: str, details: list[str]) -> tuple[int, int, int, int, str]:
    detail_by_path = {_detail_path(detail): detail for detail in details}
    detail = detail_by_path.get(path, "")
    lower = path.lower()
    is_plan_doc = lower.startswith("docs/superpowers/plans/") or lower.startswith(
        "docs/superpowers/specs/"
    )
    is_readme = lower == "readme.md" or lower.endswith("/readme.md")
    is_generated_runtime = "vib-runtime/" in lower or "/_internal/" in lower
    is_docs = lower.endswith(".md")
    is_new = "— untracked" in detail or "— added" in detail
    return (
        0 if _looks_like_handoff_context_work([path]) else 1,
        0 if is_plan_doc else 1,
        3 if is_generated_runtime else (2 if is_readme else 0),
        0 if is_new else (1 if is_docs else 0),
        lower,
    )


def _default_next_action_for_dense_slot(wt_paths: list[str], data: HandoffData) -> str:
    verification = _handoff_lines(data.get("verification"))
    freshness = _handoff_text(data.get("verification_freshness"), "")
    if wt_paths:
        lead = wt_paths[0]
        if lead.endswith(".md"):
            return f"Review `{lead}` first, treat its explicitly sectioned content as authoritative, then rerun verification before commit."
        if lead.endswith((".py", ".ts", ".tsx", ".rs", ".js")):
            return f"Review `{lead}` first, confirm the scope is still narrow, then rerun focused verification before commit."
        return f"Review `{lead}` first, then confirm verification is current before commit."
    if verification and freshness == "stale":
        last_cmd = verification[-1].partition(" -> ")[0].strip()
        if last_cmd:
            return f"Rerun `{last_cmd}` before committing any remaining changes."
    return "Review the current handoff state, pick the next scoped git-truth change, and refresh verification before commit."


def _partition_warnings_for_display(
    data: HandoffData, warnings: list[str]
) -> tuple[list[str], list[str]]:
    wt_paths = set(_working_tree_paths(data))
    primary: list[str] = []
    secondary: list[str] = []
    for item in warnings:
        if " — " not in item:
            primary.append(item)
            continue
        path = _detail_path(item)
        if path in wt_paths:
            primary.append(item)
        else:
            secondary.append(item)
    if primary:
        return primary, secondary
    return secondary[:5], secondary[5:]


def _merge_changed_files(primary: list[str], secondary: list[str]) -> list[str]:
    merged: list[str] = []
    for item in primary + secondary:
        if item and item not in merged:
            merged.append(item)
    return merged[:10]


def _format_working_tree_live_changes(details: list[str], count: int) -> str | None:
    if count <= 0:
        return None
    prioritized_details = _prioritize_change_details(details)
    lines = [f"- git status 기준 현재 변경 {count}개 파일"]
    shown_details = prioritized_details[:_HANDOFF_CHANGE_DISPLAY_LIMIT]
    lines.extend(f"- {item}" for item in shown_details)
    hidden = count - min(count, len(shown_details))
    if hidden > 0:
        lines.append(f"- … 추가 {hidden}개 변경은 git status --porcelain으로 확인")
    return "\n".join(lines)


def _prioritize_change_details(details: list[str]) -> list[str]:
    return sorted(details, key=lambda detail: _change_priority(_detail_path(detail), detail))


def _prioritize_changed_files(files: list[str], details: list[str]) -> list[str]:
    detail_by_path = {_detail_path(detail): detail for detail in details}
    return sorted(files, key=lambda path: _change_priority(path, detail_by_path.get(path, "")))


def _detail_path(detail: str) -> str:
    return detail.split(" — ", 1)[0]


def _change_priority(path: str, detail: str) -> tuple[int, int, int, str]:
    is_new = "— untracked" in detail or "— added" in detail
    is_handoff_core = _looks_like_handoff_context_work([path])
    is_auto_state = "/.omc/" in path or path.startswith(".omc/")
    return (
        0 if is_handoff_core else 1,
        0 if is_new else 1,
        1 if is_auto_state else 0,
        path,
    )


def _format_working_tree_session_summary(
    details: list[str], files: list[str], count: int
) -> str | None:
    if count <= 0:
        return None
    paths = files or [item.split(" — ", 1)[0] for item in details]
    if _looks_like_handoff_context_work(paths):
        return (
            "Current uncommitted work is improving VibeLign Session Handoff "
            "self-sufficiency for AI-to-AI continuation. Git status remains the "
            f"source of truth for {count} handoff-visible changed files, while "
            "the narrative summary preserves why the handoff work exists. The "
            "changes cover transfer git-context collection, handoff rendering, "
            "MCP/CLI verification flow, and regression tests. Before committing, "
            "separate unrelated local state from the handoff-context changes and "
            "keep the verification snapshot current."
        )
    # v2.0.37: 단일 파일 시나리오는 path / file kind 를 inline 으로 결론 형태 제공
    if count == 1 and paths:
        single = paths[0]
        if single.endswith(".md"):
            return (
                f"Current work is narrowed to the docs file `{single}`; treat any "
                "explicitly section-marked content (§, ##, etc.) as the authoritative "
                "spec, and ignore unrelated runtime watch artifacts unless they reappear in git status."
            )
        if single.endswith((".py", ".ts", ".tsx", ".rs", ".js")):
            return (
                f"Current work is narrowed to the source file `{single}`; the change "
                "is small enough to review in one pass — re-run focused tests covering "
                "this file and update verification before committing."
            )
        return (
            f"Current work is narrowed to `{single}`; verify the file's role and "
            "rerun any test/build covering it before committing."
        )
    samples = [item.split(" (", 1)[0] for item in details[:3]] or paths[:3]
    if samples:
        return (
            f"Current uncommitted work has {count} handoff-visible file changes. "
            f"Key changes: {'; '.join(samples)}. Review the intent behind these "
            "changes, then update verification before committing."
        )
    return (
        f"Current uncommitted work has {count} handoff-visible file changes. "
        "Review the changed files for intent and update verification before committing."
    )


def _looks_like_handoff_context_work(paths: list[str]) -> bool:
    joined = " ".join(paths)
    return any(
        marker in joined
        for marker in (
            "vib_transfer_cmd",
            "transfer_git_context",
            "mcp_transfer",
            "test_vib_transfer_handoff",
            "test_transfer_git_context",
        )
    )


def _merge_handoff_lines(primary: list[str], secondary: list[str], limit: int = 8) -> list[str]:
    merged: list[str] = []
    for item in primary + secondary:
        if item and item not in merged:
            merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _merge_verification_lines(
    older: list[str], newer: list[str], limit: int = 5
) -> list[str]:
    merged: list[str] = []
    for item in older + newer:
        if not item:
            continue
        key = _verification_key(item)
        merged = [
            existing
            for existing in merged
            if _verification_key(existing) != key
        ]
        merged.append(item)
    return merged[-limit:]


def _verification_key(value: str) -> str:
    command = value.partition(" -> ")[0].strip()
    if command.startswith("uv run python -m py_compile"):
        return "uv run python -m py_compile"
    return command or value


def _live_working_changes_from_events(events: object) -> list[str]:
    live_changes: list[str] = []
    for event in _handoff_lines(events):
        if event.startswith("warning:"):
            continue
        display = event
        if ": " in event and " — " in event:
            kind_and_path, message = event.split(" — ", 1)
            kind, path = kind_and_path.split(": ", 1)
            if message in {f"{path} {kind}", f"{path} {kind}d", f"{path} modified"}:
                display = f"{kind}: {path}"
        if display in live_changes:
            continue
        live_changes.append(display)
    return live_changes[:5]


def _is_handoff_reading_instruction(value: object) -> bool:
    text = _handoff_text(value, "")
    if not text:
        return False
    return "PROJECT_CONTEXT.md" in text and "Session Handoff" in text and "먼저 읽" in text


def _is_generic_watch_action(value: object) -> bool:
    text = _handoff_text(value, "")
    return text in {
        "Review the latest change and refresh transfer handoff if needed.",
        "Confirm the deletion intent or restore the file if needed.",
    }


def _mentions_any(text: str, markers: tuple[str, ...]) -> bool:
    lower_text = text.lower()
    return any(marker.lower() in lower_text for marker in markers)


def _infer_active_intent(data: HandoffData) -> str | None:
    # v2.0.37: 구체 session_summary 가 있으면 그걸 우선 — generic canned narrative 는 빈 슬롯 fallback.
    summary = _handoff_text(data.get("session_summary"), "")
    if summary:
        return summary
    paths = " ".join(
        _handoff_files(data.get("changed_files"))
        + [entry["path"] for entry in _handoff_relevant_files(data.get("relevant_files"))]
    )
    if any(
        marker in paths
        for marker in (
            "work_memory",
            "vib_transfer_cmd",
            "TransferCard",
            "mcp_transfer",
            "mcp_tool_specs",
        )
    ):
        return (
            "transfer/work_memory 기반 Session Handoff 품질을 개선해, 새 AI가 현재 세션의 "
            "의도·검증·다음 작업을 바로 이어받게 만드는 중입니다."
        )
    return None


def _build_concrete_next_steps(data: HandoffData) -> list[str]:
    steps: list[str] = []
    next_action = _handoff_text(data.get("first_next_action"), "")
    if (
        next_action
        and not _is_handoff_reading_instruction(next_action)
        and not _is_generic_watch_action(next_action)
    ):
        steps.append(next_action)
    else:
        steps.extend(
            item
            for item in _handoff_lines(data.get("concrete_next_steps"))
            if not _is_generic_watch_action(item)
        )

    # v2.0.37: 시나리오별 구체화 — 단일 파일이면 파일명 inline + kind 별 권장 액션
    changed = _working_tree_paths(data)
    total = len(changed)
    if total == 1 and changed:
        single = changed[0]
        if single.endswith(".md"):
            steps.append(
                f"Review `{single}` as authoritative spec — check §- / ##- marked sections for canonical answers."
            )
        elif single.endswith((".py", ".ts", ".tsx", ".rs", ".js")):
            steps.append(
                f"Review `{single}` for intent and scope; the change is small enough for one-pass review."
            )

    if not steps and _looks_like_handoff_context_work(_handoff_files(data.get("changed_files"))):
        steps.append(
            "Review the uncommitted handoff-context changes, keep unrelated local "
            "state separate, then prepare focused commits only after verification is current."
        )
    verification = _handoff_lines(data.get("verification"))
    mentions_verification = any(
        _mentions_any(step, ("pytest", "build", "test", "테스트", "verification"))
        for step in steps
    )
    # v2.0.37: stale verification 이면 정확한 명령어를 next step 으로 승격
    freshness = _handoff_text(data.get("verification_freshness"), "")
    if verification and freshness == "stale":
        last_cmd = verification[-1].partition(" -> ")[0].strip()
        if last_cmd:
            steps.append(f"Rerun (verification stale): `{last_cmd}`")
    elif verification:
        steps.append("Verification snapshot을 기준으로 실패나 회귀가 없는지 확인하세요.")
    elif not mentions_verification:
        steps.append("관련 pytest/build를 재실행하고 Verification snapshot을 갱신하세요.")
    mentions_warnings = any(
        _mentions_any(step, ("warning", "warnings", "risk", "risks", "경고"))
        for step in steps
    )
    if _handoff_lines(data.get("warnings")) and not mentions_warnings:
        steps.append("Warnings / risks를 검토하고 실제 수정 대상과 허용 가능한 경고를 구분하세요.")
    if _handoff_text(data.get("unfinished_work"), ""):
        steps.append("unrelated 변경을 분리한 뒤 handoff 관련 변경만 커밋 준비하세요.")
    if not steps:
        steps.append("현재 Session Handoff의 Active intent에 맞춰 다음 작업을 이어가세요.")
    return steps[:5]


def _enrich_handoff_with_work_memory(root: Path, data: HandoffData) -> HandoffData:
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.memory.store import build_handoff_summary

    # v2.0.37: verification freshness 라벨은 staleness 분기와 무관하게 항상 계산.
    freshness = transfer_git_context.get_verification_freshness(root)
    if freshness:
        data["verification_freshness"] = freshness

    summary = build_handoff_summary(MetaPaths(root).work_memory_path)
    if summary is None:
        return data
    if not data.get("verification_freshness") and summary.get("verification_freshness"):
        data["verification_freshness"] = summary.get("verification_freshness")

    stale_warning = _get_work_memory_staleness_warning(root)
    if stale_warning:
        if not data.get("active_intent"):
            data["active_intent"] = summary.get("active_intent")
        verification = summary.get("verification")
        if verification:
            data["verification"] = _merge_verification_lines(
                verification, _handoff_lines(data.get("verification")), limit=5
            )
        state_references = summary.get("state_references")
        if state_references:
            data["state_references"] = state_references
        data["warnings"] = _merge_handoff_lines(
            [stale_warning], _handoff_lines(data.get("warnings"))
        )
        return data

    if not data.get("active_intent"):
        data["active_intent"] = summary.get("active_intent")
    if not data.get("session_summary"):
        data["session_summary"] = summary.get("session_summary")
    if not data.get("first_next_action"):
        data["first_next_action"] = summary.get("first_next_action")
    if not data.get("unfinished_work"):
        data["unfinished_work"] = summary.get("unfinished_work")
    concrete_next_steps = summary.get("concrete_next_steps")
    if concrete_next_steps:
        data["concrete_next_steps"] = concrete_next_steps
    data["changed_files"] = _merge_changed_files(
        _handoff_files(data.get("changed_files")),
        _handoff_files(summary.get("changed_files")),
    )
    data["change_details"] = _merge_handoff_lines(
        _handoff_lines(data.get("change_details")),
        _handoff_lines(summary.get("change_details")),
    )
    relevant_files = summary.get("relevant_files")
    if relevant_files:
        data["relevant_files"] = cast(list[dict[str, str]], relevant_files)
    recent_events = summary.get("recent_events")
    if recent_events:
        data["recent_events"] = recent_events
        if not data.get("completed_work"):
            live_changes = _live_working_changes_from_events(recent_events)
            if live_changes:
                data["completed_work"] = "\n".join(f"- {event}" for event in live_changes)
        # v2.0.37: git status 와 무관한 work_memory 이벤트만 Supporting watch context 로 분리.
        # _live_working_changes_from_events 로 redundant message 패턴 (path+kind echo) 도 정리.
        wt_paths = {
            _detail_path(line)
            for line in _handoff_lines(data.get("working_tree_details"))
        }
        cleaned_events = _live_working_changes_from_events(recent_events)
        supporting: list[str] = []
        for event_line in cleaned_events:
            event_path = event_line.split(": ", 1)[-1].split(" — ", 1)[0]
            if event_path in wt_paths:
                continue
            if event_line not in supporting:
                supporting.append(event_line)
        if supporting:
            data["supporting_watch_context"] = supporting[:_HANDOFF_CHANGE_DISPLAY_LIMIT]
    warnings = summary.get("warnings")
    if warnings:
        data["warnings"] = warnings
    verification = summary.get("verification")
    if verification:
        data["verification"] = _merge_verification_lines(
            verification, _handoff_lines(data.get("verification")), limit=5
        )
    state_references = summary.get("state_references")
    if state_references:
        data["state_references"] = state_references
    return data


def enrich_handoff_with_work_memory(root: Path, data: HandoffData) -> HandoffData:
    return _enrich_handoff_with_work_memory(root, data)


def _build_current_work_section(
    checkpoints: list[CheckpointSummary], handoff_data: HandoffData | None
) -> str:
    last_work = checkpoints[0]["message"] if checkpoints else "(체크포인트 없음)"
    last_time = checkpoints[0]["time"] if checkpoints else ""
    if handoff_data is None:
        return (
            f"- **마지막 작업**: {last_time} — `{last_work}`\n"
            "- **상태**: 작업 진행 중 (아래 체크포인트 기록 참고)"
        )

    active = _handoff_text(handoff_data.get("active_intent"), "") or _handoff_text(
        handoff_data.get("session_summary"), "Session Handoff 기준 현재 작업"
    )
    unfinished = _handoff_text(handoff_data.get("unfinished_work"), "")
    status = unfinished or "Session Handoff 기준으로 이어서 작업 가능"
    return (
        f"- **현재 작업**: `{active}`\n"
        f"- **상태**: {status}\n"
        f"- **체크포인트 참고**: {last_time} — `{last_work}` "
        "(handoff/git 상태가 실제 이어받을 기준)"
    )


def _build_context_content(
    root: Path,
    compact: bool = False,
    full: bool = False,
    handoff_data: HandoffData | None = None,
) -> str:
    """PROJECT_CONTEXT.md 내용 생성."""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = _detect_project_name(root)
    tech_stack = _detect_tech_stack(root)
    checkpoints = _get_recent_checkpoints(root, n=3 if compact else 5)
    agents_rules = _read_agents_md(root)
    run_commands = _detect_run_commands(root)

    # 파일 트리 (compact면 깊이 2, full이면 4, 기본 3)
    max_depth = 2 if compact else (4 if full else 3)
    file_tree = _build_file_tree(root, max_depth=max_depth)

    current_work_section = _build_current_work_section(checkpoints, handoff_data)

    # 체크포인트 테이블
    cp_rows = ""
    for cp in checkpoints:
        cp_rows += f"| {cp['time']} | {cp['message']} |\n"

    # 실행 명령어
    run_cmd_str = "\n".join(f"  {cmd}" for cmd in run_commands)

    # Session Handoff 블록 (--handoff 모드일 때만)
    handoff_section = ""
    if handoff_data:
        handoff_section = _build_handoff_block(handoff_data) + "\n---\n\n"

    content = f"""{_TRANSFER_MARKER}
<!--
  ⚡ AI Transfer Context — Generated by VibeLign
  이 파일을 읽으면 이 프로젝트를 즉시 파악할 수 있어요.
  Generated: {now_str} | `vib transfer`

  📌 AI 툴에게: Session Handoff 블록을 먼저 읽고 작업을 시작하세요.
-->

{handoff_section}# ⚡ {project_name} — AI Transfer Context

> 이 파일은 `vib transfer`로 자동 생성되었습니다.
> **AI 툴이 바뀌어도 이 파일 하나로 즉시 이어서 작업 가능합니다.**

---

## 1. 지금 무엇을 작업 중인가

{current_work_section}

---

## 2. 프로젝트 요약

- **프로젝트명**: {project_name}
- **기술 스택**: {", ".join(tech_stack)}
- **루트 경로**: {root}

---

## 3. 파일 구조

```
{file_tree}
```

> ⭐ = 핵심 진입점 파일

---

## 4. 최근 체크포인트 (작업 이력)

| 시간 | 작업 내용 |
|------|-----------|
{cp_rows}
> 전체 기록: `vib history`

---

## 5. AI 작업 규칙 (AGENTS.md)

```
{agents_rules}
```

---

## 6. 실행 방법

```bash
{run_cmd_str}
```

---

## 7. VibeLign 필수 명령어

```bash
vib checkpoint "설명"  # 작업 전 반드시 저장
vib undo               # 잘못됐으면 되돌리기
vib history            # 작업 이력 보기
vib transfer           # 이 파일 갱신
```

---

*Generated by [VibeLign](https://github.com/yesonsys03-web/VibeLign) — AI 코딩 안전망*
"""
    return content


def build_context_content(
    root: Path,
    compact: bool = False,
    full: bool = False,
    handoff_data: HandoffData | None = None,
) -> str:
    return _build_context_content(
        root, compact=compact, full=full, handoff_data=handoff_data
    )


def _get_recent_commits(root: Path, n: int = 5) -> list[str]:
    return transfer_git_context.get_recent_commits(root, n=n)


def _get_detailed_commits(root: Path, n: int = 10) -> list[transfer_git_context.DetailedCommit]:
    return transfer_git_context.get_detailed_commits(root, n=n)


def _get_uncommitted_summary(root: Path) -> str | None:
    return transfer_git_context.get_uncommitted_summary(root)


def _get_work_memory_staleness_warning(root: Path) -> str | None:
    return transfer_git_context.get_work_memory_staleness_warning(root)


def _persist_handoff_memory(root: Path, data: HandoffData) -> None:
    """Persist explicit handoff facts so future transfers do not depend on watch."""
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.memory.store import (
        add_memory_decision,
        add_memory_verification,
        is_memory_read_only,
        set_memory_next_action,
    )

    work_memory_path = MetaPaths(root).work_memory_path
    if is_memory_read_only(work_memory_path):
        clack_info(
            "memory schema is newer than this VibeLign supports; skipping handoff memory persistence."
        )
        return
    decision_context = _handoff_decision_context(data.get("decision_context"))
    if decision_context:
        add_memory_decision(
            work_memory_path,
            "Handoff decision: "
            f"tried={decision_context['tried']}; "
            f"blocked_by={decision_context['blocked_by']}; "
            f"switched_to={decision_context['switched_to']}",
            updated_by="vib transfer --handoff",
        )
    verification_to_persist = _handoff_lines(data.get("verification_to_persist"))
    if not verification_to_persist:
        verification_to_persist = _handoff_lines(data.get("verification"))
    for item in verification_to_persist:
        add_memory_verification(work_memory_path, item)
    for item in _handoff_lines(data.get("decision_notes")):
        add_memory_decision(work_memory_path, item, updated_by="vib transfer --handoff")
    next_action = _handoff_text(data.get("first_next_action"), "")
    if next_action and data.get("first_next_action_confirmed") is True:
        set_memory_next_action(work_memory_path, next_action)


def persist_handoff_memory(root: Path, data: HandoffData) -> None:
    _persist_handoff_memory(root, data)


def _resolve_transfer_out_path(root: Path, out_file: str) -> Path:
    candidate = Path(out_file)
    out_path = candidate if candidate.is_absolute() else root / candidate
    root_resolved = root.resolve()
    out_resolved = out_path.resolve(strict=False)
    if out_resolved != root_resolved and root_resolved not in out_resolved.parents:
        raise ValueError("--out path must stay inside the project root")
    return out_resolved


def _handoff_quality(data: HandoffData) -> tuple[str, str]:
    """handoff 완성도 평가. (이모지, 메시지) 반환."""
    score = 0
    missing: list[str] = []

    summary = _handoff_text(data.get("session_summary"), "")
    if summary and summary != "(not provided)":
        score += 40
    else:
        missing.append("현재 세션 작업 요약")

    next_action = _handoff_text(data.get("first_next_action"), "")
    if next_action and next_action != "(not provided)":
        score += 40
    else:
        missing.append("다음 AI가 할 일")

    if _handoff_files(data.get("changed_files")):
        score += 20

    if score >= 80:
        return "🟢", f"좋음 ({score}%)"
    elif score >= 40:
        tips = ", ".join(missing)
        return "🟡", f"보통 ({score}%) — 추가하면 좋아요: {tips}"
    else:
        tips = ", ".join(missing)
        return "🔴", f"부족 ({score}%) — 꼭 추가하세요: {tips}"


_AGENTS_HANDOFF_MARKER = "<!-- VibeLign Handoff Instruction -->"
_AGENTS_HANDOFF_BLOCK = """{marker}
## AI 전환 / Session Handoff

새 채팅을 열거나 다른 AI 툴로 이동했을 때:

1. `PROJECT_CONTEXT.md` 파일을 가장 먼저 읽으세요.
2. 파일 맨 위의 `## Session Handoff` 블록을 확인하세요.
3. `State references`에 `.vibelign/work_memory.json`이 있으면 함께 읽어 전체 작업 기록을 확인하세요.
4. `Next action` 항목에 적힌 작업부터 시작하세요.

> 이 지시는 `vib transfer --handoff` 실행 시 자동으로 추가됩니다.
""".format(marker=_AGENTS_HANDOFF_MARKER)


def _inject_agents_handoff_instruction(root: Path) -> None:
    """AGENTS.md가 있으면 handoff 읽기 지시를 추가 (중복 방지)."""
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        return
    text = agents_path.read_text(encoding="utf-8")
    if _AGENTS_HANDOFF_MARKER in text:
        return  # 이미 있음
    _ = agents_path.write_text(
        text.rstrip() + "\n\n" + _AGENTS_HANDOFF_BLOCK, encoding="utf-8"
    )


def inject_agents_handoff_instruction(root: Path) -> None:
    _inject_agents_handoff_instruction(root)


def get_changed_files(root: Path) -> list[str]:
    return _get_changed_files(root)


def get_working_tree_summary(root: Path) -> transfer_git_context.WorkingTreeSummary:
    return _get_working_tree_summary(root)


def _collect_handoff_data_from_cli(
    root: Path,
    no_prompt: bool,
    session_summary: str | None = None,
    first_next_action: str | None = None,
    verification: list[str] | None = None,
    decision: list[str] | None = None,
) -> HandoffData:
    """CLI 경로(파일 기반 폴백)로 handoff_data 수집."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    working_tree = _get_working_tree_summary(root)
    changed_files = working_tree["files"]
    change_details = working_tree["details"]
    changed_count = working_tree["count"]
    checkpoints = _get_recent_checkpoints(root, n=1)
    latest_cp = checkpoints[0]["message"] if checkpoints else None

    data: HandoffData = {
        "generated_at": now_str,
        "source": "file_fallback",
        "quality": "auto-drafted",
        "session_summary": _format_working_tree_session_summary(
            change_details, changed_files, changed_count
        ),
        "changed_files": changed_files,
        "changed_file_count": changed_count,
        "change_details": change_details,
        "working_tree_details": list(change_details),
        "completed_work": _format_working_tree_live_changes(change_details, changed_count),
        "unfinished_work": working_tree["summary"],
        "first_next_action": None,
        "decision_context": None,
        "latest_checkpoint": latest_cp,
        "latest_checkpoint_note": "reference only; handoff/git state is current"
        if changed_count
        else None,
        "verification": verification or [],
        "decision_notes": decision or [],
        "first_next_action_confirmed": False,
    }
    git_completed_work: str | None = None

    # git 커밋 메시지로 session_summary 초안 생성
    recent_commits = _get_recent_commits(root, n=5)
    commit_draft = ", ".join(recent_commits) if recent_commits else None
    if recent_commits:
        data["recent_git_context"] = recent_commits

    # 상세 커밋 정보로 completed_work 자동 생성
    detailed = _get_detailed_commits(root, n=10)
    if detailed:
        work_lines: list[str] = []
        for c in detailed:
            line = f"- `{c['hash']}` {c['message']}"
            if c["files"]:
                line += f"\n  변경: {c['files']}"
            work_lines.append(line)
        git_completed_work = "\n".join(work_lines)
        data["completed_work"] = git_completed_work

    # 커밋되지 않은 변경으로 unfinished_work 감지
    stale_work_memory_warning = _get_work_memory_staleness_warning(root)
    data = _enrich_handoff_with_work_memory(root, data)
    current_session_events = _live_working_changes_from_events(data.get("recent_events"))
    if stale_work_memory_warning:
        data["warnings"] = _merge_handoff_lines(
            [stale_work_memory_warning], _handoff_lines(data.get("warnings"))
        )
        data["changed_files"] = changed_files
        data["changed_file_count"] = changed_count
        data["change_details"] = change_details
        if changed_count:
            data["completed_work"] = _format_working_tree_live_changes(
                change_details, changed_count
            )
        elif git_completed_work:
            data["completed_work"] = git_completed_work
        data.pop("recent_events", None)
    elif changed_count:
        # changed_files / change_details 는 enrich 단계에서 git status 와 work_memory
        # recent_events 가 이미 합쳐졌으므로 덮어쓰지 않는다.
        # changed_file_count 는 합쳐진 displayed 목록 크기에 맞춰 보정 (변경 파일 +N 표기 정확도).
        merged_files = _handoff_files(data.get("changed_files"))
        data["changed_file_count"] = max(changed_count, len(merged_files))
        data["unfinished_work"] = working_tree["summary"]
        data["completed_work"] = _format_working_tree_live_changes(
            change_details, changed_count
        )
    elif current_session_events:
        data["completed_work"] = "\n".join(
            f"- {event}" for event in current_session_events[:5]
        )

    if commit_draft and not data.get("session_summary"):
        data["session_summary"] = commit_draft

    if session_summary:
        data["session_summary"] = session_summary
        data["quality"] = "gui-assisted"
    if first_next_action:
        data["first_next_action"] = first_next_action
        data["first_next_action_confirmed"] = True
        data["quality"] = "gui-assisted"
    if verification:
        data["verification"] = _merge_verification_lines(
            _handoff_lines(data.get("verification")), verification, limit=5
        )
        data["verification_to_persist"] = verification
        data["quality"] = "gui-assisted"
    if decision:
        data["decision_notes"] = decision
        data["active_intent"] = decision[-1]
        data["quality"] = "gui-assisted"

    if no_prompt:
        return data

    # 자동 감지 정보 출력
    clack_info("")
    clack_info("  📋 자동 감지 현황:")
    if changed_files:
        clack_info(
            f"     변경 파일: {', '.join(changed_files[:4])}"
            + (" …" if len(changed_files) > 4 else "")
        )
    else:
        clack_info("     변경 파일: (없음)")
    if latest_cp:
        clack_info(f"     최근 체크포인트: {latest_cp}")

    # git 커밋 초안 확인
    if data.get("session_summary"):
        clack_info("")
        clack_info("  💡 현재 세션 작업 요약이 이미 준비되어 있어요.")
    elif commit_draft:
        clack_info("")
        clack_info("  💡 현재 세션 작업 초안 (최근 커밋 기반):")
        for c in recent_commits:
            clack_info(f"     • {c}")
        clack_info("")
        try:
            keep = input("  이 내용으로 할까요? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            keep = ""
        if keep == "n":
            data["session_summary"] = None
            try:
                manual = input("  현재 세션 작업 요약 (한 줄): ").strip()
            except (EOFError, KeyboardInterrupt):
                manual = ""
            if manual:
                data["session_summary"] = manual
    else:
        clack_info("")
        try:
            manual = input("  현재 세션 작업 요약 (선택, 엔터 = 건너뜀): ").strip()
        except (EOFError, KeyboardInterrupt):
            manual = ""
        if manual:
            data["session_summary"] = manual

    clack_info("")

    # 필수: 다음 AI 첫 번째 할 일
    if data.get("first_next_action"):
        clack_info("  다음 AI 첫 작업도 이미 준비되어 있어요.")
    else:
        try:
            next_action = input("  다음 AI가 먼저 할 일을 한 줄로 알려주세요: ").strip()
        except (EOFError, KeyboardInterrupt):
            next_action = ""
        if next_action:
            data["first_next_action"] = next_action
            data["first_next_action_confirmed"] = True
            data["quality"] = "user-reviewed"

    # 선택: 방향 전환 컨텍스트
    try:
        dc_ans = input("  방향이 바뀐 게 있나요? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        dc_ans = ""
    if dc_ans == "y":
        try:
            tried = input("    Tried (시도한 것): ").strip()
            blocked = input("    Blocked by (막힌 이유): ").strip()
            switched = input("    Switched to (새 방향): ").strip()
        except (EOFError, KeyboardInterrupt):
            tried = blocked = switched = ""
        if any([tried, blocked, switched]):
            data["decision_context"] = {
                "tried": tried or "(not provided)",
                "blocked_by": blocked or "(not provided)",
                "switched_to": switched or "(not provided)",
            }

    return data


def run_transfer(args: object) -> None:
    """vib transfer 실행."""
    root = resolve_project_root(Path.cwd())
    compact = _arg_bool(args, "compact")
    full = _arg_bool(args, "full")
    handoff = _arg_bool(args, "handoff")
    ai = _arg_bool(args, "ai")
    no_prompt = _arg_bool(args, "no_prompt")
    print_mode = _arg_bool(args, "print_mode")
    dry_run = _arg_bool(args, "dry_run")
    out_file = _arg_text(args, "out") or "PROJECT_CONTEXT.md"
    session_summary = _arg_text(args, "session_summary")
    first_next_action = _arg_text(args, "first_next_action")
    verification = _arg_text_list(args, "verification")
    decision = _arg_text_list(args, "decision")
    try:
        out_path = _resolve_transfer_out_path(root, out_file)
    except ValueError as exc:
        clack_info(f"오류: {exc}")
        return

    if handoff and ai and (no_prompt or not sys.stdin.isatty()):
        _run_ai_handoff_non_interactive(
            root,
            out_path,
            session_summary=session_summary,
            first_next_action=first_next_action,
            verification=verification,
            decision=decision,
        )
        return

    clack_intro("VibeLign Transfer")

    # --handoff와 --compact/--full 동시 사용 불가
    if handoff and (compact or full):
        clack_info("오류: --handoff는 --compact 또는 --full과 함께 사용할 수 없습니다.")
        return

    clack_step("프로젝트 분석 중...")

    if handoff:
        handoff_data = _collect_handoff_data_from_cli(
            root,
            no_prompt=no_prompt,
            session_summary=session_summary,
            first_next_action=first_next_action,
            verification=verification,
            decision=decision,
        )
        _persist_handoff_memory(root, handoff_data)
        content = _build_context_content(root, handoff_data=handoff_data)
    else:
        handoff_data = None
        content = _build_context_content(root, compact=compact, full=full)

    tokens = _estimate_tokens(content)

    if dry_run:
        # 파일 저장 없이 handoff 블록만 미리 출력
        clack_info("")
        clack_info("  ─── [dry-run] 저장되지 않음 ───")
        if handoff_data:
            block = _build_handoff_block(handoff_data)
            for line in block.splitlines():
                clack_info(f"  {line}")
            quality_emoji, quality_msg = _handoff_quality(handoff_data)
            clack_info("")
            clack_info(f"  handoff 품질: {quality_emoji} {quality_msg}")
        else:
            clack_info(f"  예상 토큰: ~{tokens:,} tokens")
        clack_outro("dry-run 완료 — 실제 저장하려면 --dry-run 없이 실행하세요.")
        return

    _ = out_path.write_text(content, encoding="utf-8")

    if handoff:
        _inject_agents_handoff_instruction(root)

    clack_success(f"{out_file} 생성 완료!")
    clack_info(f"  📄 파일: {out_path}")
    clack_info(f"  🔢 예상 토큰: ~{tokens:,} tokens")

    # handoff 품질 표시
    if handoff and handoff_data:
        quality_emoji, quality_msg = _handoff_quality(handoff_data)
        clack_info(f"  handoff 품질: {quality_emoji} {quality_msg}")

    if handoff and print_mode and handoff_data:
        clack_info("")
        clack_info("  ─── Session Handoff 요약 (새 AI에 붙여넣기용) ───")
        block = _build_handoff_block(handoff_data)
        for line in block.splitlines():
            clack_info(f"  {line}")

    clack_info("")
    clack_info("  💡 사용법:")
    if handoff:
        clack_info(
            "     새 AI에게 PROJECT_CONTEXT.md 상단의 Session Handoff 블록을 읽혀주세요."
        )
    else:
        clack_info("     AI 툴에서 이 프로젝트 폴더를 열면 자동으로 읽혀요.")
        clack_info("     또는 새 AI 채팅에 PROJECT_CONTEXT.md 내용을 붙여넣으세요.")
    clack_outro("이제 어떤 AI 툴에서든 바로 이어서 작업할 수 있어요!")


def _run_ai_handoff_non_interactive(
    root: Path,
    out_path: Path,
    *,
    session_summary: str | None,
    first_next_action: str | None,
    verification: list[str],
    decision: list[str],
) -> None:
    from vibelign.core.memory.agent import build_handoff_summary_draft, handoff_draft_to_payload
    from vibelign.core.meta_paths import MetaPaths

    handoff_data = _collect_handoff_data_from_cli(
        root,
        no_prompt=True,
        session_summary=session_summary,
        first_next_action=first_next_action,
        verification=verification,
        decision=decision,
    )
    draft = build_handoff_summary_draft(
        MetaPaths(root).work_memory_path,
        cast(dict[str, object], cast(object, handoff_data)),
    )
    content = _build_context_content(root, handoff_data=handoff_data)
    _ = out_path.write_text(content, encoding="utf-8")
    _inject_agents_handoff_instruction(root)
    payload: dict[str, object] = {
        "ok": True,
        "mode": "handoff_ai_draft",
        "project_context_path": out_path.relative_to(root).as_posix(),
        "deterministic_handoff_written": True,
        "draft": handoff_draft_to_payload(draft),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


# === ANCHOR: VIB_TRANSFER_CMD_END ===
