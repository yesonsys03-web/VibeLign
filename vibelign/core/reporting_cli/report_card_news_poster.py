# === ANCHOR: REPORT_CARD_NEWS_POSTER_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.report_card_news_html import render_card_news_html
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict, VisualCardsDict, VisualImageMetadata

_HTML_RE: Final[re.Pattern[str]] = re.compile(r"<html\b[\s\S]*?</html>", re.IGNORECASE)
_INTERACTIVE_CONTROL_RE: Final[re.Pattern[str]] = re.compile(r"<button\b", re.IGNORECASE)
_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"<script\b[\s\S]*?</script>", re.IGNORECASE)
_DANGEROUS_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"<\s*/?\s*(iframe|object|embed|link|base|meta)\b[^>]*>", re.IGNORECASE
)
_HANDLER_RE: Final[re.Pattern[str]] = re.compile(r"""\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_EXTERNAL_ATTR_RE: Final[re.Pattern[str]] = re.compile(
    r"""\s(?:src|href|xlink:href)\s*=\s*("(?:https?:)?//[^"]*"|'(?:https?:)?//[^']*')""", re.IGNORECASE
)
# Fix #1+#2: strip javascript:, vbscript:, and data: URI attribute values.
# Covers href/src and all other URL-bearing attrs.
_DANGEROUS_SCHEME_ATTR_RE: Final[re.Pattern[str]] = re.compile(
    r"""\s(?:src|href|xlink:href|srcset|poster|formaction|action|data-src)\s*=\s*"""
    r"""("\s*(?:javascript|vbscript|data):[^"]*"|'\s*(?:javascript|vbscript|data):[^']*')""",
    re.IGNORECASE,
)
# A whole-poster HTML design for up to 6 cards measured >195s with Claude (sonnet);
# 150s timed out and silently fell back to the deterministic render. Give real headroom.
_POSTER_TIMEOUT_SECONDS: Final = 300
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
    html = _DANGEROUS_SCHEME_ATTR_RE.sub("", html)
    if _has_remaining_external_url(html):
        # Intentionally over-broad sweep (defense-in-depth backstop; pairs with
        # the sandboxed iframe on the consumer side) — do NOT tighten this regex.
        html = re.sub(r"(https?:)?//[^\s\"'>)]+", "", html)
    if _INTERACTIVE_CONTROL_RE.search(html):
        # We strip all <script>; a surviving <button> means the model built a JS-driven
        # interactive page (slide/tab toggle) whose controls are now dead and whose
        # non-active cards stay hidden. Reject so the caller falls back to the static render.
        return None
    return html


def _has_remaining_external_url(html: str) -> bool:
    return "http://" in html or "https://" in html or "//" in html


def _self_contained_fallback(payload: VisualCardsDict, cards: list[VisualCardDict], root: Path) -> str:
    # The poster is shown in a sandboxed srcDoc iframe (null origin, no base URL), so a
    # relative <img src> to an on-disk SVG asset cannot load and renders as a broken image.
    # Clear asset_path so the renderer inlines the sketch SVG instead — fully self-contained.
    inline_cards: list[VisualCardDict] = []
    for card in cards:
        image: VisualImageMetadata = {**card["image"], "asset_path": ""}
        inline_cards.append({**card, "image": image})
    return render_card_news_html(payload, inline_cards, root, root)


def deterministic_poster_html(payload: VisualCardsDict, cards: list[VisualCardDict], root: Path) -> str:
    """Self-contained placeholder poster used as an instant sketch-first preview before the
    (slow) LLM poster is ready. Identical to the timeout/sanitize fallback render."""
    return _self_contained_fallback(payload, cards, root)


def generate_card_news_poster(
    payload: VisualCardsDict,
    cards: list[VisualCardDict],
    root: Path,
    provider: str,
    runner: cli_adapters.PlanningCliRunner | None = None,
    timeout_seconds: int = _POSTER_TIMEOUT_SECONDS,
) -> PosterResult:
    command = cli_adapters.build_cli_command(provider, _poster_prompt(cards))
    if command is None:
        raise CardNewsPosterError(f"{provider} CLI를 찾지 못해 카드뉴스 포스터를 만들지 못했어요.")
    active_runner = runner or cli_adapters.SubprocessPlanningCliRunner()
    result = active_runner.run(command, cwd=root, input_text="", timeout_seconds=timeout_seconds)
    status = safe_planning_status(result.status, result.stdout)
    if status == "timeout":
        return PosterResult(html=_self_contained_fallback(payload, cards, root), source="fallback")
    if status != "ok":
        raise CardNewsPosterError(f"{provider} CLI 카드뉴스 포스터 생성 실패: {result.stderr.strip() or status}")
    sanitized = sanitize_card_news_html(result.stdout)
    if sanitized is None:
        return PosterResult(html=_self_contained_fallback(payload, cards, root), source="fallback")
    return PosterResult(html=sanitized, source="llm")


def _poster_prompt(cards: list[VisualCardDict]) -> str:
    import json

    storyboard = json.dumps(
        [{"number": i, "title": c["title"], "body": c["body"], "caption": c["caption"]} for i, c in enumerate(cards, 1)],
        ensure_ascii=False,
    )[:_MAX_SOURCE_CHARS]
    return (
        "아래 스토리보드로 단일 파일 정적(static) 한국어 카드뉴스 HTML을 만들어줘.\n"
        "조건: 한국어는 DOM 텍스트로(이미지 글자 금지), 각 카드 본문에 CSS/inline-SVG 도식,\n"
        "외부 스크립트/이미지/CDN/iframe/link 금지, 인라인 <style>만 사용, 모바일에서 겹침/잘림 없음.\n"
        "JavaScript 절대 금지: <script>, onclick, <button>, 슬라이드/탭/캐러셀 같은 인터랙션을 넣지 마.\n"
        "모든 카드를 한 페이지에 세로로 전부 펼쳐 클릭 없이 한 번에 다 보이게 해(기본 숨김 금지). 그대로 읽고 인쇄할 수 있어야 해.\n"
        "설명 없이 <html>...</html> 하나만 반환해.\n\n"
        f"스토리보드 JSON:\n{storyboard}"
    )
# === ANCHOR: REPORT_CARD_NEWS_POSTER_END ===
