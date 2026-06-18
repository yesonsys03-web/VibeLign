from vibelign.core.reporting_cli.html_renderer import render_html
from vibelign.core.reporting_cli.font_sizes import ReportFontSizes
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


def test_theme_minimal_injects_its_css():
    html = render_html(_model(), theme="minimal")
    assert "Pretendard" in html and "text-transform:uppercase" in html


def test_generated_theme_injects_its_css():
    html = render_html(_model(), theme="cards-teal-dense")
    assert "#147A73" in html
    assert "border-radius:12px" in html


def test_unknown_theme_falls_back_to_classic():
    assert render_html(_model(), theme="nope") == render_html(_model(), theme="classic")


def test_default_theme_is_classic_unchanged():
    assert "#9B1B1B" in render_html(_model())


def test_font_size_overrides_are_injected_after_theme_css():
    html = render_html(
        _model(),
        theme="minimal",
        font_sizes=ReportFontSizes(title=32, heading=19, body=15),
    )
    assert "h1 { font-size:32px; }" in html
    assert "h2 { font-size:19px; }" in html
    assert "body { font-size:15px; }" in html


def test_author_shown_in_meta_when_present():
    from dataclasses import replace
    html = render_html(replace(_model(), author="홍길동"))
    assert "작성자: 홍길동" in html


def test_author_absent_keeps_meta_plain():
    assert "작성자:" not in render_html(_model())


def test_font_family_override_injected_after_theme_css():
    from vibelign.core.reporting_cli.fonts import ReportFonts
    html = render_html(_model(), theme="classic", fonts=ReportFonts(heading="pretendard"))
    assert "@font-face" in html
    assert '"Pretendard"' in html
    assert "h1, h2 { font-family:" in html


def test_no_fonts_keeps_theme_default_unchanged():
    assert render_html(_model(), theme="classic") == render_html(
        _model(), theme="classic", fonts=None
    )
