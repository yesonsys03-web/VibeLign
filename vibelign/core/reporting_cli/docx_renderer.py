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


def _add_page_number_footer(document) -> None:
    """바닥글 중앙에 'PAGE / NUMPAGES'(예: 1 / 3) 필드를 넣는다. Word 가 실제 번호 렌더."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    para = document.sections[0].footer.paragraphs[0]
    para.alignment = 1  # WD_ALIGN_PARAGRAPH.CENTER

    def _field(instr: str) -> None:
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), instr)
        para._p.append(fld)

    _field("PAGE")
    para.add_run(" / ")
    _field("NUMPAGES")


def render_docx(model: ReportModel, theme: str = "classic", page_numbers: bool = False) -> bytes:
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
    if page_numbers:
        _add_page_number_footer(doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
