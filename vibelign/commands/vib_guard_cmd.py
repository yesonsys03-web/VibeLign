# === ANCHOR: VIB_GUARD_CMD_START ===
import json
import re
import subprocess
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TypedDict, cast

from vibelign.core.anchor_tools import COMMENT_PREFIX
from vibelign.core.change_explainer import (
    ChangeItem,
    ExplainReport,
    FileSummary,
    classify_path,
    explain_from_git,
    explain_from_mtime,
    risk_from_items,
)
from vibelign.core.doctor_v2 import analyze_project_v2
from vibelign.core.guard_report import GuardReport
from vibelign.core.guard_report import _risk_label, combine_guard
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import enrich_change_kind, load_project_map
from vibelign.core.project_root import resolve_project_root
from vibelign.core.protected_files import get_protected, is_protected
from vibelign.core.risk_analyzer import analyze_project
from vibelign.core.structure_policy import (
    WINDOWS_SUBPROCESS_FLAGS,
    classify_structure_path,
    small_fix_line_threshold,
)
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
    # 사람용 3단 판정(pass|prepare|stop) — status/blocked 는 기계 게이트로 의미 유지(2026-06-12)
    verdict: str
    strict: bool
    blocked: bool
    project_score: int
    project_status: str
    change_risk_level: str
    summary: str
    recommendations: list[str]
    protected_violations: list[str]
    anchor_violations: list[str]
    doctor: dict[str, object] | GuardDoctorData
    explain: GuardExplainData
    planning: "PlanningData"


class PlanningData(TypedDict):
    status: str
    strict: bool
    active_plan_id: str | None
    summary: str
    changed_files: list[str]
    required_reasons: list[str]
    deviations: list[str]
    exempt_reasons: list[str]


class FileChangeDetails(TypedDict):
    added_lines: int
    ranges: list[tuple[int, int]]


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


_PLAN_REQUIRED_RECOMMENDATION = (
    "구조 영향 가능성이 높다면 먼저 `vib plan \"작업 내용\"` 또는 GUI 기획방에서 계획을 정리하세요."
)
_ANCHOR_REQUIRED_RECOMMENDATION = "신규 소스 파일에는 먼저 앵커를 추가하세요. `vib anchor --auto` 또는 `vib watch --auto-fix`를 사용할 수 있어요."
_ANCHOR_PATTERN = re.compile(r"ANCHOR:\s*[A-Z0-9_]+_(START|END)")
_SOURCE_EXTENSIONS = set(COMMENT_PREFIX.keys())


def _planning_message(status: str) -> str:
    return {
        "planning_exempt": "현재 변경은 별도 기획 없이 진행 가능한 범위입니다.",
        "planning_required": "구조 영향 가능성이 높은 변경이 감지되었습니다. 먼저 `vib plan \"작업 내용\"` 또는 GUI 기획방에서 계획을 정리하세요.",
        "fail": "구조 영향 검증에 실패했습니다.",
        "pass": "구조 영향 검사를 통과했습니다.",
    }.get(status, "구조 영향 상태를 확인하세요.")


def _planning_exempt_summary(reasons: Sequence[str]) -> str:
    if "docs_only" in reasons:
        return "현재 변경은 문서만 수정하므로 별도 기획 없이 진행 가능한 범위입니다."
    if "tests_only" in reasons:
        return "현재 변경은 테스트만 수정하므로 별도 기획 없이 진행 가능한 범위입니다."
    if "config_only" in reasons:
        return "현재 변경은 config만 수정하므로 별도 기획 없이 진행 가능한 범위입니다."
    if "small_single_file_fix" in reasons:
        return "현재 변경은 소규모 단일 파일 수정이므로 별도 기획 없이 진행 가능한 범위입니다."
    if "no_changed_files" in reasons:
        return "현재 변경 파일이 없어 별도 기획 없이 진행 가능한 상태입니다."
    return "현재 변경은 별도 기획 없이 진행 가능한 범위입니다."


def _planning_guard_level(status: str, strict: bool) -> str:
    if status in {"fail"}:
        return "fail"
    if status == "planning_required":
        return "fail" if strict else "warn"
    return "pass"


def _merge_status(current: str, planning_level: str) -> str:
    rank = {"pass": 0, "warn": 1, "fail": 2}
    return (
        planning_level
        if rank.get(planning_level, 0) > rank.get(current, 0)
        else current
    )


def _run_guard_git(root: Path, args: Sequence[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        return proc.returncode == 0, proc.stdout if proc.returncode == 0 else (
            proc.stderr or proc.stdout
        )
    except Exception as exc:
        return False, str(exc)


def _decode_guard_git_path(path: str) -> str:
    import unicodedata

    if not (path.startswith('"') and path.endswith('"')):
        return unicodedata.normalize("NFC", path)
    path = path[1:-1]
    buf = bytearray()
    index = 0
    while index < len(path):
        if (
            path[index] == "\\"
            and index + 3 < len(path)
            and path[index + 1 : index + 4].isdigit()
        ):
            buf.append(int(path[index + 1 : index + 4], 8))
            index += 4
        else:
            buf.extend(path[index].encode("utf-8"))
            index += 1
    try:
        return unicodedata.normalize("NFC", buf.decode("utf-8"))
    except UnicodeDecodeError:
        return path


def _status_to_change(status_code: str) -> str:
    return {
        "M": "modified",
        "A": "added",
        "D": "deleted",
        "R": "renamed",
        "??": "untracked",
    }.get(status_code, "changed")


def _guard_explain_report(root: Path, since_minutes: int) -> ExplainReport:
    staged_ok, staged_out = _run_guard_git(
        root, ["diff", "--cached", "--name-status", "--", "."]
    )
    if staged_ok and staged_out.strip():
        project_map, _project_map_error = load_project_map(root)
        items: list[ChangeItem] = []
        for line in staged_out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status_code = parts[0].strip()[:1]
            rel = parts[-1].strip()
            decoded = _decode_guard_git_path(rel)
            items.append(
                ChangeItem(
                    decoded,
                    _status_to_change(status_code),
                    enrich_change_kind(project_map, decoded, classify_path(decoded)),
                )
            )
        return ExplainReport(
            "git-staged",
            f"staged 변경 {len(items)}개를 기준으로 검사했어요.",
            ["staged 변경을 우선 검사했습니다."],
            ["working tree 변경이 있어도 staged 기준으로 planning을 계산합니다."],
            risk_from_items(items),
            "staged 변경을 먼저 정리하거나 새 plan을 생성하세요.",
            [
                {"path": item.path, "status": item.status, "kind": item.kind}
                for item in items
            ],
        )
    explain_report = explain_from_git(root)
    if explain_report is not None:
        return explain_report
    return explain_from_mtime(root, since_minutes=since_minutes)


def _parse_diff_line_ranges(diff_text: str) -> tuple[int, list[tuple[int, int]]]:
    added_lines = 0
    ranges: list[tuple[int, int]] = []
    hunk_pattern = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in diff_text.splitlines():
        match = hunk_pattern.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count > 0:
            ranges.append((start, start + count - 1))
            added_lines += count
    return added_lines, ranges


def _file_change_details(
    root: Path, item: FileSummary, *, staged_only: bool
) -> FileChangeDetails:
    rel_path = str(item["path"])
    status = str(item["status"])
    path = root / rel_path
    if status in {"added", "untracked"}:
        if staged_only:
            ok, staged_content = _run_guard_git(root, ["show", f":{rel_path}"])
            if ok:
                line_count = len(staged_content.splitlines())
                return {
                    "added_lines": line_count,
                    "ranges": [(1, line_count)] if line_count else [],
                }
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            line_count = 0
        return {
            "added_lines": line_count,
            "ranges": [(1, line_count)] if line_count else [],
        }
    diff_args = ["diff", "--unified=0"]
    if staged_only:
        diff_args.append("--cached")
    else:
        diff_args.append("HEAD")
    diff_args.extend(["--", rel_path])
    ok, diff = _run_guard_git(root, diff_args)
    if not ok:
        return {"added_lines": 0, "ranges": []}
    added_lines, ranges = _parse_diff_line_ranges(diff)
    return {"added_lines": added_lines, "ranges": ranges}


def _new_file_text(root: Path, rel_path: str, *, staged_only: bool) -> str:
    if staged_only:
        ok, staged_content = _run_guard_git(root, ["show", f":{rel_path}"])
        if ok:
            return staged_content
    try:
        return (root / rel_path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _anchor_violations(
    root: Path, explain_files: Sequence[FileSummary], *, staged_only: bool
) -> list[str]:
    violations: list[str] = []
    for item in explain_files:
        rel_path = str(item["path"])
        if classify_structure_path(rel_path) != "production":
            continue
        if str(item["status"]) not in {"added", "untracked"}:
            continue
        if Path(rel_path).suffix.lower() not in _SOURCE_EXTENSIONS:
            continue
        if _ANCHOR_PATTERN.search(
            _new_file_text(root, rel_path, staged_only=staged_only)
        ):
            continue
        violations.append(rel_path)
    return violations


def _planning_data(
    root: Path,
    meta: MetaPaths,
    strict: bool,
    explain_files: Sequence[FileSummary],
    explain_source: str,
) -> PlanningData:
    threshold = small_fix_line_threshold(meta)
    staged_only = explain_source == "git-staged"
    changed_files = [str(item["path"]) for item in explain_files]
    if not changed_files:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_exempt_summary(["no_changed_files"]),
            "changed_files": [],
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["no_changed_files"],
        }

    production_items = [
        item
        for item in explain_files
        if classify_structure_path(str(item["path"])) == "production"
    ]
    relevant_items = [
        item
        for item in explain_files
        if classify_structure_path(str(item["path"])) != "meta"
    ]
    new_production_items = [
        item
        for item in production_items
        if str(item["status"]) in {"added", "untracked"}
    ]
    docs_only = (
        all(
            classify_structure_path(str(item["path"])) == "docs"
            for item in relevant_items
        )
        if relevant_items
        else False
    )
    tests_only = (
        all(
            classify_structure_path(str(item["path"])) == "tests"
            for item in relevant_items
        )
        if relevant_items
        else False
    )
    config_only = (
        all(
            classify_structure_path(str(item["path"])) == "config"
            for item in relevant_items
        )
        if relevant_items
        else False
    )
    small_fix_candidate = False
    if len(production_items) == 1 and len(relevant_items) == 1:
        item = production_items[0]
        if str(item["status"]) not in {"deleted", "renamed"}:
            details = _file_change_details(root, item, staged_only=staged_only)
            small_fix_candidate = details["added_lines"] <= threshold

    exempt_reasons: list[str] = []
    if docs_only:
        exempt_reasons.append("docs_only")
    if tests_only:
        exempt_reasons.append("tests_only")
    if config_only:
        exempt_reasons.append("config_only")
    if exempt_reasons:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_exempt_summary(exempt_reasons),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": exempt_reasons,
        }

    if small_fix_candidate:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_exempt_summary(["small_single_file_fix"]),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["small_single_file_fix"],
        }

    required_reasons: list[str] = []
    if new_production_items:
        required_reasons.append("new_production_file")
    if len(production_items) >= 2:
        required_reasons.append("multi_file_production_edit")

    if not required_reasons:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_exempt_summary(exempt_reasons or ["default_exempt"]),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": exempt_reasons or ["default_exempt"],
        }

    return {
        "status": "planning_required",
        "strict": strict,
        "active_plan_id": None,
        "summary": f"{_planning_message('planning_required')} 이유: {', '.join(required_reasons)}",
        "changed_files": changed_files,
        "required_reasons": required_reasons,
        "deviations": [],
        "exempt_reasons": exempt_reasons,
    }


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


def _envelope_summary(
    doctor_v2_status: str, doctor_v2_score: int, legacy_guard: GuardReport
) -> str:
    """guard 요약 모순 수정(2026-06-12, 알람앱 트라이얼에서 발견).

    헤더의 점수·상태는 doctor v2(예: Safe·90점)인데 요약의 '기본 상태'는 legacy v1
    level("위험")을 서술해 한 화면에서 서로 모순됐다. 기본 상태는 헤더와 같은 v2
    기준으로 맞춘다. 판단("멈춤/준비/통과")은 _verdict_lead 가 첫 줄로 말하므로
    여기서는 사실만 서술한다.
    """
    return (
        f"프로젝트 기본 상태는 {doctor_v2_status}({doctor_v2_score}점), "
        f"최근 바뀐 내용의 위험도는 {_risk_label(legacy_guard.change_risk_level)}입니다."
    )


def _verdict_tier(
    protected_violations: list[str],
    anchor_violations: list[str],
    change_risk_level: str,
    planning_level: str,
    status: str,
) -> str:
    """사람용 3단 판정 — 위반 채널과 위생 채널의 분리(2026-06-12 결정).

    배경: legacy v1 감점은 위생 항목(앵커 미설정 2점/파일 등)을 상한 없이 합산해
    임계만 넘으면 사고와 같은 '중지'로 승격한다 — 새 파일 14개면 28점, 멀쩡한
    프로젝트가 첫날부터 경보를 받는다. 오경보가 반복되면 진짜 사고 때 경고의
    권위가 소진된다(양치기 소년). 그래서 위반이 0이면 어떤 위생 누적으로도
    stop 이 되지 않는다. 기계 게이트(status·blocked·exit code)는 기존 의미를
    유지한다 — 바뀌는 것은 사람에게 보여주는 층(리포트 라벨·홈·작업방)뿐이다.

    앵커 '부재'(_anchor_violations = 신규 소스 파일에 앵커 없음)는 위생이다 —
    경계 침범이 아니라 다음 작업을 위한 준비 항목이므로 진행을 막지 않고
    prepare 로 유도한다(2026-06-12 사용자 피드백: "일단 진행시키고 나중에
    앵커를 추가하도록 유도").
    """
    if protected_violations or change_risk_level == "HIGH" or planning_level == "fail":
        return "stop"
    if status != "pass" or anchor_violations:
        return "prepare"
    return "pass"


def _verdict_lead(verdict: str) -> str:
    """요약 첫 줄 — 잘된 것을 먼저, 남은 것을 준비로 말한다(공포 어휘는 stop 전용)."""
    return {
        "stop": "멈출 사유를 찾았어요 — 아래 항목을 먼저 해결하세요. 백업에서 되돌릴 수 있어요.",
        "prepare": "이번 변경은 약속 범위 안입니다 ✓ — 다음 AI 작업 전에 준비하면 좋은 항목이 있어요.",
        "pass": "이상 없음 — 약속 범위 안에서 작업했어요.",
    }.get(verdict, "")


# === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_START ===
def _build_guard_envelope(
    root: Path,
    strict: bool,
    since_minutes: int,
    # === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_END ===
) -> GuardEnvelope:
    legacy_doctor = analyze_project(root, strict=strict)
    explain_report_obj = _guard_explain_report(root, since_minutes)
    explain_report = (
        explain_report_obj
        if hasattr(explain_report_obj, "files")
        else explain_from_mtime(root, since_minutes=since_minutes)
    )
    legacy_guard = combine_guard(legacy_doctor, explain_report)
    doctor_v2 = analyze_project_v2(root, strict=strict)
    violations = _protected_violations(root, explain_report.files)
    anchor_violations = _anchor_violations(
        root, explain_report.files, staged_only=explain_report.source == "git-staged"
    )
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
        "verdict": "pass",  # 자리값 — planning·anchor 병합이 끝난 envelope 말미에서 확정
        "strict": strict,
        "blocked": legacy_guard.blocked or (strict and status == "fail"),
        "project_score": doctor_v2.project_score,
        "project_status": doctor_v2.status,
        "change_risk_level": legacy_guard.change_risk_level,
        "summary": _envelope_summary(doctor_v2.status, doctor_v2.project_score, legacy_guard),
        "recommendations": _rewrite_recommendations(legacy_guard.recommendations),
        "protected_violations": violations,
        "anchor_violations": anchor_violations,
        "doctor": doctor_v2.to_dict(),
        "explain": explain_data,
        "planning": {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_message("planning_exempt"),
            "changed_files": [],
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["default_exempt"],
        },
    }
    planning = _planning_data(
        root,
        MetaPaths(root),
        strict,
        explain_report.files,
        explain_report.source,
    )
    data["planning"] = planning
    planning_level = _planning_guard_level(planning["status"], strict)
    data["status"] = _merge_status(status, planning_level)
    data["blocked"] = bool(data["blocked"] or data["status"] == "fail")
    if planning_level != "pass":
        data["summary"] = f"{data['summary']}\n\n구조 계획: {planning['summary']}"
        recommendations = list(data["recommendations"])
        if _PLAN_REQUIRED_RECOMMENDATION not in recommendations:
            recommendations.append(_PLAN_REQUIRED_RECOMMENDATION)
        data["recommendations"] = recommendations
    if anchor_violations:
        anchor_level = "fail" if strict else "warn"
        data["status"] = _merge_status(str(data["status"]), anchor_level)
        data["blocked"] = bool(data["blocked"] or anchor_level == "fail")
        joined = ", ".join(anchor_violations)
        data["summary"] = (
            f"{data['summary']}\n\n앵커 집행: 신규 소스 파일에 앵커가 없습니다. {joined}"
        )
        recommendations = list(data["recommendations"])
        if _ANCHOR_REQUIRED_RECOMMENDATION not in recommendations:
            recommendations.append(_ANCHOR_REQUIRED_RECOMMENDATION)
        data["recommendations"] = recommendations
    # 사람용 3단 판정 확정 — status/blocked 병합(planning·anchor)이 모두 끝난 뒤에 계산한다.
    verdict = _verdict_tier(
        violations,
        anchor_violations,
        explain_report.risk_level,
        str(planning_level),
        str(data["status"]),
    )
    data["verdict"] = verdict
    data["summary"] = f"{_verdict_lead(verdict)}\n{data['summary']}"
    if verdict != "stop":
        # 위반이 없는데 "멈추세요"가 첫 권고로 나오면 판정 첫 줄과 모순 — 공포 어휘는 stop 전용.
        data["recommendations"] = [
            r for r in data["recommendations"] if "멈추세요" not in r
        ]
    return {"ok": True, "error": None, "data": data}


def build_guard_envelope(root: Path, strict: bool, since_minutes: int) -> GuardEnvelope:
    return _build_guard_envelope(root, strict=strict, since_minutes=since_minutes)


# === ANCHOR: VIB_GUARD_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(data: GuardData) -> str:
    # 사람용 라벨은 3단 verdict 기준 — 구버전 데이터(verdict 부재)는 status 에서 보수적으로 유도.
    verdict = str(
        data.get("verdict")
        or {"pass": "pass", "warn": "prepare"}.get(str(data["status"]), "stop")
    )
    status_label = {
        "pass": "통과",
        "prepare": "준비 필요",
        "stop": "멈춤",
    }.get(verdict, verdict)
    status_hint = {
        "pass": "지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다.",
        "prepare": "이번 변경은 문제 없어요. 다음 AI 작업 전에 아래 권장 항목을 준비하면 더 안전해져요.",
        "stop": "발견된 문제를 먼저 해결하는 게 좋아요. 백업에서 되돌릴 수 있어요.",
    }.get(verdict, "현재 상태를 먼저 확인해보세요.")
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
    planning = data.get("planning")
    if planning:
        lines.extend(
            [
                "## 구조 계획 판정",
                f"- 상태: {planning.get('status')}",
                f"- 참조 plan: {planning.get('active_plan_id') or '없음'}",
                f"- 요약: {planning.get('summary')}",
            ]
        )
        changed_files = cast(list[object], planning.get("changed_files", []))
        if changed_files:
            lines.append("- 변경 파일:")
            lines.extend([f"  - `{item}`" for item in changed_files])
        required_reasons = cast(list[object], planning.get("required_reasons", []))
        if required_reasons:
            lines.append("- 필요 이유:")
            lines.extend([f"  - {item}" for item in required_reasons])
        deviations = cast(list[object], planning.get("deviations", []))
        if deviations:
            lines.append("- 이탈 항목:")
            lines.extend([f"  - {item}" for item in deviations])
        lines.append("")
    if data["protected_violations"]:
        lines.extend(["## 보호된 파일에서 바뀐 점"])
        lines.extend([f"- `{item}`" for item in data["protected_violations"]])
        lines.append("")
    if data["anchor_violations"]:
        lines.extend(["## 앵커 집행 경고"])
        lines.extend([f"- `{item}`" for item in data["anchor_violations"]])
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
