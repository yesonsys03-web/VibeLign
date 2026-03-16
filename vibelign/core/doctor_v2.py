# === ANCHOR: DOCTOR_V2_START ===
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List

from vibelign.core.anchor_tools import extract_anchors
from vibelign.core.project_map import load_project_map
from vibelign.core.project_scan import iter_source_files
from vibelign.core.risk_analyzer import analyze_project


STATUS_LEVELS = [
    (85, "Safe"),
    (70, "Good"),
    (50, "Caution"),
    (30, "Risky"),
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
            else "관련 파일을 직접 열어서 확인해보세요."
        )
        details.append(
            {
                "found": issue,
                "why_it_matters": f"{issue} 때문에 AI가 엉뚱한 곳까지 건드리거나 코드를 더 꼬이게 만들 수 있어요.",
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
            action = "vib anchor --suggest"
        elif "분리" in suggestion or "나눠" in suggestion:
            action = "파일이 너무 길면 기능별로 나눠보세요 (AI 실수 예방에 도움돼요)"
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
    project_map, project_map_error = load_project_map(root)
    stats["anchor_coverage"] = coverage
    stats["legacy_penalty"] = legacy.score
    stats["project_map_loaded"] = project_map is not None
    issues = list(legacy.issues)
    suggestions = list(legacy.suggestions)
    if project_map is not None:
        stats["project_map_file_count"] = project_map.file_count
        stats["project_map_generated_at"] = project_map.generated_at
    elif project_map_error == "unsupported_project_map_schema":
        issues.append(".vibelign/project_map.json 파일의 버전이 맞지 않아요")
        suggestions.append("vib start 를 다시 실행하면 자동으로 고쳐져요")
    elif project_map_error == "invalid_project_map":
        issues.append(".vibelign/project_map.json 파일을 읽을 수 없어요")
        suggestions.append("vib start 를 다시 실행하면 자동으로 고쳐져요")
    return DoctorV2Report(
        project_score=project_score,
        status=status,
        anchor_coverage=coverage,
        stats=stats,
        issues=_issue_details(issues, suggestions),
        recommended_actions=_recommended_actions(suggestions),
    )


def build_doctor_envelope(root: Path, strict: bool = False) -> Dict[str, Any]:
    report = analyze_project_v2(root, strict=strict)
    return {"ok": True, "error": None, "data": report.to_dict()}


def render_doctor_markdown(
    report: DoctorV2Report, detailed: bool = False, fix_hints: bool = False
) -> str:
    status_line = {
        "Safe": "지금 상태가 아주 좋아요. 바로 다음 작업으로 넘어가도 됩니다.",
        "Good": "지금 상태가 좋아요. 작은 수정부터 시작하면 됩니다.",
        "Caution": "큰 문제는 아니지만, 먼저 몇 가지를 정리하면 더 안전해요.",
        "Risky": "바로 크게 수정하기보다, 먼저 문제를 줄이는 게 좋아요.",
        "High Risk": "지금은 수정부터 하기보다, 먼저 구조 문제를 확인하는 게 좋아요.",
    }.get(report.status, "현재 상태를 먼저 확인하는 게 좋아요.")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "VibeLign 프로젝트 상태 보기",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"프로젝트 점수: {report.project_score} / 100",
        f"현재 상태: {report.status}",
        status_line,
        f"AI 안전 구역 표시된 파일 비율: {report.anchor_coverage}%",
        "",
        "먼저 보면 좋은 점:",
    ]
    if report.issues:
        for index, item in enumerate(report.issues, 1):
            lines.append(f"{index}. {item['found']}")
    else:
        lines.append("1. 지금 바로 걱정할 큰 구조 문제는 보이지 않습니다.")

    if detailed and report.issues:
        lines.extend(["", "자세히 보면:"])
        for item in report.issues:
            lines.extend(
                [
                    f"- 찾은 문제: {item['found']}",
                    f"  왜 중요하냐면: {item['why_it_matters']}",
                    f"  다음에 하면 좋은 일: {item['next_step']}",
                ]
            )

    if fix_hints or report.recommended_actions:
        lines.extend(["", "다음에 하면 좋은 일:"])
        for action in report.recommended_actions or ["vib anchor --suggest"]:
            lines.append(f"- {action}")

    return "\n".join(lines) + "\n"


def render_doctor_json(envelope: Dict[str, Any]) -> str:
    return json.dumps(envelope, indent=2, ensure_ascii=False)


# === ANCHOR: DOCTOR_V2_END ===
