from __future__ import annotations

import io

from vibelign.core.reporting_cli.models import ReportModel
from vibelign.core.reporting_cli.templates import meta_line
from vibelign.core.reporting_cli.themes import get_theme

try:
    import docx  # noqa: F401
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class ReportRendererUnavailable(RuntimeError):
    """렌더러 라이브러리(python-docx/pptx) 미설치."""


def render_docx(model: ReportModel, theme: str = "classic") -> bytes:
    if not DOCX_AVAILABLE:
        raise ReportRendererUnavailable(
            "Word 내보내기에 python-docx 가 필요합니다. (pip install python-docx)"
        )
    from docx import Document
    from docx.shared import RGBColor

    accent = RGBColor.from_string(get_theme(theme).accent.lstrip("#"))

    def _accent(heading) -> None:
        for r in heading.runs:
            r.font.color.rgb = accent

    doc = Document()
    _accent(doc.add_heading(model.title, level=0))
    doc.add_paragraph(meta_line(model))
    for section in model.sections:
        _accent(doc.add_heading(section.heading, level=1))
        for block in section.blocks:
            if block.kind == "bullets":
                for item in block.items:
                    doc.add_paragraph(item, style="List Bullet")
            elif block.kind == "summary":
                p = doc.add_paragraph()
                run = p.add_run(block.text)
                run.bold = True
            else:  # paragraph
                doc.add_paragraph(block.text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
