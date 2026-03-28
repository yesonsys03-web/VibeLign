# === ANCHOR: VIB_EXPLAIN_CMD_START ===
import importlib
import json
from pathlib import Path
from typing import NotRequired, Protocol, TypedDict, cast

from vibelign.core.change_explainer import (
    FileSummary,
    explain_file_from_git,
    explain_file_from_mtime,
    explain_from_git,
    explain_from_mtime,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


class ExplainError(TypedDict):
    code: str
    message: str
    hint: str


class ExplainData(TypedDict):
    source: str
    risk_level: str
    summary: str
    what_changed: list[str]
    why_it_matters: list[str]
    what_to_do_next: str
    files: list[FileSummary]
    file: NotRequired[str]


class ExplainEnvelope(TypedDict):
    ok: bool
    error: ExplainError | None
    data: ExplainData


class ExplainArgs(Protocol):
    file: str | None
    since_minutes: int
    json: bool
    write_report: bool
    ai: bool


class AIExplainModule(Protocol):
    def has_ai_provider(self) -> bool: ...

    def explain_with_ai(self, data: ExplainData) -> tuple[object | None, object]: ...


def _risk_label(level: str) -> str:
    return {
        "LOW": "낮음",
        "MEDIUM": "보통",
        "HIGH": "높음",
    }.get(level, level)


def _resolve_file_path(
    root: Path, file_arg: str
) -> tuple[str | None, Path | None, str | None]:
    """파일 인자를 절대 경로로 해석. (rel_path, abs_path, error_msg) 반환."""
    p = Path(file_arg)
    abs_path = p if p.is_absolute() else root / p
    if not abs_path.exists():
        return (
            None,
            None,
            f"파일을 찾을 수 없어요: {file_arg}\n경로와 파일명을 다시 확인해보세요.",
        )
    try:
        rel = str(abs_path.relative_to(root))
    except ValueError:
        rel = file_arg
    return rel, abs_path, None


def _error_explain_data(file_arg: str) -> ExplainData:
    return {
        "file": file_arg,
        "source": "fallback",
        "risk_level": "LOW",
        "summary": "변경 설명 데이터를 만들지 못했습니다.",
        "what_changed": [],
        "why_it_matters": [],
        "what_to_do_next": "경로와 파일 상태를 확인한 뒤 다시 시도해보세요.",
        "files": [],
    }


def _build_file_explain_envelope(
    root: Path, file_arg: str, since_minutes: int
) -> ExplainEnvelope:
    """특정 파일의 변경 설명 envelope 를 반환."""
    rel, _abs, err = _resolve_file_path(root, file_arg)
    if err:
        return {
            "ok": False,
            "error": {"code": "file_not_found", "message": err, "hint": ""},
            "data": _error_explain_data(file_arg),
        }
    rel_path = rel or file_arg
    report = explain_file_from_git(root, rel_path)
    if report is None:
        report = explain_file_from_mtime(root, rel_path, since_minutes=since_minutes)
    data: ExplainData = {
        "file": rel_path,
        "source": report.source,
        "risk_level": report.risk_level,
        "summary": report.summary,
        "what_changed": report.what_changed,
        "why_it_matters": report.why_it_might_matter,
        "what_to_do_next": report.rollback_hint,
        "files": report.files,
    }
    return {"ok": True, "error": None, "data": data}


def _render_file_markdown(data: ExplainData) -> str:
    """파일별 explain 결과를 ask 스타일 마크다운으로 변환."""
    file_name = data.get("file", "")
    risk = data.get("risk_level", "LOW")
    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")

    what_changed = data.get("what_changed") or []
    why_matters = data.get("why_it_matters") or []

    source_label = {
        "git": "파일 변경 감지",
        "mtime": "최근 수정 시간 감지",
        "fallback": "자동 감지 실패",
    }.get(str(data.get("source", "")), str(data.get("source", "")))
    lines = [
        f"# `{file_name}` 변경 설명",
        "",
        f"**위험 수준:** {risk_emoji} {_risk_label(str(risk))}  |  **감지 방식:** {source_label}",
        "",
        "## 1. 무슨 일이 있었나요?",
        str(data.get("summary", "")),
        "",
        "## 2. 구체적으로 어떤 변화?",
    ]
    lines.extend(
        [f"- {item}" for item in what_changed] or ["- 눈에 띄는 변경이 없어요."]
    )
    lines.extend(["", "## 3. 왜 신경 써야 하나요?"])
    lines.extend([f"- {item}" for item in why_matters] or ["- 큰 영향은 없어 보여요."])
    lines.extend(["", "## 4. 되돌리려면?", str(data.get("what_to_do_next", ""))])
    return "\n".join(lines) + "\n"


def _build_explain_envelope(root: Path, since_minutes: int) -> ExplainEnvelope:
    report = explain_from_git(root)
    if report is None:
        report = explain_from_mtime(root, since_minutes=since_minutes)
    data: ExplainData = {
        "source": report.source,
        "risk_level": report.risk_level,
        "what_changed": report.what_changed,
        "why_it_matters": report.why_it_might_matter,
        "what_to_do_next": report.rollback_hint,
        "files": report.files,
        "summary": report.summary,
    }
    return {"ok": True, "error": None, "data": data}


def _render_markdown(data: ExplainData) -> str:
    files = data.get("files") or []
    what_changed = data.get("what_changed") or []
    why_it_matters = data.get("why_it_matters") or []
    source_label = {
        "git": "파일 변경 감지",
        "mtime": "최근 수정 시간 감지",
        "fallback": "자동 감지 실패",
    }.get(str(data.get("source", "")), str(data.get("source", "")))
    lines = [
        "# VibeLign Explain Report",
        "",
        f"위험 수준: {_risk_label(str(data['risk_level']))}  |  감지 방식: {source_label}",
        "",
        "## 1. 한 줄 요약",
        str(data["summary"]),
        "",
        "## 2. 변경된 내용",
    ]
    lines.extend(
        [f"- {item}" for item in what_changed] or ["- 눈에 띄는 변경이 없습니다."]
    )
    lines.extend(["", "## 3. 왜 중요한가"])
    lines.extend(
        [f"- {item}" for item in why_it_matters] or ["- 큰 영향은 없어 보입니다."]
    )
    lines.extend(
        ["", "## 4. 다음 할 일", str(data["what_to_do_next"]), "", "## 참고 파일"]
    )
    if files:
        lines.extend(
            [f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in files]
        )
    else:
        lines.append("- 나열할 파일이 없습니다.")
    return "\n".join(lines) + "\n"


def run_vib_explain(args: ExplainArgs) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)

    # ── 파일 인자가 있으면 파일별 explain 모드
    file_arg = args.file or ""
    if file_arg:
        envelope = _build_file_explain_envelope(
            root, file_arg, since_minutes=args.since_minutes
        )
        if not envelope["ok"]:
            err = envelope["error"]
            if err is None:
                print("✗ 변경 설명 데이터를 만들지 못했습니다.")
                return
            print(f"✗ {err['message']}")
            return
        if args.json:
            text = json.dumps(envelope, indent=2, ensure_ascii=False)
            print(text)
            if args.write_report:
                meta.ensure_vibelign_dirs()
                _ = meta.report_path("explain", "json").write_text(
                    text + "\n", encoding="utf-8"
                )
            return
        markdown = _render_file_markdown(envelope["data"])
        print_ai_response(markdown)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("explain", "md").write_text(markdown, encoding="utf-8")
        return

    # ── 파일 인자 없으면 기존 전체 프로젝트 explain 모드
    envelope = _build_explain_envelope(root, since_minutes=args.since_minutes)
    if args.json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("explain", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        return
    if args.ai:
        ai_fallback_message: str | None = None
        try:
            ai_explain_raw = cast(
                object, importlib.import_module("vibelign.core.ai_explain")
            )
            ai_explain = cast(AIExplainModule, ai_explain_raw)
        except Exception:
            text = None
            ai_fallback_message = "AI 설명을 불러오지 못해 기본 설명으로 대체합니다."
        else:
            try:
                has_provider = ai_explain.has_ai_provider()
            except Exception:
                has_provider = False
                ai_fallback_message = (
                    "AI 설정을 확인하지 못해 기본 설명으로 대체합니다."
                )
            if has_provider:
                try:
                    text, _attempted = ai_explain.explain_with_ai(envelope["data"])
                except Exception:
                    text = None
                    ai_fallback_message = (
                        "AI 설명 생성에 실패해 기본 설명으로 대체합니다."
                    )
                else:
                    if text is not None and not isinstance(text, str):
                        text = None
                        ai_fallback_message = (
                            "AI 설명 결과를 해석하지 못해 기본 설명으로 대체합니다."
                        )
                    elif text is not None and not text.strip():
                        text = None
                        ai_fallback_message = (
                            "AI 설명 결과가 비어 있어 기본 설명으로 대체합니다."
                        )
            else:
                text = None
                if ai_fallback_message is None:
                    print("AI API 키가 설정되어 있지 않아서 기본 설명을 보여드릴게요.")
                    print(
                        "더 자세한 설명을 원하시면 vib config 에서 AI API를 설정하세요."
                    )
                    print("  (Google Gemini는 무료 키를 바로 받을 수 있어요)")
                    print()
        if text is not None:
            print_ai_response(text)
            if args.write_report:
                meta.ensure_vibelign_dirs()
                _ = meta.report_path("explain", "md").write_text(
                    text + "\n", encoding="utf-8"
                )
            return
        if ai_fallback_message is not None:
            print(ai_fallback_message)
            print()
    markdown = _render_markdown(envelope["data"])
    print_ai_response(markdown)
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("explain", "md").write_text(markdown, encoding="utf-8")


# === ANCHOR: VIB_EXPLAIN_CMD_END ===
