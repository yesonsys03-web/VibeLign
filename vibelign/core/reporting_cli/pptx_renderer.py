from __future__ import annotations

import io

from vibelign.core.reporting_cli.docx_renderer import ReportRendererUnavailable
from vibelign.core.reporting_cli.models import ReportModel
from vibelign.core.reporting_cli.templates import meta_line
from vibelign.core.reporting_cli.themes import get_theme

try:
    import pptx  # noqa: F401
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


def _section_text(section) -> str:
    lines: list[str] = []
    for block in section.blocks:
        if block.kind == "bullets":
            lines.extend(block.items)
        elif block.text:
            lines.append(block.text)
    return "\n".join(lines)


def render_pptx(model: ReportModel, theme: str = "classic") -> bytes:
    if not PPTX_AVAILABLE:
        raise ReportRendererUnavailable(
            "PPT 내보내기에 python-pptx 가 필요합니다. (pip install python-pptx)"
        )
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    accent = RGBColor.from_string(get_theme(theme).accent.lstrip("#"))

    def _accent_title(shape) -> None:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.font.color.rgb = accent

    prs = Presentation()
    # 제목 슬라이드
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = model.title
    _accent_title(title_slide.shapes.title)
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = meta_line(model)
    # Section 당 슬라이드 1장 (Title and Content 레이아웃)
    for section in model.sections:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = section.heading
        _accent_title(slide.shapes.title)
        body = _section_text(section)
        if len(slide.placeholders) > 1 and body:
            slide.placeholders[1].text = body
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
