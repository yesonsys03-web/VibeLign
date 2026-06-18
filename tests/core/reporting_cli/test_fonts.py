import pytest
from vibelign.core.reporting_cli.fonts import (
    FONTS_DIR, REPORT_FONTS, font_def,
    ReportFonts, font_family_override_css, normalize_report_fonts,
)


def test_registry_has_five_fonts():
    assert set(REPORT_FONTS) == {
        "pretendard", "nanum-myeongjo", "gowun-batang", "gowun-dodum", "black-han-sans",
    }


def test_every_registered_face_file_exists_and_is_woff2():
    for fdef in REPORT_FONTS.values():
        for face in fdef.faces:
            path = FONTS_DIR / face.file
            assert path.exists(), f"missing {path}"
            assert path.read_bytes()[:4] == b"wOF2", f"not woff2: {path}"


def test_font_def_unknown_returns_none():
    assert font_def("nope") is None
    assert font_def("pretendard").office_name == "Pretendard"


def test_no_overrides_returns_empty():
    css = font_family_override_css(
        ReportFonts(), default_heading='"X", serif', default_body='"Y", serif'
    )
    assert css == ""


def test_heading_override_embeds_face_and_sets_h1_h2():
    css = font_family_override_css(
        ReportFonts(heading="pretendard"),
        default_heading='"X", serif', default_body='"Y", serif',
    )
    assert "@font-face" in css
    assert "data:font/woff2;base64," in css
    assert '"Pretendard"' in css
    # 제목만 바꿨으면 본문은 default 유지
    assert '"Y"' in css


def test_body_override_only_does_not_change_heading():
    css = font_family_override_css(
        ReportFonts(body="gowun-batang"),
        default_heading='"X", serif', default_body='"Y", serif',
    )
    assert '"Gowun Batang"' in css
    assert '"X"' in css  # 제목은 default 유지


def test_normalize_rejects_unknown_id():
    with pytest.raises(ValueError):
        normalize_report_fonts(heading="nope")


def test_normalize_blank_becomes_none():
    fonts = normalize_report_fonts(heading="", body="pretendard")
    assert fonts.heading is None
    assert fonts.body == "pretendard"
    assert fonts.has_overrides() is True
