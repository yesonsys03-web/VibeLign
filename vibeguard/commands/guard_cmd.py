import json
from pathlib import Path
from vibeguard.core.risk_analyzer import analyze_project
from vibeguard.core.change_explainer import explain_from_git, explain_from_mtime
from vibeguard.core.guard_report import combine_guard
from vibeguard.core.protected_files import get_protected, is_protected

def _render_markdown(report, protected_violations=None):
    lines = []
    # 보호 파일 위반이 있으면 최상단에 경고 표시
    if protected_violations:
        lines += [
            "# VibeGuard 가드 리포트",
            "",
            "## ⚠️  보호된 파일이 수정되었습니다!",
            "",
        ]
        for f in protected_violations:
            lines.append(f"  [잠금] `{f}`")
        lines += [
            "",
            "AI가 보호 설정된 파일을 건드렸습니다. 즉시 확인하세요.",
            "되돌리려면: `vibeguard undo`",
            "",
            "---",
            "",
        ]
    else:
        lines.append("# VibeGuard 가드 리포트")
        lines.append("")

    lines += [f"종합 수준: {report.overall_level}", f"차단 여부: {'예' if report.blocked else '아니오'}", f"Doctor 수준: {report.doctor_level}", f"Doctor 점수: {report.doctor_score}", f"최근 변경 위험도: {report.change_risk_level}", "", "## 요약", report.summary, "", "## 권장 조치"]
    lines.extend([f"- {item}" for item in report.recommendations])
    lines.extend(["", "## Doctor 문제 목록"])
    lines.extend([f"- {item}" for item in report.doctor.get("issues", [])] or ["- 주요 구조적 문제가 없습니다."])
    lines.extend(["", "## 최근 변경된 파일"])
    files = report.explain.get("files", [])
    if files:
        lines.extend([f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in files])
    else:
        lines.append("- 최근 변경된 파일이 없습니다.")
    return "\n".join(lines) + "\n"

def run_guard(args):
    root = Path.cwd()
    doctor = analyze_project(root, strict=args.strict)
    explain = explain_from_git(root) or explain_from_mtime(root, since_minutes=args.since_minutes)
    report = combine_guard(doctor, explain)

    # 보호된 파일 위반 확인
    protected = get_protected(root)
    protected_violations = []
    if protected:
        changed_paths = [f["path"] for f in explain.get("files", [])]
        for cp in changed_paths:
            if is_protected(cp, protected):
                protected_violations.append(cp)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report, protected_violations=protected_violations)
    print(md)
    if args.write_report:
        out = root / "VIBEGUARD_GUARD.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")
