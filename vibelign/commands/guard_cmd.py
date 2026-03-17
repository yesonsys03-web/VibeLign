# === ANCHOR: GUARD_CMD_START ===
import json
from pathlib import Path
from vibelign.core.risk_analyzer import analyze_project
from vibelign.core.change_explainer import explain_from_git, explain_from_mtime
from vibelign.core.guard_report import combine_guard
from vibelign.core.protected_files import get_protected, is_protected
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: GUARD_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(report, protected_violations=None):
    lines = []
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
    lines.extend(
        [f"- {item}" for item in report.doctor.get("issues", [])]
        or ["- 지금 바로 걱정할 큰 구조 문제는 없습니다."]
    )
    lines.extend(["", "## 최근 바뀐 파일"])
    files = report.explain.get("files", [])
    if files:
        lines.extend(
            [f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in files]
        )
    else:
        lines.append("- 최근에 바뀐 파일이 없습니다.")
    return "\n".join(lines) + "\n"
# === ANCHOR: GUARD_CMD__RENDER_MARKDOWN_END ===


# === ANCHOR: GUARD_CMD_RUN_GUARD_START ===
def run_guard(args):
    root = Path.cwd()
    doctor = analyze_project(root, strict=args.strict)
    explain = explain_from_git(root) or explain_from_mtime(
        root, since_minutes=args.since_minutes
    )
    report = combine_guard(doctor, explain)
    explain_data = explain.to_dict()

    # 보호된 파일 위반 확인
    protected = get_protected(root)
    protected_violations = []
    if protected:
        changed_paths = [f["path"] for f in explain_data.get("files", [])]
        for cp in changed_paths:
            if is_protected(cp, protected):
                protected_violations.append(cp)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report, protected_violations=protected_violations)
    print_ai_response(md)
    if args.write_report:
        out = root / "VIBELIGN_GUARD.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")
# === ANCHOR: GUARD_CMD_RUN_GUARD_END ===
# === ANCHOR: GUARD_CMD_END ===
