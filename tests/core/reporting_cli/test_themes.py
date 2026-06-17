from __future__ import annotations

from vibelign.core.reporting_cli.themes import THEME_IDS, get_theme


def test_five_themes_registered():
    assert THEME_IDS == ("classic", "minimal", "executive", "compact", "pastel")


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
