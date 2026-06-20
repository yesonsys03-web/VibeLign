# === ANCHOR: VIB_REPORT_CONTEXT_START ===
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path
from typing import NoReturn, Protocol

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli import (
    PlanningData,
    ReportModel,
    build_doc_report_model,
    build_report_model,
    parse_plan_markdown,
)
from vibelign.core.reporting_cli.font_sizes import ReportFontSizes, normalize_report_font_sizes
from vibelign.core.reporting_cli.fonts import ReportFonts, normalize_report_fonts
from vibelign.core.reporting_cli.themes import has_theme


# === ANCHOR: VIB_REPORT_CONTEXT_TYPES_START ===
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
    emit_model: bool
    assist_missing: bool
    visual_cards: bool
    reject_blocks: str | None
    polish_key: str | None
    theme: str
    title_font_size: int | None
    heading_font_size: int | None
    body_font_size: int | None
    meta_font_size: int | None
    heading_font: str | None
    body_font: str | None
    author: str
    page_numbers: bool


class ReportFailure(Protocol):
    def __call__(self, want_json: bool, message: str) -> NoReturn:
        ...


@dataclass(frozen=True, slots=True)
class ReportCommandContext:
    want_json: bool
    report_date: str
    plan_path: Path
    root: Path
    text: str
    data: PlanningData
    model: ReportModel
    slug_source: str
    provider: str
    author: str
    report_theme: str
    font_sizes: ReportFontSizes
    report_fonts: ReportFonts


@dataclass(frozen=True, slots=True)
class ModelBuildInput:
    raw: ReportArgs
    text: str
    data: PlanningData
    report_date: str
    plan_path: Path
    want_json: bool
# === ANCHOR: VIB_REPORT_CONTEXT_TYPES_END ===


# === ANCHOR: VIB_REPORT_CONTEXT_READ_START ===
def read_report_context(raw: ReportArgs, fail: ReportFailure) -> ReportCommandContext:
    want_json = bool(raw.json)
    report_date = raw.date or _date.today().isoformat()
    plan_path = Path(raw.plan).expanduser()
    if not plan_path.exists():
        fail(want_json, f"기획안 파일을 찾을 수 없어요: {plan_path}")
    report_theme = getattr(raw, "theme", "classic") or "classic"
    if not has_theme(report_theme):
        fail(want_json, f"알 수 없는 디자인 테마예요: {report_theme}")
    font_sizes = _normalize_font_sizes(raw, want_json, fail)
    report_fonts = _normalize_fonts(raw, want_json, fail)
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        fail(want_json, f"기획안을 읽을 수 없어요: {exc}")
    data = parse_plan_markdown(text)
    model_input = ModelBuildInput(raw, text, data, report_date, plan_path, want_json)
    model, slug_source = _build_model(model_input, fail)
    return ReportCommandContext(
        want_json=want_json,
        report_date=report_date,
        plan_path=plan_path,
        root=resolve_project_root(Path.cwd()),
        text=text,
        data=data,
        model=model,
        slug_source=slug_source,
        provider=getattr(raw, "cli", "auto") or "auto",
        author=getattr(raw, "author", "") or "",
        report_theme=report_theme,
        font_sizes=font_sizes,
        report_fonts=report_fonts,
    )


def _normalize_font_sizes(raw: ReportArgs, want_json: bool, fail: ReportFailure) -> ReportFontSizes:
    try:
        return normalize_report_font_sizes(
            title=getattr(raw, "title_font_size", None),
            heading=getattr(raw, "heading_font_size", None),
            body=getattr(raw, "body_font_size", None),
            meta=getattr(raw, "meta_font_size", None),
        )
    except ValueError as exc:
        fail(want_json, str(exc))


def _normalize_fonts(raw: ReportArgs, want_json: bool, fail: ReportFailure) -> ReportFonts:
    try:
        return normalize_report_fonts(
            heading=getattr(raw, "heading_font", None),
            body=getattr(raw, "body_font", None),
        )
    except ValueError as exc:
        fail(want_json, str(exc))


def _build_model(model_input: ModelBuildInput, fail: ReportFailure) -> tuple[ReportModel, str]:
    raw = model_input.raw
    author = getattr(raw, "author", "") or ""
    if raw.type == "doc":
        return _build_doc_model(model_input, author, fail)
    try:
        model = build_report_model(
            model_input.data,
            raw.type,
            date=model_input.report_date,
            source_plan_path=str(model_input.plan_path),
            author=author,
        )
    except ValueError as exc:
        fail(model_input.want_json, str(exc))
    return model, model_input.data.title or model_input.data.idea or model_input.plan_path.stem


def _build_doc_model(
    model_input: ModelBuildInput,
    author: str,
    fail: ReportFailure,
) -> tuple[ReportModel, str]:
    model = build_doc_report_model(
        model_input.text,
        date=model_input.report_date,
        source_plan_path=str(model_input.plan_path),
        author=author,
        default_title=model_input.plan_path.stem,
    )
    if not model.sections:
        fail(model_input.want_json, "문서에 내보낼 내용이 없습니다.")
    return model, model.title or model_input.plan_path.stem
# === ANCHOR: VIB_REPORT_CONTEXT_READ_END ===
# === ANCHOR: VIB_REPORT_CONTEXT_END ===
