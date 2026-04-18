# === ANCHOR: VIB_PLAN_OVERRIDE_CMD_START ===
from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import cast

from vibelign.core.project_root import resolve_project_root
from vibelign.mcp.mcp_state_store import (
    load_planning_session,
    patch_session_now,
    save_planning_session,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import clack_success


# === ANCHOR: VIB_PLAN_OVERRIDE_CMD_RUN_VIB_PLAN_OVERRIDE_START ===
def run_vib_plan_override(args: Namespace) -> None:
    raw_reason_obj: object = getattr(args, "reason", [])
    if isinstance(raw_reason_obj, str):
        reason = raw_reason_obj.strip()
    elif isinstance(raw_reason_obj, (list, tuple)):
        reason_items = cast(list[object] | tuple[object, ...], raw_reason_obj)
        reason_parts = [
            item.strip()
            for item in reason_items
            if isinstance(item, str) and item.strip()
        ]
        reason = " ".join(reason_parts).strip()
    else:
        reason = ""
    if not reason:
        raise SystemExit(
            'override 이유를 입력하세요. 예: vib plan-override "plan이 현재 구조와 맞지 않음"'
        )

    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    planning = load_planning_session(meta) or {}
    if planning.get("active") is not True or not isinstance(
        planning.get("plan_id"), str
    ):
        raise SystemExit(
            "override할 활성 구조 계획이 없어요. 먼저 vib plan-structure를 실행하세요"
        )
    updated = dict(planning)
    now = patch_session_now()
    _ = updated.setdefault("active", True)
    _ = updated.setdefault("feature", None)
    _ = updated.setdefault("created_at", now)
    current_override_count = updated.get("override_count", 0)
    override_count = (
        current_override_count if isinstance(current_override_count, int) else 0
    )
    updated["override"] = True
    updated["override_reason"] = reason
    updated["overridden_at"] = now
    updated["updated_at"] = now
    updated["override_count"] = override_count + 1
    save_planning_session(meta, updated)
    clack_success(f"구조 계획 override를 기록했어요: {reason}")
# === ANCHOR: VIB_PLAN_OVERRIDE_CMD_RUN_VIB_PLAN_OVERRIDE_END ===
# === ANCHOR: VIB_PLAN_OVERRIDE_CMD_END ===
