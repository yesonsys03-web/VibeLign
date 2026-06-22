# === ANCHOR: REPORT_CARD_NEWS_POSTER_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path  # noqa: F401
from typing import Final, Literal

from vibelign.core.planning_cli import cli_adapters  # noqa: F401
from vibelign.core.planning_cli.response_policy import safe_planning_status  # noqa: F401
from vibelign.core.reporting_cli.report_card_news_html import render_card_news_html  # noqa: F401
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict, VisualCardsDict  # noqa: F401

_HTML_RE: Final[re.Pattern[str]] = re.compile(r"<html\b[\s\S]*?</html>", re.IGNORECASE)
_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"<script\b[\s\S]*?</script>", re.IGNORECASE)
_DANGEROUS_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"<\s*/?\s*(iframe|object|embed|link|base|meta)\b[^>]*>", re.IGNORECASE
)
_HANDLER_RE: Final[re.Pattern[str]] = re.compile(r"""\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_EXTERNAL_ATTR_RE: Final[re.Pattern[str]] = re.compile(
    r"""\s(?:src|href|xlink:href)\s*=\s*("(?:https?:)?//[^"]*"|'(?:https?:)?//[^']*')""", re.IGNORECASE
)
_POSTER_TIMEOUT_SECONDS: Final = 150
_MAX_SOURCE_CHARS: Final = 7000


class CardNewsPosterError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PosterResult:
    html: str
    source: Literal["llm", "fallback"]


def sanitize_card_news_html(raw_html: str) -> str | None:
    match = _HTML_RE.search(raw_html)
    if match is None:
        return None
    html = match.group(0)
    html = _SCRIPT_RE.sub("", html)
    html = _DANGEROUS_TAG_RE.sub("", html)
    html = _HANDLER_RE.sub("", html)
    html = _EXTERNAL_ATTR_RE.sub("", html)
    if _has_remaining_external_url(html):
        html = re.sub(r"(https?:)?//[^\s\"'>]+", "", html)
    return html


def _has_remaining_external_url(html: str) -> bool:
    return "http://" in html or "https://" in html
# === ANCHOR: REPORT_CARD_NEWS_POSTER_END ===
