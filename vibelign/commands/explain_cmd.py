# === ANCHOR: EXPLAIN_CMD_START ===
import json
from pathlib import Path
from vibelign.core.change_explainer import (
    explain_file_from_git,
    explain_file_from_mtime,
    explain_from_git,
    explain_from_mtime,

)

from vibelign.terminal_render import cli_print
print = cli_print

# === ANCHOR: EXPLAIN_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(report):
    lines = ["# VibeLign 변경 설명 리포트", "", f"소스: {report.source}", f"위험 수준: {report.risk_level}", "", "## 요약", report.summary, "", "## 변경된 사항"]
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
# === ANCHOR: EXPLAIN_CMD__RENDER_MARKDOWN_END ===

# === ANCHOR: EXPLAIN_CMD__RENDER_FILE_MARKDOWN_START ===
def _render_file_markdown(report, rel_path: str) -> str:
    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(report.risk_level, "⚪")
    lines = [
        f"# `{rel_path}` 변경 설명",
        "",
        f"위험 수준: {risk_emoji} {report.risk_level}  |  소스: {report.source}",
        "",
        "## 1. 무슨 일이 있었나요?",
        report.summary,
        "",
        "## 2. 구체적으로 어떤 변화?",
    ]
    lines.extend([f"- {item}" for item in report.what_changed] or ["- 눈에 띄는 변경이 없어요."])
    lines.extend(["", "## 3. 왜 신경 써야 하나요?"])
    lines.extend([f"- {item}" for item in report.why_it_might_matter] or ["- 큰 영향은 없어 보여요."])
    lines.extend(["", "## 4. 되돌리려면?", report.rollback_hint])
    return "\n".join(lines) + "\n"
# === ANCHOR: EXPLAIN_CMD__RENDER_FILE_MARKDOWN_END ===


# === ANCHOR: EXPLAIN_CMD_RUN_EXPLAIN_START ===
def run_explain(args):
    root = Path.cwd()

    # 파일 인자가 있으면 파일별 설명 모드
    file_arg: str = getattr(args, "file", None) or ""
    if file_arg:
        p = Path(file_arg)
        abs_path = p if p.is_absolute() else root / p
        if not abs_path.exists():
            print(f"파일을 찾을 수 없어요: {file_arg}")
            return
        try:
            rel = str(abs_path.relative_to(root))
        except ValueError:
            rel = file_arg
        report = explain_file_from_git(root, rel) or explain_file_from_mtime(
            root, rel, since_minutes=args.since_minutes
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
            return
        md = _render_file_markdown(report, rel)
        print(md)
        if args.write_report:
            out = root / "VIBELIGN_EXPLAIN.md"
            out.write_text(md, encoding="utf-8")
            print(f"{out.name} 에 저장했습니다")
        return

    # 파일 인자 없으면 전체 프로젝트 explain
    report = explain_from_git(root) or explain_from_mtime(root, since_minutes=args.since_minutes)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report)
    print(md)
    if args.write_report:
        out = root / "VIBELIGN_EXPLAIN.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")
# === ANCHOR: EXPLAIN_CMD_RUN_EXPLAIN_END ===
# === ANCHOR: EXPLAIN_CMD_END ===
