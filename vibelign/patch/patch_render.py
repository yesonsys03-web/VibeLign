# === ANCHOR: PATCH_RENDER_START ===
from collections.abc import Callable
from typing import cast


# === ANCHOR: PATCH_RENDER_BUILD_CONSTRAINTS_START ===
def build_constraints(codespeak: object) -> list[str]:
    constraints = [
        "patch only",
        "keep file structure",
        "no unrelated edits",
    ]
    patch_points = cast(dict[str, object], getattr(codespeak, "patch_points"))
    behavior_constraint = str(patch_points.get("behavior_constraint", "")).strip()
    if behavior_constraint:
        constraints.append(f"Behavior preservation: {behavior_constraint}")
    return constraints
# === ANCHOR: PATCH_RENDER_BUILD_CONSTRAINTS_END ===


# === ANCHOR: PATCH_RENDER_RENDER_MARKDOWN_START ===
def render_markdown(
    data: dict[str, object],
    *,
    build_contract: Callable[[dict[str, object]], dict[str, object]],
    preview_text: str | None = None,
# === ANCHOR: PATCH_RENDER_RENDER_MARKDOWN_END ===
) -> str:
    patch_plan = cast(dict[str, object], data["patch_plan"])
    contract = cast(
        dict[str, object], data.get("contract") or build_contract(patch_plan)
    )
    handoff = cast(dict[str, object] | None, data.get("handoff"))
    user_status = cast(dict[str, object], contract.get("user_status", {}))
    patch_points = cast(dict[str, object], contract.get("patch_points", {}))
    scope = cast(dict[str, object], contract.get("scope", {}))
    user_guidance = cast(list[object], contract.get("user_guidance", []))
    clarifying_questions = cast(list[object], contract.get("clarifying_questions", []))
    preconditions = cast(list[object], contract.get("preconditions", []))
    allowed_ops = cast(list[object], contract.get("allowed_ops", []))
    rationale = cast(list[object], patch_plan.get("rationale", []))
    allowed_files = cast(list[object], scope.get("allowed_files", []))
    lines: list[str] = [
        "# VibeLign 패치 계획",
        "",
        f"지금 상태: {user_status.get('title', '')}",
        "",
        str(user_status.get("reason", "")),
        "",
    ]
    if contract["status"] == "NEEDS_CLARIFICATION":
        lines.append("## 먼저 이렇게 해보세요")
        lines.extend(f"- {item}" for item in user_guidance)
        lines.extend(["", "## 먼저 확인하면 좋은 질문"])
        lines.extend(f"- {item}" for item in clarifying_questions)
        lines.append("")
    else:
        lines.append("## 이제 이렇게 진행하면 돼요")
        lines.extend(f"- {item}" for item in user_guidance)
        lines.append("")

    lines.extend(
        [
            "## 수정 대상 요약",
            f"- CodeSpeak : {patch_plan['codespeak']}",
            f"- 파일      : {patch_plan['target_file']}",
            f"- 앵커      : {patch_plan['target_anchor']}",
            f"- 목적지 파일 : {patch_plan.get('destination_target_file') or '[없음]'}",
            f"- 목적지 앵커 : {patch_plan.get('destination_target_anchor') or '[없음]'}",
            f"- 확신 정도 : {patch_plan['confidence']}",
            "",
            "## 정확한 수정 포인트",
            f"- 작업 종류 : {patch_points.get('operation', 'unknown')}",
            f"- 원래 위치 : {patch_points.get('source', '') or '[없음]'}",
            f"- 목표 위치 : {patch_points.get('destination', '') or '[없음]'}",
            f"- 대상 객체 : {patch_points.get('object', '') or '[없음]'}",
            "",
            "## 이 계획에서 허용하는 범위",
        ]
    )
    for item in allowed_files:
        lines.append(f"- 허용된 파일: {item}")
    lines.extend(
        [
            f"- 파일 상태: {scope.get('target_file_status', '')}",
            f"- 안전 구역 상태: {scope.get('target_anchor_status', '')}",
            "",
            "## 이 계획이 바로 실행되려면",
        ]
    )
    lines.extend(f"- {item}" for item in preconditions)
    lines.extend(["", "## 허용된 수정 방식"])
    lines.extend(f"- {item}" for item in allowed_ops)
    lines.extend(["", "## 왜 이렇게 골랐는지"])
    lines.extend(f"- {item}" for item in rationale)
    if contract["clarifying_questions"] and contract["status"] != "NEEDS_CLARIFICATION":
        lines.extend(["", "## 먼저 확인하면 좋은 질문"])
        lines.extend(f"- {item}" for item in clarifying_questions)
    if preview_text is not None:
        lines.extend(["", "## 미리 보기", "```text", preview_text, "```"])
    lines.extend(["", "## 다음에 할 일", str(user_status.get("next_step", ""))])
    if contract["status"] == "READY" and handoff is not None:
        lines.extend(
            [
                "",
                "────────────────────────────────────────",
                "📋 아래 내용을 복사해서 AI에게 붙여넣으세요",
                "────────────────────────────────────────",
                "",
                str(handoff["prompt"]),
                "",
                "────────────────────────────────────────",
            ]
        )
    return "\n".join(lines) + "\n"
# === ANCHOR: PATCH_RENDER_END ===
