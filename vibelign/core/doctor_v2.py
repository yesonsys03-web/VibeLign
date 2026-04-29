# === ANCHOR: DOCTOR_V2_START ===
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import cast

from vibelign.core.anchor_tools import extract_anchors, insert_auto_anchors
from vibelign.core.project_map import load_project_map
from vibelign.core.project_scan import iter_source_files, safe_read_text
from vibelign.core.risk_analyzer import analyze_project
from vibelign.core.structure_policy import COMMON_IGNORED_DIRS, is_trivial_package_init


STATUS_LEVELS = [
    (85, "Safe"),
    (70, "Good"),
    (50, "Caution"),
    (30, "Risky"),
    (0, "High Risk"),
]

ISSUE_PENALTIES: dict[str, dict[str, float]] = {
    "anchor": {"low": 0.0, "medium": 1.0, "high": 2.0},
    "structure": {"low": 0.5, "medium": 1.5, "high": 3.0},
    "metadata": {"low": 0.5, "medium": 1.0, "high": 2.0},
    "mcp": {"low": 1.0, "medium": 2.0, "high": 4.0},
}


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
    # priority order; absolute path = global config, relative path = root-relative
    config_paths: list[Path]
    signals: list[Path]
    config_format: str = "json"  # "json" or "toml"
    servers_key: str = "mcpServers"  # JSON top-level key holding servers dict


@dataclass(frozen=True)
class PreparedToolConfig:
    label: str
    required_paths: list[Path]
    setup_command: str


MCP_TOOL_CONFIGS = {
    "claude": MCPToolConfig(
        label="Claude Code",
        # FIXED: Claude Code reads project-scope .mcp.json, not .claude/settings.json
        config_paths=[Path(".mcp.json")],
        signals=[Path("CLAUDE.md"), Path("vibelign_exports/claude")],
    ),
    "cursor": MCPToolConfig(
        label="Cursor",
        config_paths=[Path(".cursor/mcp.json")],
        signals=[Path(".cursorrules"), Path("vibelign_exports/cursor")],
    ),
    "opencode": MCPToolConfig(
        label="OpenCode",
        # project (root/opencode.json) precedes global (~/.config/opencode/opencode.json)
        config_paths=[
            Path("opencode.json"),
            Path.home() / ".config" / "opencode" / "opencode.json",
        ],
        signals=[Path("OPENCODE.md"), Path("vibelign_exports/opencode")],
        servers_key="mcp",
    ),
    "antigravity": MCPToolConfig(
        label="Antigravity",
        config_paths=[Path.home() / ".gemini" / "antigravity" / "mcp_config.json"],
        signals=[Path("vibelign_exports/antigravity")],
    ),
    "codex": MCPToolConfig(
        label="Codex",
        config_paths=[Path.home() / ".codex" / "config.toml"],
        signals=[Path("vibelign_exports/codex")],
        config_format="toml",
    ),
}

# 5개 도구 모두 MCP 자동 등록되도록 통합 → PREPARED_TOOL_CONFIGS 는 비어있음.
# (관련 검사 로직은 빈 dict 를 안전하게 반복하도록 그대로 둔다.)
PREPARED_TOOL_CONFIGS: dict[str, PreparedToolConfig] = {}
FIX_ANCHOR_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}


def _fix_anchor_relpath(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _fix_anchor_requested_paths(root: Path, paths: list[str]) -> list[Path]:
    requested: list[Path] = []
    resolved_root = root.resolve()
    for raw_path in paths:
        normalized_path = raw_path.replace("\\", "/")
        candidate = (root / normalized_path).resolve()
        try:
            _ = candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"project-outside path: {raw_path}") from exc
        if candidate.is_file() and candidate.suffix.lower() in FIX_ANCHOR_EXTENSIONS:
            requested.append(candidate)
    return requested


def _iter_fix_anchor_candidates(root: Path, paths: list[str] | None = None) -> list[Path]:
    if paths:
        return _fix_anchor_requested_paths(root, paths)
    ignored = {part.lower() for part in COMMON_IGNORED_DIRS} | {".vibelign", "docs"}
    candidates: list[Path] = []
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part.lower() in ignored for part in relative_parts):
            continue
        if path.is_symlink():
            continue
        try:
            resolved_path = path.resolve()
            _ = resolved_path.relative_to(resolved_root)
        except (OSError, ValueError):
            continue
        if not path.is_file() or path.suffix.lower() not in FIX_ANCHOR_EXTENSIONS:
            continue
        if is_trivial_package_init(path, safe_read_text(path)):
            continue
        candidates.append(path)
    return candidates


def fix_anchors_action(
    root: Path, paths: list[str] | None = None, dry_run: bool = False
) -> dict[str, object]:
    from vibelign.core.protected_files import get_protected, is_protected

    protected = get_protected(root)
    anchored: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    for path in _iter_fix_anchor_candidates(root, paths):
        rel = _fix_anchor_relpath(root, path)
        try:
            if is_protected(rel, protected):
                skipped.append(f"{rel} (protected)")
                continue
            if extract_anchors(path):
                skipped.append(f"{rel} (already anchored)")
                continue
            if dry_run:
                anchored.append(rel)
                continue
            if insert_auto_anchors(path):
                anchored.append(rel)
            else:
                skipped.append(f"{rel} (unsupported or unchanged)")
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
    return {"dry_run": dry_run, "anchored": anchored, "skipped": skipped, "errors": errors}


def _build_status(score: int) -> str:
    for threshold, label in STATUS_LEVELS:
        if score >= threshold:
            return label
    return "High Risk"


def _project_score_from_issues(issues: list[dict[str, object]]) -> int:
    total_penalty = 0.0
    for issue in issues:
        category = str(issue.get("category", "metadata"))
        severity = str(issue.get("severity", "low"))
        category_penalties = ISSUE_PENALTIES.get(category, ISSUE_PENALTIES["metadata"])
        total_penalty += category_penalties.get(severity, category_penalties["medium"])
    return max(0, 100 - round(total_penalty))


def _anchor_coverage(root: Path) -> int:
    source_files = [
        path
        for path in iter_source_files(root)
        if not is_trivial_package_init(path, safe_read_text(path))
    ]
    if not source_files:
        return 100
    covered = sum(1 for path in source_files if extract_anchors(path))
    return round((covered / len(source_files)) * 100)


def _issue_details(issues: list[dict[str, object]]) -> list[dict[str, object]]:
    details: list[dict[str, object]] = []
    for issue in issues:
        found = str(issue.get("found", ""))
        next_step = str(issue.get("next_step", "관련 파일을 직접 열어서 확인해보세요."))
        category = str(issue.get("category", "metadata"))
        severity = str(issue.get("severity", "low"))
        recommended_command = issue.get("recommended_command")
        can_auto_fix = bool(issue.get("can_auto_fix", False))
        auto_fix_label = issue.get("auto_fix_label")
        path = issue.get("path")

        if category == "anchor" and recommended_command is None:
            recommended_command = "vib doctor --fix"
            can_auto_fix = True
            auto_fix_label = "앵커 자동 추가"

        details.append(
            {
                "found": found,
                "why_it_matters": issue.get(
                    "why_it_matters",
                    f"{found} 때문에 AI가 엉뚱한 곳까지 건드리거나 코드를 더 꼬이게 만들 수 있어요.",
                ),
                "next_step": next_step,
                "path": path,
                "severity": severity,
                "category": category,
                "recommended_command": recommended_command,
                "can_auto_fix": can_auto_fix,
                "auto_fix_label": auto_fix_label,
            }
        )
    return details


def _recommended_actions(issues: list[dict[str, object]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        command = issue.get("recommended_command")
        next_step = issue.get("next_step")
        action = str(command or next_step or "")
        if action and action not in seen:
            seen.add(action)
            actions.append(action)
    return actions[:6]


def _resolve_config_path(root: Path, p: Path) -> Path:
    """Absolute path 는 그대로(글로벌 설정), relative 는 root 기준으로 풀어준다."""
    return p if p.is_absolute() else root / p


def _humanize_config_path(path: Path, root: Path) -> str:
    """사용자 출력용으로 root 상대 또는 ~/ 단축 경로."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        pass
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


def _check_vibelign_in_config(config_path: Path, tool: MCPToolConfig) -> str:
    """단일 설정 파일에서 vibelign MCP 등록 여부 확인.

    반환값: 'registered' | 'missing_server' | 'invalid_json'
    """
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return "missing_server"

    if tool.config_format == "toml":
        # Codex: TOML 의 [mcp_servers.vibelign] 섹션 헤더 존재 여부.
        return (
            "registered"
            if "[mcp_servers.vibelign]" in text
            else "missing_server"
        )

    try:
        loaded = cast(object, json.loads(text))
    except json.JSONDecodeError:
        return "invalid_json"
    if not isinstance(loaded, dict):
        return "invalid_json"
    loaded_dict = cast(dict[str, object], loaded)
    servers = loaded_dict.get(tool.servers_key)
    if not isinstance(servers, dict):
        return "missing_server"
    return "registered" if "vibelign" in servers else "missing_server"


def _is_mcp_tool_enabled(root: Path, tool_name: str) -> bool:
    tool = MCP_TOOL_CONFIGS[tool_name]
    # 프로젝트 스코프 config (relative path) 만 "이 프로젝트에서 쓰는 도구" 신호로 간주.
    # 글로벌 config (absolute path) 는 사용자 일반 설정이므로 enable 신호 아님.
    for cp in tool.config_paths:
        if not cp.is_absolute() and (root / cp).exists():
            return True
    return any((root / signal).exists() for signal in tool.signals)


def _read_mcp_server_status(root: Path, tool_name: str) -> dict[str, object]:
    tool = MCP_TOOL_CONFIGS[tool_name]
    primary_path = _resolve_config_path(root, tool.config_paths[0])
    status: dict[str, object] = {
        "enabled": _is_mcp_tool_enabled(root, tool_name),
        "registered": False,
        "config_path": _humanize_config_path(primary_path, root),
        "label": tool.label,
        "state": "not_configured",
    }
    if not status["enabled"]:
        status["state"] = "not_in_use"
        return status

    # 후보 경로들을 우선순위대로 검사 — vibelign 등록된 첫 번째를 기록.
    invalid_seen: Path | None = None
    any_exists = False
    for cp in tool.config_paths:
        resolved = _resolve_config_path(root, cp)
        if not resolved.exists():
            continue
        any_exists = True
        result = _check_vibelign_in_config(resolved, tool)
        if result == "registered":
            status["config_path"] = _humanize_config_path(resolved, root)
            status["registered"] = True
            status["state"] = "registered"
            return status
        if result == "invalid_json" and invalid_seen is None:
            invalid_seen = resolved

    if invalid_seen is not None:
        status["config_path"] = _humanize_config_path(invalid_seen, root)
        status["state"] = "invalid_json"
        return status

    # enabled (signals 있음) 인데 config 파일이 아예 없으면 not_configured,
    # 파일은 있는데 vibelign 항목만 없으면 missing_server (의미 보존).
    status["state"] = "missing_server" if any_exists else "not_configured"
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
    issues: list[dict[str, object]], mcp_status: dict[str, dict[str, object]]
) -> None:
    for tool_name, status in mcp_status.items():
        if not status["enabled"] or status["registered"]:
            continue
        config_path = str(status["config_path"])
        label = str(status["label"])
        if status["state"] == "invalid_json":
            issues.append(
                {
                    "found": f"{config_path} 파일을 읽을 수 없어요",
                    "next_step": f"{label} MCP 설정 파일을 다시 만들어야 해요.",
                    "path": config_path,
                    "category": "mcp",
                    "severity": "high",
                    "recommended_command": f"vib start --tools {tool_name}",
                    "can_auto_fix": False,
                    "auto_fix_label": None,
                }
            )
            continue
        issues.append(
            {
                "found": f"{config_path}에 vibelign MCP 등록이 없어요",
                "next_step": f"`vib start --tools {tool_name}` 를 실행하면 {label}에 vibelign MCP를 자동 등록해요",
                "path": config_path,
                "category": "mcp",
                "severity": "high",
                "recommended_command": f"vib start --tools {tool_name}",
                "can_auto_fix": False,
                "auto_fix_label": None,
            }
        )


def _append_prepared_tool_issues(
    issues: list[dict[str, object]],
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
        setup_command = PREPARED_TOOL_CONFIGS[tool_name].setup_command
        issues.append(
            {
                "found": f"{status['label']} 준비 파일이 일부 없어요 ({missing})",
                "next_step": f"`{setup_command}` 를 다시 실행하면 {status['label']} 준비 파일을 자동으로 채워줘요",
                "path": None,
                "category": "metadata",
                "severity": "medium",
                "recommended_command": setup_command,
                "can_auto_fix": False,
                "auto_fix_label": None,
            }
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


def _collect_checkpoint_engine_status(root: Path) -> dict[str, object]:
    from vibelign.core.meta_paths import MetaPaths

    state_path = MetaPaths(root).state_path
    status: dict[str, object] = {
        "engine_used": "unknown",
        "last_fallback_reason": None,
    }
    try:
        loaded = cast(object, json.loads(state_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return status
    if not isinstance(loaded, dict):
        return status
    state = cast(dict[str, object], loaded)
    engine_used = state.get("engine_used")
    fallback_reason = state.get("last_fallback_reason")
    if isinstance(engine_used, str) and engine_used:
        status["engine_used"] = engine_used
    if isinstance(fallback_reason, str) and fallback_reason:
        status["last_fallback_reason"] = fallback_reason
    return status


def _render_checkpoint_engine_lines(stats: dict[str, object]) -> list[str]:
    raw = stats.get("checkpoint_engine_status")
    if not isinstance(raw, dict):
        return []
    status = cast(dict[str, object], raw)
    engine_used = str(status.get("engine_used") or "unknown")
    fallback_reason = status.get("last_fallback_reason")
    if engine_used == "rust":
        return ["Checkpoint engine: Rust/SQLite 활성"]
    if engine_used == "python":
        if isinstance(fallback_reason, str) and fallback_reason:
            return [f"Checkpoint engine: Python fallback 활성 ({fallback_reason})"]
        return ["Checkpoint engine: Python fallback 활성"]
    return ["Checkpoint engine: 아직 실행 기록 없음"]


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
        cached_stats["checkpoint_engine_status"] = _collect_checkpoint_engine_status(root)
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
    stats["checkpoint_engine_status"] = _collect_checkpoint_engine_status(root)
    issues: list[dict[str, object]] = list(legacy.issues)
    if project_map is not None:
        stats["project_map_file_count"] = project_map.file_count
        stats["project_map_generated_at"] = project_map.generated_at
    elif project_map_error == "unsupported_project_map_schema":
        issues.append(
            {
                "found": ".vibelign/project_map.json 파일의 버전이 맞지 않아요",
                "next_step": "vib start 를 다시 실행하면 자동으로 고쳐져요",
                "path": ".vibelign/project_map.json",
                "category": "metadata",
                "severity": "medium",
                "check_type": "unsupported_project_map_schema",
            }
        )
    elif project_map_error == "invalid_project_map":
        issues.append(
            {
                "found": ".vibelign/project_map.json 파일을 읽을 수 없습니다",
                "next_step": "vib start 를 다시 실행하면 자동으로 고쳐져요",
                "path": ".vibelign/project_map.json",
                "category": "metadata",
                "severity": "medium",
                "check_type": "invalid_project_map",
            }
        )
    _append_mcp_issues(issues, mcp_status)
    _append_prepared_tool_issues(issues, prepared_tool_status)
    project_score = _project_score_from_issues(issues)
    status = _build_status(project_score)
    detailed_issues = _issue_details(issues)
    report = DoctorV2Report(
        project_score=project_score,
        status=status,
        anchor_coverage=coverage,
        stats=stats,
        issues=detailed_issues,
        recommended_actions=_recommended_actions(detailed_issues),
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
    lines.extend(_render_checkpoint_engine_lines(report.stats))
    lines.extend(["", "먼저 보면 좋은 점:"])
    if report.issues:
        for index, item in enumerate(report.issues, 1):
            lines.append(f"{index}. {item['found']}")
    else:
        lines.append("1. 지금 바로 걱정할 큰 구조 문제는 보이지 않습니다.")

    if detailed and report.issues:
        lines.extend(["", "자세히 보면:"])
        for item in report.issues:
            sev = str(item.get("severity", "low")).upper()
            cat = str(item.get("category", "metadata"))
            lines.append(f"- [{sev}][{cat}] {item['found']}")
            lines.append(f"  왜 중요하냐면: {item['why_it_matters']}")
            lines.append(f"  다음에 하면 좋은 일: {item['next_step']}")
            if item.get("recommended_command"):
                lines.append(f"  추천 명령: {item['recommended_command']}")
            lines.append(
                "  자동 수정: 가능" if item.get("can_auto_fix") else "  자동 수정: 불가"
            )

    if fix_hints or report.recommended_actions:
        lines.extend(["", "다음에 하면 좋은 일:"])
        for action in report.recommended_actions or ["vib anchor --suggest"]:
            lines.append(f"- {action}")

    return "\n".join(lines) + "\n"


def render_doctor_json(envelope: dict[str, object]) -> str:
    return json.dumps(envelope, indent=2, ensure_ascii=False)


# === ANCHOR: DOCTOR_V2_END ===
