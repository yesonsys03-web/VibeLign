from __future__ import annotations

from vibelign.core.reporting_cli.themes import THEME_IDS, get_theme


def test_five_themes_registered():
    assert THEME_IDS[:5] == ("classic", "minimal", "executive", "compact", "pastel")
    assert len(THEME_IDS) == 118


def test_each_theme_has_nonempty_fields():
    for tid in THEME_IDS:
        t = get_theme(tid)
        assert t.id == tid
        assert t.label and t.html_css and t.accent and t.heading_font and t.body_font


def test_unknown_theme_falls_back_to_classic():
    assert get_theme("nope").id == "classic"
    assert get_theme("").id == "classic"


def test_classic_css_matches_current_design():
    assert get_theme("classic").accent == "#9B1B1B"


def test_generated_theme_uses_token_catalog():
    theme = get_theme("board-indigo-balanced")
    assert theme.label == "임원형 · 인디고 · 표준"
    assert theme.accent == "#3157A4"
    assert "background:var(--accent)" in theme.html_css


def test_satgat_specimen_pack_has_thirteen_report_forms():
    satgat_ids = [tid for tid in THEME_IDS if tid.startswith("satgat-")]
    assert len(satgat_ids) == 13
    assert satgat_ids[0] == "satgat-work-brief"
    assert satgat_ids[-1] == "satgat-case-study"


def test_satgat_specimen_uses_korean_print_tokens():
    theme = get_theme("satgat-executive-memo")
    assert theme.label == "삿갓 · 임원 메모"
    assert theme.paper == "#F7F7F2"
    assert theme.ink == "#1C1916"
    assert theme.accent == "#9B1B1B"
    assert "백자지" in theme.html_css
    assert "한 페이지 강조 5%" in theme.html_css
    assert "word-break:keep-all" in theme.html_css
    assert "@media (max-width:480px)" in theme.html_css
