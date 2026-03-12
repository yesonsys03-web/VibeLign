import json
from pathlib import Path
from vibeguard.core.change_explainer import explain_from_git, explain_from_mtime

def _render_markdown(report):
    lines = ["# VibeGuard 변경 설명 리포트", "", f"소스: {report.source}", f"위험 수준: {report.risk_level}", "", "## 요약", report.summary, "", "## 변경된 사항"]
    lines.extend([f"- {item}" for item in report.what_changed] or ["- 주목할 만한 변경사항이 없습니다."])
    lines.extend(["", "## 왜 중요한가"])
    lines.extend([f"- {item}" for item in report.why_it_might_matter] or ["- 큰 영향이 없는 것으로 보입니다."])
    lines.extend(["", "## 파일 목록"])
    if report.files:
        lines.extend([f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in report.files])
    else:
        lines.append("- 나열된 파일이 없습니다.")
    lines.extend(["", "## 롤백 힌트", report.rollback_hint])
    return "\n".join(lines) + "\n"

def run_explain(args):
    root = Path.cwd()
    report = explain_from_git(root) or explain_from_mtime(root, since_minutes=args.since_minutes)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report)
    print(md)
    if args.write_report:
        out = root / "VIBEGUARD_EXPLAIN.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")
