from __future__ import annotations

from vibelign.core.reporting_cli.report_card_news_poster import sanitize_card_news_html


def test_sanitize_strips_script_and_handlers() -> None:
    html = sanitize_card_news_html(
        '<html><body><h1 onclick="x()">A</h1><script>alert(1)</script><p>본문</p></body></html>'
    )
    assert html is not None
    assert "<script" not in html
    assert "onclick" not in html
    assert "본문" in html


def test_sanitize_strips_external_resources() -> None:
    html = sanitize_card_news_html(
        '<html><head><link rel="stylesheet" href="https://cdn/x.css"></head>'
        '<body><img src="https://evil/x.png"><iframe src="//e"></iframe>카드</body></html>'
    )
    assert html is not None
    assert "https://" not in html
    assert "<iframe" not in html
    assert "<link" not in html


def test_sanitize_returns_none_without_html() -> None:
    assert sanitize_card_news_html("그냥 설명 텍스트, HTML 없음") is None


def test_sanitize_keeps_inline_style() -> None:
    html = sanitize_card_news_html("<html><head><style>.c{color:red}</style></head><body>카드</body></html>")
    assert html is not None
    assert "<style>" in html
    assert "color:red" in html


def test_sanitize_strips_protocol_relative_css_url() -> None:
    html = sanitize_card_news_html("<html><head><style>div{background:url(//evil.com/x.png)}</style></head><body>카드</body></html>")
    assert html is not None
    assert "//evil.com" not in html
    assert "<style>" in html  # style block itself kept
    assert "카드" in html
