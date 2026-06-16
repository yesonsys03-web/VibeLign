from vibelign.core.reporting_cli.html_renderer import render_html
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _model() -> ReportModel:
    return ReportModel(
        title="예약 앱 <보고>",
        report_type="work",
        date="2026-06-15",
        sections=[
            Section("개요", [Block(kind="summary", text="미용실 예약 앱")]),
            Section(
                "핵심 내용",
                [Block(kind="bullets", items=["예약 캘린더", "알림 문자"])],
            ),
        ],
    )


def test_render_includes_title_and_type_label():
    html = render_html(_model())
    assert "예약 앱 &lt;보고&gt;" in html  # HTML 이스케이프됨
    assert "업무 보고" in html
    assert "2026-06-15" in html


def test_render_bullets_as_list_items():
    html = render_html(_model())
    assert "<li>예약 캘린더</li>" in html
    assert "<li>알림 문자</li>" in html


def test_render_is_full_document_with_print_css():
    html = render_html(_model())
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "@media print" in html
    assert "</html>" in html.rstrip()
