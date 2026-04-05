# === ANCHOR: VIB_GUARD_CMD_START ===
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TypedDict, cast

from vibelign.core.change_explainer import (
    FileSummary,
    explain_from_git,
    explain_from_mtime,
)
from vibelign.core.doctor_v2 import analyze_project_v2
from vibelign.core.guard_report import GuardReport
from vibelign.core.guard_report import combine_guard
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.core.protected_files import get_protected, is_protected
from vibelign.core.risk_analyzer import analyze_project
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


class GuardDoctorData(TypedDict):
    project_score: int
    status: str
    issues: list[object]
    recommended_actions: list[str]


class GuardExplainData(TypedDict):
    source: str
    risk_level: str
    files: list[FileSummary]
    summary: str


class GuardData(TypedDict):
    status: str
    strict: bool
    blocked: bool
    project_score: int
    project_status: str
    change_risk_level: str
    summary: str
    recommendations: list[str]
    protected_violations: list[str]
    doctor: dict[str, object] | GuardDoctorData
    explain: GuardExplainData


class GuardError(TypedDict):
    code: str
    message: str
    hint: str


class GuardEnvelope(TypedDict):
    ok: bool
    error: GuardError | None
    data: GuardData


class GuardArgs(Protocol):
    strict: bool
    since_minutes: int
    json: bool
    write_report: bool


# === ANCHOR: VIB_GUARD_CMD__GUARD_STATUS_START ===
def _guard_status(report: GuardReport) -> str:
    if report.blocked:
        return "fail"
    if report.overall_level == "WARNING":
        return "warn"
    return "pass"


# === ANCHOR: VIB_GUARD_CMD__GUARD_STATUS_END ===


# === ANCHOR: VIB_GUARD_CMD__REWRITE_RECOMMENDATIONS_START ===
def _rewrite_recommendations(recommendations: list[str]) -> list[str]:
    rewritten: list[str] = []
    for item in recommendations:
        rewritten.append(
            item.replace("`vibelign anchor`", "`vib anchor --suggest`")
            .replace("vibelign undo", "vib undo")
            .replace("vibelign", "vib")
        )
    return rewritten


# === ANCHOR: VIB_GUARD_CMD__REWRITE_RECOMMENDATIONS_END ===


# === ANCHOR: VIB_GUARD_CMD__PROTECTED_VIOLATIONS_START ===
def _protected_violations(
    root: Path, explain_files: Sequence[FileSummary]
) -> list[str]:
    protected = get_protected(root)
    if not protected:
        return []
    violations: list[str] = []
    for item in explain_files:
        path = item["path"]
        if is_protected(path, protected):
            violations.append(path)
    return violations


# === ANCHOR: VIB_GUARD_CMD__PROTECTED_VIOLATIONS_END ===


# === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_START ===
def _build_guard_envelope(
    root: Path,
    strict: bool,
    since_minutes: int,
    # === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_END ===
) -> GuardEnvelope:
    legacy_doctor = analyze_project(root, strict=strict)
    explain_report = explain_from_git(root)
    if explain_report is None:
        explain_report = explain_from_mtime(root, since_minutes=since_minutes)
    legacy_guard = combine_guard(legacy_doctor, explain_report)
    doctor_v2 = analyze_project_v2(root, strict=strict)
    violations = _protected_violations(root, explain_report.files)
    status = _guard_status(legacy_guard)
    if strict and status == "warn":
        status = "fail"
    explain_data: GuardExplainData = {
        "source": explain_report.source,
        "risk_level": explain_report.risk_level,
        "files": explain_report.files,
        "summary": explain_report.summary,
    }
    data: GuardData = {
        "status": status,
        "strict": strict,
        "blocked": legacy_guard.blocked or (strict and status == "fail"),
        "project_score": doctor_v2.project_score,
        "project_status": doctor_v2.status,
        "change_risk_level": legacy_guard.change_risk_level,
        "summary": legacy_guard.summary,
        "recommendations": _rewrite_recommendations(legacy_guard.recommendations),
        "protected_violations": violations,
        "doctor": doctor_v2.to_dict(),
        "explain": explain_data,
    }
    return {"ok": True, "error": None, "data": data}


# === ANCHOR: VIB_GUARD_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(data: GuardData) -> str:
    status_label = {
        "pass": "통과",
        "warn": "주의",
        "fail": "중지",
    }.get(str(data["status"]), str(data["status"]))
    status_hint = {
        "pass": "지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다.",
        "warn": "바로 멈출 정도는 아니지만, 먼저 한 번 더 확인하는 게 좋아요.",
        "fail": "지금은 다음 작업으로 넘어가기보다, 먼저 문제를 해결하는 게 좋아요.",
    }.get(str(data["status"]), "현재 상태를 먼저 확인해보세요.")
    lines = [
        "# VibeLign 가드 리포트",
        "",
        f"전체 상태: {status_label}",
        status_hint,
        f"엄격 모드: {'예' if data['strict'] else '아니오'}",
        f"프로젝트 점수: {data['project_score']} / 100",
        f"프로젝트 기본 상태: {data['project_status']}",
        f"최근 바뀐 내용의 위험도: {data['change_risk_level']}",
        "",
        "## 요약",
        str(data["summary"]),
        "",
    ]
    if data["protected_violations"]:
        lines.extend(["## 보호된 파일에서 바뀐 점"])
        lines.extend([f"- `{item}`" for item in data["protected_violations"]])
        lines.append("")
    lines.extend(["## 다음에 하면 좋은 일"])
    lines.extend([f"- {item}" for item in data["recommendations"]])
    lines.extend(["", "## 최근 바뀐 파일"])
    files = data["explain"]["files"]
    if files:
        lines.extend(
            [f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in files]
        )
    else:
        lines.append("- 최근에 바뀐 파일이 없습니다.")
    return "\n".join(lines) + "\n"


# === ANCHOR: VIB_GUARD_CMD__RENDER_MARKDOWN_END ===


# === ANCHOR: VIB_GUARD_CMD__UPDATE_GUARD_STATE_START ===
def _update_guard_state(meta: MetaPaths, quiet: bool = False) -> None:
    if not meta.state_path.exists():
        return
    try:
        raw_state_obj = cast(
            object, json.loads(meta.state_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        if not quiet:
            print("가드 상태 파일을 읽지 못해 마지막 실행 시간 기록은 건너뜁니다.")
        return
    if not isinstance(raw_state_obj, dict):
        return
    raw_state = cast(dict[object, object], raw_state_obj)
    state = {str(key): value for key, value in raw_state.items()}
    state["last_guard_run_at"] = datetime.now(timezone.utc).isoformat()
    try:
        _ = meta.state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError:
        if not quiet:
            print("가드 상태 파일을 저장하지 못해 마지막 실행 시간 기록은 건너뜁니다.")


# === ANCHOR: VIB_GUARD_CMD__UPDATE_GUARD_STATE_END ===


# === ANCHOR: VIB_GUARD_CMD_RUN_VIB_GUARD_START ===
def run_vib_guard(args: GuardArgs) -> None:
    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    envelope = _build_guard_envelope(
        root, strict=args.strict, since_minutes=args.since_minutes
    )
    _update_guard_state(meta, quiet=args.json)
    if args.json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("guard", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        if envelope["data"]["status"] == "fail":
            raise SystemExit(1)
        return
    markdown = _render_markdown(envelope["data"])
    print_ai_response(markdown)
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("guard", "md").write_text(markdown, encoding="utf-8")
    if envelope["data"]["status"] == "fail":
        raise SystemExit(1)


# === ANCHOR: VIB_GUARD_CMD_RUN_VIB_GUARD_END ===
# === ANCHOR: VIB_GUARD_CMD_END ===
