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
    assert "p.meta" not in css


def test_normalize_report_font_sizes_accepts_meta():
    sizes = normalize_report_font_sizes(meta=11)
    assert sizes == ReportFontSizes(meta=11)
    assert sizes.has_overrides()


def test_normalize_report_font_sizes_rejects_out_of_range_meta():
    try:
        normalize_report_font_sizes(meta=73)
    except ValueError as exc:
        assert "머리말" in str(exc)
        assert "8~72" in str(exc)
    else:
        raise AssertionError("머리말 폰트 크기 범위를 벗어나면 실패해야 합니다.")


def test_font_size_override_css_emits_meta_rule():
    css = font_size_override_css(ReportFontSizes(meta=11))
    assert "p.meta { font-size:11px; }" in css
