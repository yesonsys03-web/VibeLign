# === ANCHOR: DOCTOR_V2_START ===
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import cast

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
    stats: dict[str, object]
    issues: list[dict[str, object]]
    recommended_actions: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MCPToolConfig:
    label: str
    config_path: Path
    signals: list[Path]


@dataclass(frozen=True)
class PreparedToolConfig:
    label: str
    required_paths: list[Path]
    setup_command: str


MCP_TOOL_CONFIGS = {
    "claude": MCPToolConfig(
        label="Claude Code",
        config_path=Path(".claude/settings.json"),
        signals=[Path("CLAUDE.md"), Path("vibelign_exports/claude")],
    ),
    "cursor": MCPToolConfig(
        label="Cursor",
        config_path=Path(".cursor/mcp.json"),
        signals=[Path(".cursorrules"), Path("vibelign_exports/cursor")],
    ),
}

PREPARED_TOOL_CONFIGS = {
    "opencode": PreparedToolConfig(
        label="OpenCode",
        required_paths=[Path("OPENCODE.md"), Path("vibelign_exports/opencode")],
        setup_command="vib start --tools opencode",
    ),
    "antigravity": PreparedToolConfig(
        label="Antigravity",
        required_paths=[Path("vibelign_exports/antigravity")],
        setup_command="vib start --tools antigravity",
    ),
    "codex": PreparedToolConfig(
        label="Codex",
        required_paths=[Path("vibelign_exports/codex")],
        setup_command="vib start --tools codex",
    ),
}


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


def _issue_details(
    issues: list[str], suggestions: list[str]
) -> list[dict[str, object]]:
    details: list[dict[str, object]] = []
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


def _recommended_actions(legacy_suggestions: list[str]) -> list[str]:
    actions: list[str] = []
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


def _is_mcp_tool_enabled(root: Path, tool_name: str) -> bool:
    tool = MCP_TOOL_CONFIGS[tool_name]
    config_path = root / tool.config_path
    if config_path.exists():
        return True
    return any((root / signal).exists() for signal in tool.signals)


def _read_mcp_server_status(root: Path, tool_name: str) -> dict[str, object]:
    tool = MCP_TOOL_CONFIGS[tool_name]
    config_path = root / tool.config_path
    status: dict[str, object] = {
        "enabled": _is_mcp_tool_enabled(root, tool_name),
        "registered": False,
        "config_path": str(tool.config_path),
        "label": tool.label,
        "state": "not_configured",
    }
    if not status["enabled"]:
        status["state"] = "not_in_use"
        return status
    if not config_path.exists():
        return status
    try:
        loaded = cast(object, json.loads(config_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        status["state"] = "invalid_json"
        return status
    if not isinstance(loaded, dict):
        status["state"] = "invalid_json"
        return status
    loaded_dict = cast(dict[str, object], loaded)
    mcp_servers = loaded_dict.get("mcpServers")
    if not isinstance(mcp_servers, dict):
        status["state"] = "missing_server"
        return status
    if "vibelign" not in mcp_servers:
        status["state"] = "missing_server"
        return status
    status["registered"] = True
    status["state"] = "registered"
    return status


def _collect_mcp_status(root: Path) -> dict[str, dict[str, object]]:
    return {
        tool_name: _read_mcp_server_status(root, tool_name)
        for tool_name in MCP_TOOL_CONFIGS
    }


def _collect_prepared_tool_status(root: Path) -> dict[str, dict[str, object]]:
    status_map: dict[str, dict[str, object]] = {}
    for tool_name, tool in PREPARED_TOOL_CONFIGS.items():
        missing = [
            str(path) for path in tool.required_paths if not (root / path).exists()
        ]
        any_present = any((root / path).exists() for path in tool.required_paths)
        if not any_present:
            status_map[tool_name] = {
                "enabled": False,
                "ready": False,
                "label": tool.label,
                "state": "not_in_use",
                "missing": missing,
            }
            continue
        status_map[tool_name] = {
            "enabled": True,
            "ready": not missing,
            "label": tool.label,
            "state": "prepared" if not missing else "partial",
            "missing": missing,
        }
    return status_map


def _append_mcp_issues(
    issues: list[str], suggestions: list[str], mcp_status: dict[str, dict[str, object]]
) -> None:
    for tool_name, status in mcp_status.items():
        if not status["enabled"] or status["registered"]:
            continue
        config_path = status["config_path"]
        label = status["label"]
        if status["state"] == "invalid_json":
            issues.append(f"{config_path} 파일을 읽을 수 없어요")
            suggestions.append(
                f"`vib start --tools {tool_name}` 를 다시 실행하면 {label} MCP 설정을 자동으로 복구해요"
            )
            continue
        issues.append(f"{config_path}에 vibelign MCP 등록이 없어요")
        suggestions.append(
            f"`vib start --tools {tool_name}` 를 실행하면 {label}에 vibelign MCP를 자동 등록해요"
        )


def _append_prepared_tool_issues(
    issues: list[str],
    suggestions: list[str],
    prepared_status: dict[str, dict[str, object]],
) -> None:
    for tool_name, status in prepared_status.items():
        if not status["enabled"] or status["ready"]:
            continue
        raw_missing = status.get("missing", [])
        missing_items = (
            cast(list[object], raw_missing) if isinstance(raw_missing, list) else []
        )
        missing = ", ".join(str(path) for path in missing_items)
        issues.append(f"{status['label']} 준비 파일이 일부 없어요 ({missing})")
        suggestions.append(
            f"`{PREPARED_TOOL_CONFIGS[tool_name].setup_command}` 를 다시 실행하면 {status['label']} 준비 파일을 자동으로 채워줘요"
        )


def _render_mcp_lines(stats: dict[str, object]) -> list[str]:
    raw = stats.get("mcp_status")
    if not isinstance(raw, dict):
        return []
    raw_statuses = cast(dict[str, object], raw)
    lines: list[str] = []
    for tool_name in MCP_TOOL_CONFIGS:
        raw_status = raw_statuses.get(tool_name)
        if not isinstance(raw_status, dict):
            continue
        status = cast(dict[str, object], raw_status)
        if not status.get("enabled"):
            continue
        label = str(status.get("label") or tool_name)
        state = status.get("state")
        if state == "registered":
            lines.append(f"{label} MCP: 연결됨")
        elif state == "invalid_json":
            lines.append(f"{label} MCP: 설정 파일 확인 필요")
        else:
            lines.append(f"{label} MCP: 아직 등록되지 않음")
    return lines


def _render_prepared_tool_lines(stats: dict[str, object]) -> list[str]:
    raw = stats.get("prepared_tool_status")
    if not isinstance(raw, dict):
        return []
    raw_statuses = cast(dict[str, object], raw)
    lines: list[str] = []
    for tool_name in PREPARED_TOOL_CONFIGS:
        raw_status = raw_statuses.get(tool_name)
        if not isinstance(raw_status, dict):
            continue
        status = cast(dict[str, object], raw_status)
        if not status.get("enabled"):
            continue
        label = str(status.get("label") or tool_name)
        if status.get("ready"):
            lines.append(f"{label}: 준비됨")
        else:
            lines.append(f"{label}: 준비 파일 확인 필요")
    return lines


def analyze_project_v2(
    root: Path, strict: bool = False, force: bool = False
) -> DoctorV2Report:
    from vibelign.core.analysis_cache import load_analysis_cache, save_analysis_cache
    from vibelign.core.meta_paths import MetaPaths
    from datetime import datetime, timezone

    meta = MetaPaths(root)
    cached = load_analysis_cache(meta.analysis_cache_path, root, force=force)
    if cached is not None:
        cached_score = cached.get("project_score")
        cached_status = cached.get("status")
        cached_coverage = cached.get("anchor_coverage")
        cached_stats = cast(dict[str, object], cached.get("stats", {}))
        cached_issues = cast(list[dict[str, object]], cached.get("issues", []))
        cached_actions = cast(list[str], cached.get("recommended_actions", []))
        return DoctorV2Report(
            project_score=cached_score if isinstance(cached_score, int) else 0,
            status=cached_status if isinstance(cached_status, str) else "High Risk",
            anchor_coverage=cached_coverage if isinstance(cached_coverage, int) else 0,
            stats=cached_stats,
            issues=cached_issues,
            recommended_actions=cached_actions,
        )

    legacy = analyze_project(root, strict=strict)
    project_score = max(0, 100 - (legacy.score * 4))
    status = _build_status(project_score)
    coverage = _anchor_coverage(root)
    stats = dict(legacy.stats)
    project_map, project_map_error = load_project_map(root)
    mcp_status = _collect_mcp_status(root)
    prepared_tool_status = _collect_prepared_tool_status(root)
    stats["anchor_coverage"] = coverage
    stats["legacy_penalty"] = legacy.score
    stats["project_map_loaded"] = project_map is not None
    stats["mcp_status"] = mcp_status
    stats["prepared_tool_status"] = prepared_tool_status
    issues = list(legacy.issues)
    suggestions = list(legacy.suggestions)
    if project_map is not None:
        stats["project_map_file_count"] = project_map.file_count
        stats["project_map_generated_at"] = project_map.generated_at
    elif project_map_error == "unsupported_project_map_schema":
        issues.append(".vibelign/project_map.json 파일의 버전이 맞지 않아요")
        suggestions.append("vib start 를 다시 실행하면 자동으로 고쳐져요")
    elif project_map_error == "invalid_project_map":
        issues.append(".vibelign/project_map.json 파일을 읽을 수 없습니다")
        suggestions.append("vib start 를 다시 실행하면 자동으로 고쳐져요")
    _append_mcp_issues(issues, suggestions, mcp_status)
    _append_prepared_tool_issues(issues, suggestions, prepared_tool_status)
    report = DoctorV2Report(
        project_score=project_score,
        status=status,
        anchor_coverage=coverage,
        stats=stats,
        issues=_issue_details(issues, suggestions),
        recommended_actions=_recommended_actions(suggestions),
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    meta.ensure_vibelign_dir()
    save_analysis_cache(meta.analysis_cache_path, root, report.to_dict(), generated_at)
    return report


def build_doctor_envelope(root: Path, strict: bool = False) -> dict[str, object]:
    report = analyze_project_v2(root, strict=strict)
    return {"ok": True, "error": None, "data": report.to_dict()}


def _score_grade(score: int) -> str:
    """점수를 학점 비유로 변환."""
    if score >= 90:
        return "A+ 학점이에요"
    if score >= 85:
        return "A 학점 정도예요"
    if score >= 80:
        return "B+ 학점 정도예요"
    if score >= 70:
        return "B 학점 정도예요"
    if score >= 60:
        return "C 학점 정도예요"
    if score >= 50:
        return "D 학점 정도예요"
    return "아직 많이 부족해요"


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
    grade = _score_grade(report.project_score)
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "VibeLign 프로젝트 상태 보기",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"프로젝트 점수: {report.project_score} / 100 ({grade})",
        f"현재 상태: {report.status}",
        status_line,
        f"AI 안전 구역 표시된 파일 비율: {report.anchor_coverage}%",
    ]
    lines.extend(_render_mcp_lines(report.stats))
    lines.extend(_render_prepared_tool_lines(report.stats))
    lines.extend(["", "먼저 보면 좋은 점:"])
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


def render_doctor_json(envelope: dict[str, object]) -> str:
    return json.dumps(envelope, indent=2, ensure_ascii=False)


# === ANCHOR: DOCTOR_V2_END ===
