# === ANCHOR: THEMES_START ===
from __future__ import annotations

from vibelign.core.reporting_cli.theme_catalog import Theme, all_themes


THEMES: dict[str, Theme] = {theme.id: theme for theme in all_themes()}
THEME_IDS: tuple[str, ...] = tuple(THEMES)


def get_theme(theme_id: str) -> Theme:
    """테마 조회. 모르는/빈 id 는 classic 으로 폴백한다(렌더가 안 깨지게)."""
    return THEMES.get(theme_id) or THEMES["classic"]


def has_theme(theme_id: str) -> bool:
    return theme_id in THEMES
# === ANCHOR: THEMES_END ===
