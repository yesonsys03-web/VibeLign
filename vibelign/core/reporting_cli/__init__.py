# === ANCHOR: __INIT___START ===
from vibelign.core.reporting_cli.docx_renderer import ReportRendererUnavailable, render_docx
from vibelign.core.reporting_cli.html_renderer import render_html
from vibelign.core.reporting_cli.models import (
    Block,
    PlanningData,
    ReportModel,
    Section,
)
from vibelign.core.reporting_cli.pptx_renderer import render_pptx
from vibelign.core.reporting_cli.reader import build_doc_report_model, parse_plan_markdown
from vibelign.core.reporting_cli.storage import write_report, write_report_bytes
from vibelign.core.reporting_cli.templates import (
    REPORT_TEMPLATES,
    REPORT_TYPE_LABELS,
    build_report_model,
)


# === ANCHOR: __INIT___POLISH_REPORT_MODEL_START ===
def polish_report_model(model: ReportModel, *, provider: str = "auto", root=None) -> ReportModel:
    from vibelign.core.reporting_cli.polish import polish_report_model as _polish_report_model

    return _polish_report_model(model, provider=provider, root=root)
# === ANCHOR: __INIT___POLISH_REPORT_MODEL_END ===

__all__ = [
    "Block",
    "PlanningData",
    "ReportModel",
    "ReportRendererUnavailable",
    "Section",
    "parse_plan_markdown",
    "build_doc_report_model",
    "polish_report_model",
    "REPORT_TEMPLATES",
    "REPORT_TYPE_LABELS",
    "build_report_model",
    "render_docx",
    "render_html",
    "render_pptx",
    "write_report",
    "write_report_bytes",
]
# === ANCHOR: __INIT___END ===
