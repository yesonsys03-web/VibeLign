# === ANCHOR: VIB_PLAN_CLOSE_CMD_START ===
from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from vibelign.core.project_root import resolve_project_root
from vibelign.mcp.mcp_state_store import (
    load_planning_session,
    patch_session_now,
    save_planning_session,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import clack_info, clack_success


# === ANCHOR: VIB_PLAN_CLOSE_CMD_RUN_VIB_PLAN_CLOSE_START ===
def run_vib_plan_close(_args: Namespace) -> None:
    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    planning = load_planning_session(meta)
    if not planning:
        clack_info("닫을 활성 구조 계획이 없어요.")
        return

    updated = dict(planning)
    updated["active"] = False
    updated["plan_id"] = None
    updated["override"] = False
    updated["override_reason"] = None
    _ = updated.pop("overridden_at", None)
    _ = updated.pop("override_count", None)
    updated["updated_at"] = patch_session_now()
    save_planning_session(meta, updated)
    clack_success("활성 구조 계획을 닫았어요.")
# === ANCHOR: VIB_PLAN_CLOSE_CMD_RUN_VIB_PLAN_CLOSE_END ===
# === ANCHOR: VIB_PLAN_CLOSE_CMD_END ===
