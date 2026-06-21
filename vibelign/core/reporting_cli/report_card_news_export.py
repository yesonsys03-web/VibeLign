from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import TypedDict

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli.report_card_news_html import render_card_news_html
from vibelign.core.planning_cli.storage import safe_plan_slug
from vibelign.core.reporting_cli.report_card_news_prompts import (
    CardNewsPromptPack,
    write_card_news_prompt_pack,
)
from vibelign.core.reporting_cli.report_card_news_payload import load_visual_cards_payload
from vibelign.core.reporting_cli.report_visual_cards import (
    VisualCardDict,
    VisualCardsDict,
)

EXPORT_SCHEMA_VERSION = "report-card-news-export-v1"
_MAX_CARD_NEWS_SLUG_CHARS = 80


class CardNewsExportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CardNewsExport:
    json_path: Path
    html_path: Path
    storyboard_path: Path
    prompt_dir: Path
    prompt_paths: list[Path]
    card_count: int


class _ExportPayload(TypedDict):
    schema_version: str
    provider: str
    card_count: int
    cards: list[VisualCardDict]


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
    export_json = json.dumps(_export_payload(payload, approved), ensure_ascii=False, indent=2)
    _ = json_path.write_text(f"{export_json}\n", encoding="utf-8")
    _ = html_path.write_text(render_card_news_html(payload, approved, root, html_path.parent), encoding="utf-8")
    prompt_pack = _write_prompt_pack(root, slug, payload, approved)
    return CardNewsExport(
        json_path=json_path,
        html_path=html_path,
        storyboard_path=json_path,
        prompt_dir=prompt_pack.prompt_dir,
        prompt_paths=prompt_pack.prompt_paths,
        card_count=len(approved),
    )


def _safe_card_news_dir(root: Path) -> Path:
    out_dir = root / ".vibelign" / "reports" / "card-news"
    _assert_inside_root(root, out_dir)
    return out_dir


def _safe_card_news_path(root: Path, slug: str, suffix: str) -> Path:
    relative = _unique_card_news_relative_path(root, f"{slug}-card-news{suffix}")
    path = root / relative
    _assert_inside_root(root, path)
    return path


def _safe_prompt_dir(root: Path, slug: str) -> Path:
    path = root / ".vibelign" / "reports" / "card-news" / "prompts" / f"{slug}-card-news"
    _assert_inside_root(root, path)
    return path


def _assert_inside_root(root: Path, path: Path) -> None:
    try:
        _ = path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise CardNewsExportError("카드뉴스 출력 경로가 프로젝트 밖을 가리켜요.") from exc


def _export_payload(payload: VisualCardsDict, approved: list[VisualCardDict]) -> _ExportPayload:
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "provider": payload["provider"],
        "card_count": len(approved),
        "cards": approved,
    }


def _write_prompt_pack(
    root: Path,
    slug: str,
    payload: VisualCardsDict,
    approved: list[VisualCardDict],
) -> CardNewsPromptPack:
    prompt_dir = _safe_prompt_dir(root, slug)
    return write_card_news_prompt_pack(prompt_dir, payload, approved)


def _card_news_slug(slug_source: str) -> str:
    slug = safe_plan_slug(slug_source)
    if len(slug) <= _MAX_CARD_NEWS_SLUG_CHARS:
        return slug
    digest = sha1(slug.encode("utf-8")).hexdigest()[:8]
    prefix = slug[: _MAX_CARD_NEWS_SLUG_CHARS - len(digest) - 1].strip(" .-")
    return f"{prefix}-{digest}" if prefix else f"card-news-{digest}"


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


def _slug_source(cards: list[VisualCardDict]) -> str:
    first = cards[0]
    return first["title"] or first["id"] or "card-news"
