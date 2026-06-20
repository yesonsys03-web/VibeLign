from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha1
from html import escape
from pathlib import Path
from typing import TypedDict

from vibelign.core.project_root import resolve_project_root
from vibelign.core.planning_cli.storage import safe_plan_slug
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
    _ = json_path.write_text(json.dumps(_export_payload(payload, approved), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _ = html_path.write_text(_render_card_news_html(payload, approved), encoding="utf-8")
    return CardNewsExport(json_path=json_path, html_path=html_path, card_count=len(approved))


def _safe_card_news_dir(root: Path) -> Path:
    out_dir = root / ".vibelign" / "reports" / "card-news"
    _assert_inside_root(root, out_dir)
    return out_dir


def _safe_card_news_path(root: Path, slug: str, suffix: str) -> Path:
    relative = _unique_card_news_relative_path(root, f"{slug}-card-news{suffix}")
    path = root / relative
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


def _render_card_news_html(payload: VisualCardsDict, cards: list[VisualCardDict]) -> str:
    items = "\n".join(_render_card(card, index) for index, card in enumerate(cards, 1))
    title = "카드뉴스 결과물"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#FEFBF0; --white:#FFFFFF; --black:#1A1A1A; --gray:#666666; --primary:#F5621E; --green:#4DFF91; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--black); font-family:"Space Grotesk","Apple SD Gothic Neo","Noto Sans KR",system-ui,sans-serif; }}
main {{ max-width:1160px; margin:0 auto; padding:32px 20px 48px; }}
header {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:24px; }}
h1 {{ margin:0; font-size:28px; line-height:1.15; }}
.meta {{ margin:8px 0 0; color:var(--gray); font-size:12px; line-height:1.5; }}
.badge {{ border:2px solid var(--black); background:var(--primary); padding:8px 12px; font-weight:800; box-shadow:3px 3px 0 var(--black); white-space:nowrap; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:22px; align-items:start; }}
.card {{ border:3px solid var(--black); background:var(--white); padding:18px; box-shadow:6px 6px 0 var(--black); aspect-ratio:4/5; display:flex; flex-direction:column; gap:12px; overflow:hidden; }}
.topline {{ display:flex; align-items:center; justify-content:space-between; gap:10px; }}
.number {{ width:42px; height:42px; display:inline-flex; align-items:center; justify-content:center; border:3px solid var(--black); border-radius:999px; background:#FF4D4D; color:var(--white); font-size:22px; font-weight:950; }}
.series {{ border:2px solid var(--black); border-radius:999px; background:var(--bg); padding:5px 10px; font-size:11px; font-weight:900; }}
.doodle {{ display:flex; align-items:center; gap:10px; color:var(--primary); font-size:20px; font-weight:950; }}
.doodle span:nth-child(2) {{ flex:1; border-top:4px solid var(--black); transform:rotate(-1deg); }}
.title {{ margin:0; padding-bottom:10px; border-bottom:5px solid var(--black); font-size:30px; line-height:1.15; font-weight:950; word-break:keep-all; }}
.body {{ flex:1; border:2px solid var(--black); border-radius:12px; background:var(--bg); padding:14px 16px; }}
.body ul {{ margin:0; padding-left:20px; display:grid; gap:9px; }}
.body li {{ font-size:16px; line-height:1.55; font-weight:750; word-break:keep-all; }}
.caption {{ border:2px solid var(--black); border-radius:999px; background:var(--white); padding:9px 12px; font-size:13px; font-weight:900; }}
.message {{ border:2px solid var(--black); border-radius:12px; background:#FFFFFF; padding:10px 12px; font-size:13px; font-weight:900; }}
@media (max-width: 520px) {{ main {{ padding:20px 12px 32px; }} header {{ display:block; }} .badge {{ display:inline-block; margin-top:12px; }} .card {{ aspect-ratio:auto; min-height:440px; }} .title {{ font-size:25px; }} }}
</style>
</head>
<body>
<main>
<header>
<div>
<h1>{title}</h1>
<p class="meta">승인 카드 {len(cards)}개 · provider {escape(payload["provider"])}</p>
</div>
<div class="badge">완료</div>
</header>
<section class="grid" aria-label="확정된 카드뉴스">
{items}
</section>
</main>
</body>
</html>
"""


def _render_card(card: VisualCardDict, index: int) -> str:
    body_items = "\n".join(f"<li>{escape(item)}</li>" for item in _body_lines(card["body"]))
    return f"""<article class="card" aria-label="{escape(card["title"])} 카드">
<div class="topline">
<span class="number">{index}</span>
<span class="series">REPORT CARD NEWS</span>
</div>
<div class="doodle" aria-hidden="true"><span>★</span><span></span><span>✦</span></div>
<h2 class="title">{escape(card["title"])}</h2>
<div class="body"><ul>
{body_items}
</ul></div>
<div class="caption">{escape(card["caption"])}</div>
<div class="message">핵심만 빠르게 읽는 보고서 요약 카드</div>
</article>"""


def _body_lines(body: str) -> list[str]:
    raw_lines = [line.strip(" -•\t") for line in body.replace("。", ".").splitlines()]
    lines = [line for line in raw_lines if line]
    if len(lines) >= 2:
        return lines[:4]
    if body.strip():
        return [body.strip()]
    sentences = [item.strip() for item in body.replace("!", ".").replace("?", ".").split(".") if item.strip()]
    return sentences[:4] if sentences else [body.strip() or "요약 내용 없음"]
