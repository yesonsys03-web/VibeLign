# === ANCHOR: GUARD_CMD_START ===
import json
from argparse import Namespace
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.risk_analyzer import analyze_project
from vibelign.core.change_explainer import explain_from_git, explain_from_mtime
from vibelign.core.guard_report import GuardReport, combine_guard
from vibelign.core import protected_files as protected_files_mod
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print
get_protected = cast(Callable[[Path], set[str]], protected_files_mod.get_protected)
is_protected = cast(Callable[[str, set[str]], bool], protected_files_mod.is_protected)


class ExplainFileLike(Protocol):
    def to_dict(self) -> dict[str, object]: ...


# === ANCHOR: GUARD_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(
    report: GuardReport,
    protected_violations: list[str] | None = None,
) -> str:
    lines: list[str] = []
    doctor_data = cast(Mapping[str, object], report.doctor)
    explain_data = cast(Mapping[str, object], report.explain)
    # 보호 파일 위반이 있으면 최상단에 경고 표시
    if protected_violations:
        lines += [
            "# VibeLign 가드 리포트",
            "",
            "## ⚠️  보호된 파일이 수정되었습니다!",
            "",
        ]
        for f in protected_violations:
            lines.append(f"  [잠금] `{f}`")
        lines += [
            "",
            "AI가 건드리면 안 되는 파일이 바뀌었습니다. 먼저 이 부분부터 확인하세요.",
            "되돌리고 싶다면: `vib undo`",
            "",
            "---",
            "",
        ]
    else:
        lines.append("# VibeLign 가드 리포트")
        lines.append("")

    lines += [
        f"전체 상태: {report.overall_level}",
        f"지금 멈춰야 하나요?: {'예' if report.blocked else '아니오'}",
        f"프로젝트 기본 상태: {report.doctor_level}",
        f"프로젝트 점수: {report.doctor_score}",
        f"최근 바뀐 내용의 위험도: {report.change_risk_level}",
        "",
        "## 요약",
        report.summary,
        "",
        "## 다음에 하면 좋은 일",
    ]
    lines.extend([f"- {item}" for item in report.recommendations])
    lines.extend(["", "## 프로젝트에서 보인 문제"])
    raw_issues = doctor_data.get("issues", [])
    issues: list[str] = []
    if isinstance(raw_issues, list):
        for raw_item in cast(list[object], raw_issues):
            if isinstance(raw_item, dict):
                issues.append(str(cast(dict[str, object], raw_item).get("found", "")))
            elif isinstance(raw_item, str):
                issues.append(raw_item)
    lines.extend(
        [f"- {item}" for item in issues]
        or ["- 지금 바로 걱정할 큰 구조 문제는 없습니다."]
    )
    lines.extend(["", "## 최근 바뀐 파일"])
    raw_files = explain_data.get("files", [])
    files: list[Mapping[str, object]] = []
    if isinstance(raw_files, list):
        for raw_item in cast(list[object], raw_files):
            if isinstance(raw_item, dict):
                files.append(cast(Mapping[str, object], raw_item))
    if files:
        rendered_files: list[str] = []
        for item in files:
            path = item.get("path")
            status = item.get("status")
            kind = item.get("kind")
            if (
                isinstance(path, str)
                and isinstance(status, str)
                and isinstance(kind, str)
            ):
                rendered_files.append(f"- `{path}` ({status}, {kind})")
        lines.extend(rendered_files or ["- 최근에 바뀐 파일이 없습니다."])
    else:
        lines.append("- 최근에 바뀐 파일이 없습니다.")
    return "\n".join(lines) + "\n"


# === ANCHOR: GUARD_CMD__RENDER_MARKDOWN_END ===


# === ANCHOR: GUARD_CMD_RUN_GUARD_START ===
def run_guard(args: Namespace) -> None:
    root = Path.cwd()
    strict = bool(getattr(args, "strict", False))
    since_minutes_value = getattr(args, "since_minutes", 120)
    since_minutes = since_minutes_value if isinstance(since_minutes_value, int) else 120
    json_mode = bool(getattr(args, "json", False))
    write_report = bool(getattr(args, "write_report", False))

    doctor = analyze_project(root, strict=strict)
    explain: ExplainFileLike = explain_from_git(root) or explain_from_mtime(
        root, since_minutes=since_minutes
    )
    report: GuardReport = combine_guard(doctor, explain)
    explain_data = explain.to_dict()

    # 보호된 파일 위반 확인
    protected = get_protected(root)
    protected_violations: list[str] = []
    if protected:
        raw_files = explain_data.get("files", [])
        changed_paths: list[str] = []
        if isinstance(raw_files, list):
            for raw_item in cast(list[object], raw_files):
                if not isinstance(raw_item, dict):
                    continue
                path = cast(Mapping[str, object], raw_item).get("path")
                if isinstance(path, str):
                    changed_paths.append(path)
        for cp in changed_paths:
            if is_protected(cp, protected):
                protected_violations.append(cp)
    if json_mode:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report, protected_violations=protected_violations)
    print_ai_response(md)
    if write_report:
        out = root / "VIBELIGN_GUARD.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        _ = out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")


# === ANCHOR: GUARD_CMD_RUN_GUARD_END ===
# === ANCHOR: GUARD_CMD_END ===
