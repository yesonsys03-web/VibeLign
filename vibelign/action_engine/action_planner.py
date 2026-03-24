# === ANCHOR: ACTION_PLANNER_START ===
"""Action Planner — DoctorV2Report를 실행 가능한 Plan으로 변환한다.

흐름:
    1. issue 목록 수집
    2. 각 issue → 후보 Action 생성
    3. 의존 순서 정렬 (add_anchor → split_file)
    4. 순서 확정된 Plan 반환
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from vibelign.action_engine.models.action import Action
from vibelign.action_engine.models.plan import Plan


# action_type 실행 우선순위 (낮을수록 먼저)
_ACTION_PRIORITY: Dict[str, int] = {
    "fix_project_map": 0,
    "fix_mcp": 1,
    "add_anchor": 2,
    "split_file": 3,   # add_anchor 이후에만 안전
    "review": 9,
}

# action_type → 선행 필요 action_type 목록
_ACTION_DEPENDENCY: Dict[str, List[str]] = {
    "split_file": ["add_anchor"],
}


def _classify_issue(issue: Dict[str, Any]) -> str:
    """issue dict에서 action_type을 결정한다."""
    found: str = issue.get("found", "")
    next_step: str = issue.get("next_step", "")
    text = found + " " + next_step

    if "project_map" in text or "vib start" in next_step:
        return "fix_project_map"
    if "MCP" in text or "mcp" in text.lower():
        return "fix_mcp"
    if "앵커" in text or "anchor" in text.lower():
        return "add_anchor"
    if "분리" in text or "나눠" in text or "split" in text.lower():
        return "split_file"
    return "review"


def _issue_to_action(issue: Dict[str, Any]) -> Action:
    """issue dict → Action 변환. path가 None이어도 안전하게 처리."""
    action_type = _classify_issue(issue)
    target_path = issue.get("path")  # Optional[str] — None 가능

    # 실행 명령어 결정
    command: str | None = None
    next_step: str = issue.get("next_step", "")
    if "`" in next_step:
        start = next_step.find("`") + 1
        end = next_step.find("`", start)
        if end > start:
            command = next_step[start:end]
    elif next_step.startswith("vib "):
        command = next_step.strip()

    depends_on = _ACTION_DEPENDENCY.get(action_type, [])

    return Action(
        action_type=action_type,
        description=issue.get("found", ""),
        target_path=target_path,
        command=command,
        depends_on=depends_on,
    )


def _topological_sort(actions: List[Action]) -> tuple[List[Action], List[str]]:
    """의존 순서를 보장하는 정렬.

    Returns:
        (sorted_actions, warnings)
    """
    warnings: List[str] = []
    present_types = {a.action_type for a in actions}

    for action in actions:
        for dep in action.depends_on:
            if dep not in present_types:
                warnings.append(
                    f"'{action.action_type}'이 '{dep}'에 의존하지만 plan에 없어요. "
                    f"수동으로 먼저 `vib anchor --suggest`를 실행하는 것을 권장해요."
                )

    sorted_actions = sorted(
        actions,
        key=lambda a: _ACTION_PRIORITY.get(a.action_type, 9),
    )
    return sorted_actions, warnings


def generate_plan(doctor_report: Any) -> Plan:
    """DoctorV2Report 또는 그 dict로부터 Plan을 생성한다."""
    if hasattr(doctor_report, "issues"):
        issues: List[Dict[str, Any]] = doctor_report.issues
        source_score: int = doctor_report.project_score
    else:
        issues = doctor_report.get("issues", [])
        source_score = doctor_report.get("project_score", 0)

    actions = [_issue_to_action(issue) for issue in issues]
    sorted_actions, warnings = _topological_sort(actions)

    return Plan(
        actions=sorted_actions,
        source_score=source_score,
        generated_at=datetime.now(timezone.utc).isoformat(),
        warnings=warnings,
    )
# === ANCHOR: ACTION_PLANNER_END ===
