# === ANCHOR: PATCH_GENERATOR_START ===
"""Patch Generator — Plan의 각 Action에 대해 변경 예정 미리보기를 생성한다.

patch_suggester.py를 재사용해 파일/앵커 위치를 찾는다.
실제 파일 수정은 하지 않는다 — 미리보기만 생성.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from vibelign.action_engine.models.action import Action
from vibelign.action_engine.models.plan import Plan


def _preview_add_anchor(action: Action, root: Path) -> str:
    """앵커 추가 예정 미리보기."""
    if not action.target_path:
        return "  파일 경로 미정 — vib anchor --suggest 실행 후 확인하세요."
    path = root / action.target_path
    if not path.exists():
        return f"  {action.target_path} (파일 없음 — 경로 확인 필요)"
    from vibelign.core.anchor_tools import extract_anchors
    anchors = extract_anchors(path)
    if anchors:
        return f"  {action.target_path}\n  → 이미 앵커 있음: {', '.join(anchors[:3])}"
    stem = path.stem.upper().replace("-", "_").replace(".", "_")
    return (
        f"  {action.target_path}\n"
        f"  + # === ANCHOR: {stem}_START ===\n"
        f"  + # === ANCHOR: {stem}_END ==="
    )


def _preview_fix_mcp(action: Action) -> str:
    """MCP 설정 변경 예정 미리보기."""
    cmd = action.command or "vib start --tools <tool>"
    target = action.target_path or "설정 파일"
    return (
        f"  {target}\n"
        f"  → 실행: {cmd}\n"
        f"  → vibelign MCP 서버 항목이 추가됩니다."
    )


def _preview_fix_project_map(action: Action) -> str:
    cmd = action.command or "vib start"
    return (
        f"  .vibelign/project_map.json 재생성\n"
        f"  → 실행: {cmd}"
    )


def _preview_split_file(action: Action) -> str:
    if not action.target_path:
        return "  파일 경로 미정 — 앵커 추가 후 확인하세요."
    return (
        f"  {action.target_path}\n"
        f"  → 기능별로 분리 예정 (앵커 확인 후 수동 또는 --apply로 실행)"
    )


def _preview_review(action: Action) -> str:
    target = action.target_path or "(경로 미정)"
    return f"  {target}\n  → 수동 검토 권장"


def generate_patch_preview(plan: Plan, root: Path) -> str:
    """Plan의 모든 Action에 대해 변경 예정 텍스트를 반환한다."""
    if not plan.actions:
        return "변경 예정 항목이 없습니다. 프로젝트 상태가 좋아요!\n"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "VibeLign 변경 예정 미리보기 (--patch)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"현재 점수: {plan.source_score} / 100  |  변경 예정: {len(plan.actions)}개",
        "",
    ]

    for i, action in enumerate(plan.actions, 1):
        lines.append(f"[{i}/{len(plan.actions)}] {action.action_type.upper()}")
        lines.append(f"  이유: {action.description[:80]}")

        if action.action_type == "add_anchor":
            lines.append(_preview_add_anchor(action, root))
        elif action.action_type == "fix_mcp":
            lines.append(_preview_fix_mcp(action))
        elif action.action_type == "fix_project_map":
            lines.append(_preview_fix_project_map(action))
        elif action.action_type == "split_file":
            lines.append(_preview_split_file(action))
        else:
            lines.append(_preview_review(action))

        lines.append("")

    lines.append("※ 이 미리보기는 파일을 수정하지 않아요.")
    lines.append("  실제 적용: vib doctor --apply")
    return "\n".join(lines) + "\n"
# === ANCHOR: PATCH_GENERATOR_END ===
