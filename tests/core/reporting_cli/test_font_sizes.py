from vibelign.core.reporting_cli.font_sizes import (
    ReportFontSizes,
    font_size_override_css,
    normalize_report_font_sizes,
)


def test_normalize_report_font_sizes_accepts_optional_values():
    sizes = normalize_report_font_sizes(title=32, heading=None, body=15)
    assert sizes == ReportFontSizes(title=32, heading=None, body=15)


def test_normalize_report_font_sizes_rejects_out_of_range_value():
    try:
        normalize_report_font_sizes(title=7)
    except ValueError as exc:
        assert "8~72" in str(exc)
    else:
        raise AssertionError("폰트 크기 범위를 벗어나면 실패해야 합니다.")


def test_font_size_override_css_uses_only_present_values():
    css = font_size_override_css(ReportFontSizes(title=32, body=15))
    assert "h1 { font-size:32px; }" in css
    assert "body { font-size:15px; }" in css
    assert "h2" not in css
