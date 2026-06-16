import io
import pytest
from vibelign.core.reporting_cli.pptx_renderer import render_pptx, PPTX_AVAILABLE
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _model():
    return ReportModel(
        title="예약 앱", report_type="work", date="2026-06-16",
        sections=[
            Section("개요", [Block(kind="summary", text="미용실 예약 앱")]),
            Section("핵심 내용", [Block(kind="bullets", items=["예약 캘린더", "알림 문자"])]),
        ],
    )


@pytest.mark.skipif(not PPTX_AVAILABLE, reason="python-pptx 미설치")
def test_render_pptx_opens_with_slide_per_section():
    data = render_pptx(_model())
    assert data[:2] == b"PK"
    from pptx import Presentation
    prs = Presentation(io.BytesIO(data))
    # 제목 슬라이드 1 + 섹션 2 = 3
    assert len(prs.slides) == 3
    all_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                all_text.append(shape.text_frame.text)
    blob = "\n".join(all_text)
    assert "예약 앱" in blob
    assert "예약 캘린더" in blob


def test_render_pptx_missing_lib_raises_clear(monkeypatch):
    import vibelign.core.reporting_cli.pptx_renderer as mod
    monkeypatch.setattr(mod, "PPTX_AVAILABLE", False)
    with pytest.raises(mod.ReportRendererUnavailable):
        render_pptx(_model())
