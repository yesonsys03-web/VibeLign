# === ANCHOR: DOCTOR_V2_START ===
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List

from vibeguard.core.anchor_tools import extract_anchors
from vibeguard.core.project_scan import iter_source_files
from vibeguard.core.risk_analyzer import analyze_project


STATUS_LEVELS = [
    (90, "Safe"),
    (75, "Good"),
    (55, "Caution"),
    (35, "Risky"),
    (0, "High Risk"),
]


@dataclass
class DoctorV2Report:
    project_score: int
    status: str
    anchor_coverage: int
    stats: Dict[str, Any]
    issues: List[Dict[str, Any]]
    recommended_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _build_status(score: int) -> str:
    for threshold, label in STATUS_LEVELS:
        if score >= threshold:
            return label
    return "High Risk"


def _anchor_coverage(root: Path) -> int:
    source_files = list(iter_source_files(root))
    if not source_files:
        return 100
    covered = sum(1 for path in source_files if extract_anchors(path))
    return round((covered / len(source_files)) * 100)


def _issue_details(issues: List[str], suggestions: List[str]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for index, issue in enumerate(issues):
        rel = issue.split("에 ", 1)[0]
        next_step = (
            suggestions[index]
            if index < len(suggestions)
            else "관련 파일을 직접 확인하세요."
        )
        details.append(
            {
                "found": issue,
                "why_it_matters": f"{issue} 때문에 AI가 수정 범위를 넓게 잡거나 구조를 더 망가뜨릴 수 있습니다.",
                "next_step": next_step,
                "path": rel
                if "/" in rel or rel.endswith((".py", ".js", ".ts", ".tsx", ".jsx"))
                else None,
            }
        )
    return details


def _recommended_actions(legacy_suggestions: List[str]) -> List[str]:
    actions: List[str] = []
    seen: set[str] = set()
    for suggestion in legacy_suggestions:
        if "앵커" in suggestion:
            action = "vibeguard anchor --suggest"
        elif "분리" in suggestion:
            action = "큰 파일을 역할별로 나누는 작업을 계획하세요"
        else:
            action = suggestion
        if action not in seen:
            seen.add(action)
            actions.append(action)
    return actions[:6]


def analyze_project_v2(root: Path, strict: bool = False) -> DoctorV2Report:
    legacy = analyze_project(root, strict=strict)
    project_score = max(0, 100 - (legacy.score * 4))
    status = _build_status(project_score)
    coverage = _anchor_coverage(root)
    stats = dict(legacy.stats)
    stats["anchor_coverage"] = coverage
    stats["legacy_penalty"] = legacy.score
    return DoctorV2Report(
        project_score=project_score,
        status=status,
        anchor_coverage=coverage,
        stats=stats,
        issues=_issue_details(legacy.issues, legacy.suggestions),
        recommended_actions=_recommended_actions(legacy.suggestions),
    )


def build_doctor_envelope(root: Path, strict: bool = False) -> Dict[str, Any]:
    report = analyze_project_v2(root, strict=strict)
    return {"ok": True, "error": None, "data": report.to_dict()}


def render_doctor_markdown(
    report: DoctorV2Report, detailed: bool = False, fix_hints: bool = False
) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "VibeLign Project Health Report",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Project score: {report.project_score} / 100",
        f"Status: {report.status}",
        f"Anchor coverage: {report.anchor_coverage}%",
        "",
        "Main findings:",
    ]
    if report.issues:
        for index, item in enumerate(report.issues, 1):
            lines.append(f"{index}. {item['found']}")
    else:
        lines.append("1. 큰 구조 문제를 찾지 못했습니다.")

    if detailed and report.issues:
        lines.extend(["", "Detailed findings:"])
        for item in report.issues:
            lines.extend(
                [
                    f"- Found: {item['found']}",
                    f"  Why: {item['why_it_matters']}",
                    f"  Next: {item['next_step']}",
                ]
            )

    if fix_hints or report.recommended_actions:
        lines.extend(["", "Recommended next steps:"])
        for action in report.recommended_actions or ["vibeguard anchor --suggest"]:
            lines.append(f"- {action}")

    return "\n".join(lines) + "\n"


def render_doctor_json(envelope: Dict[str, Any]) -> str:
    return json.dumps(envelope, indent=2, ensure_ascii=False)
# === ANCHOR: DOCTOR_V2_END ===
