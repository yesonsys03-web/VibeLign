# === ANCHOR: DOCTOR_CMD_START ===
import json
from pathlib import Path
from typing import Protocol
from vibelign.core.risk_analyzer import analyze_project
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


class DoctorArgs(Protocol):
    strict: bool
    json: bool


# === ANCHOR: DOCTOR_CMD_RUN_DOCTOR_START ===
def run_doctor(args: DoctorArgs) -> None:
    report = analyze_project(Path.cwd(), strict=args.strict)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    lines = [
        "# VibeLign Doctor Report",
        "",
        f"## 1. 지금 상태\n지금 프로젝트 상태는 `{report.level}`이고, 점수는 `{report.score}`입니다.",
        "",
        "## 2. 한눈에 보는 숫자",
        f"- 전체 파일 수: {report.stats.get('files_scanned', 0)}",
        f"- 소스 파일 수: {report.stats.get('source_files_scanned', 0)}",
        f"- 처음부터 중요한 역할을 하는 큰 파일 수: {report.stats.get('oversized_entry_files', 0)}",
        f"- 안전 구역 표시가 없는 파일 수: {report.stats.get('missing_anchor_files', 0)}",
        "",
    ]
    if not report.issues:
        lines.extend(
            ["## 3. 확인된 점", "- 지금 바로 걱정할 큰 구조 문제는 보이지 않습니다."]
        )
        print_ai_response("\n".join(lines) + "\n")
        return
    lines.extend(["## 3. 먼저 보면 좋은 문제"])
    for i, issue in enumerate(report.issues, 1):
        if isinstance(issue, dict):
            lines.append(f"{i}. {issue.get('found', '')}")
        else:
            lines.append(f"{i}. {issue}")
    lines.extend(["", "## 4. 다음에 하면 좋은 일"])
    for i, suggestion in enumerate(report.suggestions, 1):
        lines.append(f"{i}. {suggestion}")
    print_ai_response("\n".join(lines) + "\n")


# === ANCHOR: DOCTOR_CMD_RUN_DOCTOR_END ===
# === ANCHOR: DOCTOR_CMD_END ===
