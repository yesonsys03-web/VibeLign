from __future__ import annotations

import io

from vibelign.core.reporting_cli.docx_renderer import ReportRendererUnavailable
from vibelign.core.reporting_cli.models import ReportModel
from vibelign.core.reporting_cli.templates import REPORT_TYPE_LABELS

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


def render_pptx(model: ReportModel) -> bytes:
    if not PPTX_AVAILABLE:
        raise ReportRendererUnavailable(
            "PPT 내보내기에 python-pptx 가 필요합니다. (pip install python-pptx)"
        )
    from pptx import Presentation

    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    prs = Presentation()
    # 제목 슬라이드
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = model.title
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = f"{label} · {model.date}"
    # Section 당 슬라이드 1장 (Title and Content 레이아웃)
    for section in model.sections:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = section.heading
        body = _section_text(section)
        if len(slide.placeholders) > 1 and body:
            slide.placeholders[1].text = body
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
