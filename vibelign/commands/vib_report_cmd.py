from __future__ import annotations

import json
import sys
from datetime import date as _date
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli import (
    ReportRendererUnavailable,
    build_report_model,
    parse_plan_markdown,
    polish_report_model,
    render_docx,
    render_html,
    render_pptx,
    write_report,
    write_report_bytes,
)
from vibelign.core.reporting_cli.polish_cache import (
    load_polish_cache,
    polish_cache_key,
    save_polish_cache,
)
from vibelign.core.reporting_cli.storage import _report_slug
from vibelign.terminal_render import clack_intro, clack_success


class ReportArgs(Protocol):
    plan: str
    type: str
    format: str
    output: str | None
    force: bool
    date: str | None
    json: bool
    polish: bool
    cli: str


def run_vib_report(args: object) -> None:
    raw = cast(ReportArgs, args)
    want_json = bool(raw.json)
    report_date = raw.date or _date.today().isoformat()

    plan_path = Path(raw.plan).expanduser()
    if not plan_path.exists():
        _fail(want_json, f"기획안 파일을 찾을 수 없어요: {plan_path}")
        return

    root = resolve_project_root(Path.cwd())
    try:
        data = parse_plan_markdown(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _fail(want_json, f"기획안을 읽을 수 없어요: {exc}")
        return

    try:
        model = build_report_model(
            data,
            raw.type,
            date=report_date,
            source_plan_path=str(plan_path),
        )
    except ValueError as exc:
        _fail(want_json, str(exc))
        return

    slug_source = data.title or data.idea or plan_path.stem

    if getattr(raw, "polish", False):
        provider = getattr(raw, "cli", "auto") or "auto"
        # enrich 캐시(§6): 동일 입력 재요청 시 provider 재호출 0.
        key = polish_cache_key(model, provider=provider)
        slug = _report_slug(slug_source)
        cached = load_polish_cache(root, slug, key=key)
        if cached is not None:
            model = cached
        else:
            model = polish_report_model(model, provider=provider, root=root)
            save_polish_cache(root, slug, key=key, model=model)

    fmt = getattr(raw, "format", "html") or "html"
    try:
        if fmt == "docx":
            data_bytes = render_docx(model)
            dest = write_report_bytes(root, model, data_bytes, slug_source=slug_source, ext=".docx", output=raw.output, force=raw.force)
        elif fmt == "pptx":
            data_bytes = render_pptx(model)
            dest = write_report_bytes(root, model, data_bytes, slug_source=slug_source, ext=".pptx", output=raw.output, force=raw.force)
        else:  # html
            html = render_html(model)
            dest = write_report(root, model, html, slug_source=slug_source, output=raw.output, force=raw.force)
    except ReportRendererUnavailable as exc:
        _fail(want_json, str(exc))
        return
    except (FileExistsError, ValueError) as exc:
        _fail(want_json, str(exc))
        return

    if want_json:
        print(
            json.dumps(
                {"ok": True, "path": str(dest), "report_type": model.report_type},
                ensure_ascii=False,
            )
        )
    else:
        clack_intro("VibeLign 보고서")
        clack_success(f"보고서 저장: {dest}")


def _fail(want_json: bool, message: str) -> None:
    if want_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(message, file=sys.stderr)
    raise SystemExit(1)
