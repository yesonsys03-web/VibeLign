# === ANCHOR: EXPLAIN_CMD_START ===
from argparse import Namespace
import json
from pathlib import Path
from vibelign.core.change_explainer import (
    ExplainReport,
    explain_file_from_git,
    explain_file_from_mtime,
    explain_from_git,
    explain_from_mtime,
)

from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: EXPLAIN_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(report: ExplainReport) -> str:
    lines: list[str] = [
        "# VibeLign 변경 설명 리포트",
        "",
        f"소스: {report.source}",
        f"위험 수준: {report.risk_level}",
        "",
        "## 요약",
        report.summary,
        "",
        "## 변경된 사항",
    ]
    lines.extend(
        [f"- {item}" for item in report.what_changed]
        or ["- 주목할 만한 변경사항이 없습니다."]
    )
    lines.extend(["", "## 왜 중요한가"])
    lines.extend(
        [f"- {item}" for item in report.why_it_might_matter]
        or ["- 큰 영향이 없는 것으로 보입니다."]
    )
    lines.extend(["", "## 파일 목록"])
    if report.files:
        lines.extend(_render_reference_files(report.files))
    else:
        lines.append("- 나열된 파일이 없습니다.")
    lines.extend(["", "## 롤백 힌트", report.rollback_hint])
    return "\n".join(lines) + "\n"


def _render_reference_files(files: list[dict[str, str]]) -> list[str]:
    lines = ["파일 종류 요약:"]
    lines.extend(_file_kind_summary(files))
    lines.extend(["", "파일별 보기:"])
    for item in files:
        path = item.get("path", "")
        status_with_time = _file_status_with_time(item)
        lines.append(f"- `{path}` — {_file_kind_label(item)} ({status_with_time})")
    return lines


def _file_status_with_time(item: dict[str, str]) -> str:
    status = _status_label(item.get("status", ""))
    modified_at = item.get("modified_at", "")
    return f"{status}, {modified_at}" if modified_at else status


def _file_kind_summary(files: list[dict[str, str]]) -> list[str]:
    counts: dict[str, int] = {}
    for item in files:
        label = _file_kind_label(item)
        counts[label] = counts.get(label, 0) + 1
    order = ["문서", "테스트", "핵심 코드", "화면", "명령/설정", "일반 파일"]
    return [f"- {label} {counts[label]}개 — {_kind_description(label)}" for label in order if counts.get(label, 0)]


def _file_kind_label(item: dict[str, str]) -> str:
    kind = item.get("kind", "")
    path = item.get("path", "")
    if kind == "docs":
        return "문서"
    if kind == "test":
        return "테스트"
    if kind == "logic":
        return "핵심 코드"
    if kind == "ui":
        return "화면"
    if kind in {"entry file", "service"}:
        return "핵심 코드"
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if normalized.startswith("vibelign/commands/") or normalized.startswith("vibelign/cli/") or name in {"pyproject.toml", "vib.spec"}:
        return "명령/설정"
    return "일반 파일"


def _status_label(status: str) -> str:
    return {
        "modified": "수정됨",
        "untracked": "새 파일",
        "added": "추가됨",
        "deleted": "삭제됨",
        "renamed": "이름 변경",
    }.get(status, status or "상태 알 수 없음")


def _kind_description(label: str) -> str:
    return {
        "문서": "기획이나 설명 문서가 바뀌었습니다.",
        "테스트": "기능이 맞게 동작하는지 확인하는 코드가 바뀌었습니다.",
        "핵심 코드": "실제 기능 로직이 바뀌었습니다.",
        "화면": "GUI 화면이나 표시 코드가 바뀌었습니다.",
        "명령/설정": "CLI 명령, 패키징, 설정 파일이 바뀌었습니다.",
        "일반 파일": "기타 프로젝트 파일이 바뀌었습니다.",
    }.get(label, "프로젝트 파일이 바뀌었습니다.")


# === ANCHOR: EXPLAIN_CMD__RENDER_MARKDOWN_END ===


# === ANCHOR: EXPLAIN_CMD__RENDER_FILE_MARKDOWN_START ===
def _render_file_markdown(report: ExplainReport, rel_path: str) -> str:
    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(
        report.risk_level, "⚪"
    )
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
    lines.extend(
        [f"- {item}" for item in report.what_changed] or ["- 눈에 띄는 변경이 없어요."]
    )
    lines.extend(["", "## 3. 왜 신경 써야 하나요?"])
    lines.extend(
        [f"- {item}" for item in report.why_it_might_matter]
        or ["- 큰 영향은 없어 보여요."]
    )
    lines.extend(["", "## 4. 되돌리려면?", report.rollback_hint])
    return "\n".join(lines) + "\n"


# === ANCHOR: EXPLAIN_CMD__RENDER_FILE_MARKDOWN_END ===


# === ANCHOR: EXPLAIN_CMD_RUN_EXPLAIN_START ===
def run_explain(args: Namespace) -> None:
    root = Path.cwd()

    # 파일 인자가 있으면 파일별 설명 모드
    file_value = getattr(args, "file", None)
    file_arg = file_value if isinstance(file_value, str) else ""
    since_minutes_value = getattr(args, "since_minutes", 120)
    since_minutes = since_minutes_value if isinstance(since_minutes_value, int) else 120
    json_mode = bool(getattr(args, "json", False))
    write_report = bool(getattr(args, "write_report", False))
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
            root, rel, since_minutes=since_minutes
        )
        if json_mode:
            print(json.dumps(report.to_dict(), indent=2))
            return
        md = _render_file_markdown(report, rel)
        print(md)
        if write_report:
            out = root / "VIBELIGN_EXPLAIN.md"
            _ = out.write_text(md, encoding="utf-8")
            print(f"{out.name} 에 저장했습니다")
        return

    # 파일 인자 없으면 전체 프로젝트 explain
    report = explain_from_git(root) or explain_from_mtime(
        root, since_minutes=since_minutes
    )
    if json_mode:
        print(json.dumps(report.to_dict(), indent=2))
        return
    md = _render_markdown(report)
    print(md)
    if write_report:
        out = root / "VIBELIGN_EXPLAIN.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        _ = out.write_text(md, encoding="utf-8")
        print(f"{out.name}에 리포트를 저장했습니다")


# === ANCHOR: EXPLAIN_CMD_RUN_EXPLAIN_END ===
# === ANCHOR: EXPLAIN_CMD_END ===
