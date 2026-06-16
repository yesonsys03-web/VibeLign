import io
import pytest
from vibelign.core.reporting_cli.docx_renderer import render_docx, DOCX_AVAILABLE
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _model():
    return ReportModel(
        title="예약 앱", report_type="work", date="2026-06-16",
        sections=[
            Section("개요", [Block(kind="summary", text="미용실 예약 앱")]),
            Section("핵심 내용", [Block(kind="bullets", items=["예약 캘린더", "알림 문자"])]),
            Section("배경", [Block(kind="paragraph", text="전화 예약 누락")]),
        ],
    )


@pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx 미설치")
def test_render_docx_opens_and_contains_text():
    data = render_docx(_model())
    assert data[:2] == b"PK"  # docx = zip
    from docx import Document
    doc = Document(io.BytesIO(data))
    texts = "\n".join(p.text for p in doc.paragraphs)
    assert "예약 앱" in texts
    assert "업무 보고" in texts  # report_type 라벨
    assert "예약 캘린더" in texts
    assert "전화 예약 누락" in texts


def test_render_docx_missing_lib_raises_clear(monkeypatch):
    import vibelign.core.reporting_cli.docx_renderer as mod
    monkeypatch.setattr(mod, "DOCX_AVAILABLE", False)
    with pytest.raises(mod.ReportRendererUnavailable):
        render_docx(_model())
