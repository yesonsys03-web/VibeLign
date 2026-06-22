# === ANCHOR: REPORT_CARD_NEWS_EXPORT_START ===
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import TypedDict

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli.report_card_news_asset_generator import materialize_card_news_assets
from vibelign.core.reporting_cli.report_card_news_html import render_card_news_html
from vibelign.core.planning_cli.storage import safe_plan_slug
from vibelign.core.reporting_cli.report_card_news_prompts import (
    CardNewsPromptPack,
    write_card_news_prompt_pack,
)
from vibelign.core.reporting_cli.report_card_news_payload import load_visual_cards_payload, load_card_news_poster_html
from vibelign.core.reporting_cli.report_card_news_poster import sanitize_card_news_html
from vibelign.core.reporting_cli.report_visual_cards import (
    VisualCardDict,
    VisualCardsDict,
)

EXPORT_SCHEMA_VERSION = "report-card-news-export-v1"
_MAX_CARD_NEWS_SLUG_CHARS = 80


# === ANCHOR: REPORT_CARD_NEWS_EXPORT_CARDNEWSEXPORTERROR_START ===
class CardNewsExportError(ValueError):
    pass
# === ANCHOR: REPORT_CARD_NEWS_EXPORT_CARDNEWSEXPORTERROR_END ===


@dataclass(frozen=True, slots=True)
# === ANCHOR: REPORT_CARD_NEWS_EXPORT_CARDNEWSEXPORT_START ===
class CardNewsExport:
    json_path: Path
    html_path: Path
    storyboard_path: Path
    prompt_dir: Path
    prompt_paths: list[Path]
    card_count: int
# === ANCHOR: REPORT_CARD_NEWS_EXPORT_CARDNEWSEXPORT_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__EXPORTPAYLOAD_START ===
class _ExportPayload(TypedDict):
    schema_version: str
    provider: str
    card_count: int
    cards: list[VisualCardDict]
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__EXPORTPAYLOAD_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT_EXPORT_CARD_NEWS_START ===
def export_card_news(payload_path: Path) -> CardNewsExport:
    root = resolve_project_root(Path.cwd()).resolve()
    payload = load_visual_cards_payload(payload_path)
    approved = [card for card in payload["cards"] if card["approved"]]
    if not approved:
        raise CardNewsExportError("승인된 카드가 없습니다. 카드뉴스로 내보낼 카드를 먼저 승인하세요.")
    slug = _card_news_slug(_slug_source(approved))
    out_dir = _safe_card_news_dir(root)
    json_path = _safe_card_news_path(root, slug, ".json")
    html_path = _safe_card_news_path(root, slug, ".html")
    out_dir.mkdir(parents=True, exist_ok=True)
    approved_with_assets = materialize_card_news_assets(root, slug, approved)
    export_json = json.dumps(_export_payload(payload, approved_with_assets), ensure_ascii=False, indent=2)
    _ = json_path.write_text(f"{export_json}\n", encoding="utf-8")
    poster_html = load_card_news_poster_html(payload_path)
    safe_poster = sanitize_card_news_html(poster_html) if poster_html else None
    html_body = safe_poster if safe_poster is not None else render_card_news_html(
        payload, approved_with_assets, root, html_path.parent
    )
    _ = html_path.write_text(html_body, encoding="utf-8")
    prompt_pack = _write_prompt_pack(root, slug, payload, approved_with_assets)
    return CardNewsExport(
        json_path=json_path,
        html_path=html_path,
        storyboard_path=json_path,
        prompt_dir=prompt_pack.prompt_dir,
        prompt_paths=prompt_pack.prompt_paths,
        card_count=len(approved),
    )
# === ANCHOR: REPORT_CARD_NEWS_EXPORT_EXPORT_CARD_NEWS_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_CARD_NEWS_DIR_START ===
def _safe_card_news_dir(root: Path) -> Path:
    out_dir = root / ".vibelign" / "reports" / "card-news"
    _assert_inside_root(root, out_dir)
    return out_dir
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_CARD_NEWS_DIR_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_CARD_NEWS_PATH_START ===
def _safe_card_news_path(root: Path, slug: str, suffix: str) -> Path:
    relative = _unique_card_news_relative_path(root, f"{slug}-card-news{suffix}")
    path = root / relative
    _assert_inside_root(root, path)
    return path
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_CARD_NEWS_PATH_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_PROMPT_DIR_START ===
def _safe_prompt_dir(root: Path, slug: str) -> Path:
    path = root / ".vibelign" / "reports" / "card-news" / "prompts" / f"{slug}-card-news"
    _assert_inside_root(root, path)
    return path
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SAFE_PROMPT_DIR_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__ASSERT_INSIDE_ROOT_START ===
def _assert_inside_root(root: Path, path: Path) -> None:
    try:
        _ = path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise CardNewsExportError("카드뉴스 출력 경로가 프로젝트 밖을 가리켜요.") from exc
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__ASSERT_INSIDE_ROOT_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__EXPORT_PAYLOAD_START ===
def _export_payload(payload: VisualCardsDict, approved: list[VisualCardDict]) -> _ExportPayload:
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "provider": payload["provider"],
        "card_count": len(approved),
        "cards": approved,
    }
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__EXPORT_PAYLOAD_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__WRITE_PROMPT_PACK_START ===
def _write_prompt_pack(
    root: Path,
    slug: str,
    payload: VisualCardsDict,
    approved: list[VisualCardDict],
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__WRITE_PROMPT_PACK_END ===
) -> CardNewsPromptPack:
    prompt_dir = _safe_prompt_dir(root, slug)
    return write_card_news_prompt_pack(prompt_dir, payload, approved)


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__CARD_NEWS_SLUG_START ===
def _card_news_slug(slug_source: str) -> str:
    slug = safe_plan_slug(slug_source)
    if len(slug) <= _MAX_CARD_NEWS_SLUG_CHARS:
        return slug
    digest = sha1(slug.encode("utf-8")).hexdigest()[:8]
    prefix = slug[: _MAX_CARD_NEWS_SLUG_CHARS - len(digest) - 1].strip(" .-")
    return f"{prefix}-{digest}" if prefix else f"card-news-{digest}"
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__CARD_NEWS_SLUG_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__UNIQUE_CARD_NEWS_RELATIVE_PATH_START ===
def _unique_card_news_relative_path(root: Path, filename: str) -> Path:
    relative = Path(".vibelign") / "reports" / "card-news" / filename
    if not (root / relative).exists():
        return relative
    stem = relative.stem
    suffix = relative.suffix
    parent = relative.parent
    index = 2
    while True:
        next_relative = parent / f"{stem}-{index}{suffix}"
        if not (root / next_relative).exists():
            return next_relative
        index += 1
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__UNIQUE_CARD_NEWS_RELATIVE_PATH_END ===


# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SLUG_SOURCE_START ===
def _slug_source(cards: list[VisualCardDict]) -> str:
    first = cards[0]
    return first["title"] or first["id"] or "card-news"
# === ANCHOR: REPORT_CARD_NEWS_EXPORT__SLUG_SOURCE_END ===
# === ANCHOR: REPORT_CARD_NEWS_EXPORT_END ===
