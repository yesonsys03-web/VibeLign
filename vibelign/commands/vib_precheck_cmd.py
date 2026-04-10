# === ANCHOR: VIB_PRECHECK_CMD_START ===
from __future__ import annotations

import json
import re
import sys
from argparse import Namespace
from difflib import SequenceMatcher
from pathlib import Path
from typing import cast

from vibelign.core.anchor_tools import COMMENT_PREFIX
from vibelign.core.hook_setup import is_claude_hook_enabled
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.core.structure_policy import (
    classify_structure_path,
    is_structure_production_kind,
    load_active_plan_payload,
    small_fix_line_threshold,
)

_ANCHOR_PATTERN = re.compile(r"ANCHOR:\s*[A-Z0-9_]+_(START|END)")
_SOURCE_EXTENSIONS = set(COMMENT_PREFIX.keys())


# === ANCHOR: VIB_PRECHECK_CMD__READ_STDIN_PAYLOAD_START ===
def _read_stdin_payload() -> dict[str, object]:
    if sys.stdin.isatty():
        print(
            "이 명령은 Claude hook이 stdin JSON payload와 함께 호출해야 해요.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        payload = cast(object, json.loads(sys.stdin.read() or "{}"))
    except json.JSONDecodeError:
        print("Claude hook payload를 읽지 못했어요.", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(payload, dict):
        print("Claude hook payload 형식이 올바르지 않아요.", file=sys.stderr)
        raise SystemExit(1)
    return cast(dict[str, object], payload)


# === ANCHOR: VIB_PRECHECK_CMD__READ_STDIN_PAYLOAD_END ===


# === ANCHOR: VIB_PRECHECK_CMD__PAYLOAD_FILE_INFO_START ===
def _payload_file_info(payload: dict[str, object]) -> tuple[str | None, str | None]:
    tool_name = payload.get("tool_name")
    if tool_name != "Write":
        return None, None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None, None
    raw = cast(dict[str, object], tool_input)
    file_path = raw.get("file_path")
    content = raw.get("content")
    if not isinstance(file_path, str) or not isinstance(content, str):
        return None, None
    return file_path, content


# === ANCHOR: VIB_PRECHECK_CMD__PAYLOAD_FILE_INFO_END ===


# === ANCHOR: VIB_PRECHECK_CMD__ADDED_LINE_COUNT_START ===
def _added_line_count(old_text: str, new_text: str) -> int:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    matcher = SequenceMatcher(a=old_lines, b=new_lines)
    added = 0
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in {"insert", "replace"}:
            added += max(0, j2 - j1)
    return added


# === ANCHOR: VIB_PRECHECK_CMD__ADDED_LINE_COUNT_END ===


# === ANCHOR: VIB_PRECHECK_CMD__PLANNING_STATUS_START ===
def _planning_status(root: Path, target_path: Path, content: str) -> tuple[str, str]:
    resolved_root = root.resolve()
    resolved_target = target_path.resolve(strict=False)
    try:
        rel_path = (
            str(resolved_target.relative_to(resolved_root))
            if resolved_target.is_absolute()
            else str(resolved_target)
        )
    except ValueError:
        return "planning_exempt", ""
    path_kind = classify_structure_path(rel_path)
    if (
        not is_structure_production_kind(path_kind)
        or target_path.suffix.lower() not in _SOURCE_EXTENSIONS
    ):
        return "planning_exempt", ""

    meta = MetaPaths(root)
    existing_text = ""
    if target_path.exists():
        try:
            existing_text = target_path.read_text(encoding="utf-8")
        except OSError:
            existing_text = ""
    if _added_line_count(existing_text, content) <= small_fix_line_threshold(meta):
        return "planning_exempt", ""

    plan_payload, _active_plan_id, plan_error = load_active_plan_payload(meta)
    if plan_error == "override":
        return "planning_exempt", ""
    if plan_error in {"missing_plan_file", "broken_plan", "invalid_state"}:
        return (
            "fail",
            "구조 계획 상태가 올바르지 않습니다. plan 파일과 state를 확인하세요",
        )
    if plan_payload is None and not target_path.exists():
        return "planning_required", "vib plan-structure를 먼저 실행하세요"
    if plan_payload is None:
        return "planning_exempt", ""

    required_new_files = cast(
        list[dict[str, object]], plan_payload.get("required_new_files", [])
    )
    required_new_paths = {
        str(item["path"])
        for item in required_new_files
        if isinstance(item.get("path"), str)
    }
    if not target_path.exists() and rel_path in required_new_paths:
        return "pass", ""

    allowed_modifications = cast(
        list[dict[str, object]], plan_payload.get("allowed_modifications", [])
    )
    allowed_paths = {
        str(item["path"])
        for item in allowed_modifications
        if isinstance(item.get("path"), str)
    }
    if rel_path in allowed_paths:
        return "pass", ""

    return "plan_exists_but_deviated", "현재 변경이 활성 구조 계획 범위를 벗어났습니다"


# === ANCHOR: VIB_PRECHECK_CMD__PLANNING_STATUS_END ===


# === ANCHOR: VIB_PRECHECK_CMD__HAS_ANCHOR_MARKERS_START ===
def _has_anchor_markers(path: Path, content: str) -> bool:
    if path.suffix.lower() not in _SOURCE_EXTENSIONS:
        return True
    return _ANCHOR_PATTERN.search(content) is not None


# === ANCHOR: VIB_PRECHECK_CMD__HAS_ANCHOR_MARKERS_END ===


# === ANCHOR: VIB_PRECHECK_CMD_RUN_VIB_PRECHECK_START ===
def run_vib_precheck(_args: Namespace) -> None:
    payload = _read_stdin_payload()
    file_path, content = _payload_file_info(payload)
    if file_path is None or content is None:
        raise SystemExit(0)

    root = resolve_project_root(Path.cwd())
    if not is_claude_hook_enabled(root):
        raise SystemExit(0)

    target_path = Path(file_path)
    if not target_path.is_absolute():
        target_path = root / target_path
    target_path = target_path.resolve(strict=False)
    resolved_root = root.resolve()

    try:
        rel_path = (
            str(target_path.relative_to(resolved_root))
            if target_path.is_absolute()
            else str(target_path)
        )
    except ValueError:
        print(json.dumps({"permissionDecision": "allow"}, ensure_ascii=False))
        raise SystemExit(0)
    if (
        not is_structure_production_kind(classify_structure_path(rel_path))
        or target_path.suffix.lower() not in _SOURCE_EXTENSIONS
    ):
        print(json.dumps({"permissionDecision": "allow"}, ensure_ascii=False))
        raise SystemExit(0)

    planning_status, planning_message = _planning_status(root, target_path, content)
    if planning_status in {"planning_required", "plan_exists_but_deviated", "fail"}:
        print(planning_message, file=sys.stderr)
        raise SystemExit(2)

    if not _has_anchor_markers(target_path, content):
        print("앵커가 없습니다. 앵커를 추가한 뒤 다시 시도하세요", file=sys.stderr)
        raise SystemExit(2)

    print(json.dumps({"permissionDecision": "allow"}, ensure_ascii=False))
    raise SystemExit(0)


# === ANCHOR: VIB_PRECHECK_CMD_RUN_VIB_PRECHECK_END ===
# === ANCHOR: VIB_PRECHECK_CMD_END ===
