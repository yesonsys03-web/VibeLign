# === ANCHOR: RENDER_JOB_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli import (
    render_docx,
    render_html,
    render_pptx,
    write_report,
    write_report_bytes,
)
from vibelign.core.reporting_cli.models import ReportModel


def render_and_write(
    root: Path,
    model: ReportModel,
    fmt: str,
    *,
    slug_source: str,
    output: str | None,
    force: bool,
    theme: str = "classic",
) -> Path:
    """모델을 fmt 로 렌더해 저장하고 경로를 반환한다.
    예외는 호출자가 처리: ReportRendererUnavailable / FileExistsError / ValueError."""
    if fmt == "docx":
        data_bytes = render_docx(model, theme=theme)
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".docx", output=output, force=force
        )
    if fmt == "pptx":
        data_bytes = render_pptx(model, theme=theme)
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".pptx", output=output, force=force
        )
    html = render_html(model, theme=theme)
    return write_report(root, model, html, slug_source=slug_source, output=output, force=force)
# === ANCHOR: RENDER_JOB_END ===
