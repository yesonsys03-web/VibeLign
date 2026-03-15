# === ANCHOR: VIB_EXPLAIN_CMD_START ===
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from vibelign.core.change_explainer import (
    explain_file_from_git,
    explain_file_from_mtime,
    explain_from_git,
    explain_from_mtime,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


def _risk_label(level: str) -> str:
    return {
        "LOW": "낮음",
        "MEDIUM": "보통",
        "HIGH": "높음",
    }.get(level, level)


def _resolve_file_path(
    root: Path, file_arg: str
) -> tuple[Optional[str], Optional[Path], Optional[str]]:
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


def _build_file_explain_envelope(
    root: Path, file_arg: str, since_minutes: int
) -> Dict[str, Any]:
    """특정 파일의 변경 설명 envelope 를 반환."""
    rel, _abs, err = _resolve_file_path(root, file_arg)
    if err:
        return {
            "ok": False,
            "error": {"code": "file_not_found", "message": err, "hint": ""},
            "data": {"file": file_arg},
        }
    if rel is None:
        return {
            "ok": False,
            "error": {"code": "file_not_found", "message": file_arg, "hint": ""},
            "data": {"file": file_arg},
        }
    rel_path = rel

    report = explain_file_from_git(root, rel_path) or explain_file_from_mtime(
        root, rel_path, since_minutes=since_minutes
    )
    data = {
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


def _render_file_markdown(data: Dict[str, Any]) -> str:
    """파일별 explain 결과를 ask 스타일 마크다운으로 변환."""
    file_name = data.get("file", "")
    risk = data.get("risk_level", "LOW")
    risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")

    what_changed = cast(List[str], data.get("what_changed") or [])
    why_matters = cast(List[str], data.get("why_it_matters") or [])

    lines = [
        f"# `{file_name}` 변경 설명",
        "",
        f"**위험 수준:** {risk_emoji} {_risk_label(str(risk))}  |  **소스:** {data.get('source', '')}",
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


def _fallback_explain_data() -> Dict[str, Any]:
    return {
        "source": "fallback",
        "risk_level": "LOW",
        "what_changed": ["변경 설명 데이터를 자동으로 만들지 못했습니다."],
        "why_it_matters": ["현재 작업 상태를 직접 확인하는 편이 안전합니다."],
        "what_to_do_next": "git status 나 최근 수정 파일을 직접 확인하세요.",
        "files": [],
        "summary": "자동 설명이 실패해 안전한 기본 안내를 보여줍니다.",
    }


def _build_explain_envelope(root: Path, since_minutes: int) -> Dict[str, Any]:
    report = explain_from_git(root) or explain_from_mtime(
        root, since_minutes=since_minutes
    )
    if report is None:
        return {
            "ok": False,
            "error": {
                "code": "explain_unavailable",
                "message": "변경 설명 데이터를 만들지 못했습니다.",
                "hint": "git 상태나 최근 수정 파일을 직접 확인하세요.",
            },
            "data": _fallback_explain_data(),
        }
    data = {
        "source": report.source,
        "risk_level": report.risk_level,
        "what_changed": report.what_changed,
        "why_it_matters": report.why_it_might_matter,
        "what_to_do_next": report.rollback_hint,
        "files": report.files,
        "summary": report.summary,
    }
    return {"ok": True, "error": None, "data": data}


def _render_markdown(data: Dict[str, Any]) -> str:
    files = cast(List[Dict[str, str]], data.get("files", []) or [])
    what_changed = cast(List[str], data.get("what_changed", []) or [])
    why_it_matters = cast(List[str], data.get("why_it_matters", []) or [])
    lines = [
        "# VibeLign Explain Report",
        "",
        f"소스: {data['source']}",
        f"위험 수준: {_risk_label(str(data['risk_level']))}",
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


def run_vib_explain(args: Any) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)

    # ── 파일 인자가 있으면 파일별 explain 모드
    file_arg: str = getattr(args, "file", None) or ""
    if file_arg:
        envelope = _build_file_explain_envelope(
            root, file_arg, since_minutes=args.since_minutes
        )
        if not envelope["ok"]:
            err = envelope["error"]
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
        ai_explain = importlib.import_module("vibelign.core.ai_explain")
        if ai_explain.has_ai_provider():
            try:
                text, _attempted = ai_explain.explain_with_ai(envelope["data"])
            except Exception:
                text = None
        else:
            text = None
        if text:
            print_ai_response(text)
            if args.write_report:
                meta.ensure_vibelign_dirs()
                _ = meta.report_path("explain", "md").write_text(
                    text + "\n", encoding="utf-8"
                )
            return
    markdown = _render_markdown(envelope["data"])
    print_ai_response(markdown)
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("explain", "md").write_text(markdown, encoding="utf-8")


# === ANCHOR: VIB_EXPLAIN_CMD_END ===
