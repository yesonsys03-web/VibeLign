# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_START ===
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.core.structure_planner import build_structure_plan
from vibelign.mcp.mcp_state_store import save_planning_session
from vibelign.terminal_render import clack_intro, clack_step, clack_success, clack_warn


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_PLANSTRUCTUREARGS_START ===
class PlanStructureArgs(Protocol):
    feature: Sequence[str] | str
    ai: bool
    scope: str
    json: bool


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_PLANSTRUCTUREARGS_END ===


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD__FEATURE_TEXT_START ===
def _feature_text(raw_feature: Sequence[str] | str) -> str:
    if isinstance(raw_feature, str):
        return raw_feature.strip()
    return " ".join(
        str(item).strip() for item in raw_feature if str(item).strip()
    ).strip()


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD__FEATURE_TEXT_END ===


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_RUN_VIB_PLAN_STRUCTURE_START ===
def run_vib_plan_structure(args: object) -> None:
    raw_args = cast(PlanStructureArgs, args)
    feature = _feature_text(raw_args.feature)
    if not feature:
        raise SystemExit(
            '기능 설명을 입력하세요. 예: vib plan-structure "OAuth 인증 추가"'
        )

    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    meta.ensure_vibelign_dirs()

    if not bool(raw_args.json):
        clack_intro("VibeLign 구조 계획")
        clack_step("구조 계획 생성 중...")

    plan = build_structure_plan(
        root,
        feature,
        mode="ai" if bool(raw_args.ai) else "rules",
        scope=raw_args.scope,
    )
    plan_path = meta.plans_dir / f"{plan['id']}.json"
    _ = plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    planning_state = {
        "active": True,
        "plan_id": plan["id"],
        "feature": feature,
        "override": False,
        "override_reason": None,
        "override_count": 0,
        "created_at": plan["created_at"],
        "updated_at": plan["created_at"],
    }
    save_planning_session(meta, planning_state)

    if bool(raw_args.json):
        print(
            json.dumps(
                {
                    "ok": True,
                    "data": {
                        "plan_path": str(plan_path.relative_to(root)),
                        "plan": plan,
                    },
                },
                ensure_ascii=False,
            )
        )
        return

    required_new_files = plan.get("required_new_files", [])
    allowed_modifications = plan.get("allowed_modifications", [])
    messages_obj = plan.get("messages")
    summary = ""
    warnings: list[str] = []
    if isinstance(messages_obj, dict):
        messages = cast(dict[str, object], messages_obj)
        summary_value = messages.get("summary", "")
        summary = str(summary_value)
        raw_warnings = messages.get("warnings", [])
        if isinstance(raw_warnings, list):
            warning_items = cast(list[object], raw_warnings)
            warnings = [str(item) for item in warning_items]

    clack_success(f"계획 저장: {plan_path.relative_to(root)}")
    if summary:
        clack_step(summary)
    for item in warnings:
        clack_warn(item)

    if isinstance(allowed_modifications, list) and allowed_modifications:
        clack_step("수정 허용")
        allowed_items = cast(list[object], allowed_modifications)
        for item_obj in allowed_items:
            if isinstance(item_obj, dict):
                item = cast(dict[str, object], item_obj)
                path = item.get("path")
                anchor = item.get("anchor")
                print(f"- {path} ({anchor})")

    if isinstance(required_new_files, list) and required_new_files:
        clack_step("신규 생성")
        required_items = cast(list[object], required_new_files)
        for item_obj in required_items:
            if isinstance(item_obj, dict):
                item = cast(dict[str, object], item_obj)
                print(f"- {item.get('path')}")

    if not required_new_files:
        clack_warn(
            "신규 파일 없이 진행 가능한 계획입니다. 완료 후 vib guard로 검증하세요."
        )


# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_RUN_VIB_PLAN_STRUCTURE_END ===
# === ANCHOR: VIB_PLAN_STRUCTURE_CMD_END ===
