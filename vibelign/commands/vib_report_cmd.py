from __future__ import annotations

import json
import sys
from datetime import date as _date
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli import (
    build_report_model,
    parse_plan_markdown,
    render_html,
    write_report,
)
from vibelign.terminal_render import clack_intro, clack_success


class ReportArgs(Protocol):
    plan: str
    type: str
    format: str
    output: str | None
    force: bool
    date: str | None
    json: bool


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

    html = render_html(model)
    slug_source = data.title or data.idea or plan_path.stem
    try:
        dest = write_report(
            root,
            model,
            html,
            slug_source=slug_source,
            output=raw.output,
            force=raw.force,
        )
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
