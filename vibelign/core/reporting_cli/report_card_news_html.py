# === ANCHOR: REPORT_CARD_NEWS_HTML_START ===
from __future__ import annotations

import os
from dataclasses import dataclass
from html import escape
from pathlib import Path

from vibelign.core.reporting_cli.report_visual_cards import (
    VisualCardDict,
    VisualCardsDict,
)
from vibelign.core.reporting_cli.report_card_news_sketch import render_card_sketch_svg


@dataclass(frozen=True, slots=True)
class _RenderContext:
    root: Path
    html_dir: Path


_GENERIC_TITLES = {"개요", "핵심 내용", "주요 결정", "대상 / 배경"}


def render_card_news_html(
    payload: VisualCardsDict,
    cards: list[VisualCardDict],
    root: Path,
    html_dir: Path,
) -> str:
    context = _RenderContext(root=root, html_dir=html_dir)
    title = _poster_title(cards)
    subtitle = _poster_subtitle(cards)
    panels = "\n".join(_render_panel(card, index, context) for index, card in enumerate(cards, 1))
    flow = "\n".join(_render_flow_item(card, index) for index, card in enumerate(cards[:6], 1))
    message = _core_message(cards)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · 카드뉴스</title>
<style>
:root {{ --paper:#FFFFFF; --page:#EEF1F4; --grid:#DCE4EA; --ink:#1B1714; --soft:#5F574E; --muted:#83796E; --yellow:#FFD84D; --red:#FF4D4D; --orange:#FF6B2C; --blue:#4C9BE8; --green:#6CCB8E; --shadow:7px 8px 0 var(--ink); }}
* {{ box-sizing:border-box; }}
body {{ margin:0; color:var(--ink); font-family:"Apple SD Gothic Neo","Pretendard","Malgun Gothic","Noto Sans KR",system-ui,sans-serif; background-color:var(--page); background-image:linear-gradient(var(--grid) 1px, transparent 1px), linear-gradient(90deg, var(--grid) 1px, transparent 1px); background-size:26px 26px; line-height:1.5; }}
main {{ max-width:1180px; margin:0 auto; padding:34px 24px 56px; }}
.poster {{ background:rgba(255,255,255,.92); border:4px solid var(--ink); box-shadow:var(--shadow); padding:28px; }}
.masthead {{ display:grid; grid-template-columns:1fr auto; gap:18px; align-items:start; border-bottom:5px solid var(--ink); padding-bottom:20px; margin-bottom:18px; }}
.kicker {{ display:inline-flex; width:max-content; border:3px solid var(--ink); border-radius:999px; background:var(--yellow); box-shadow:3px 3px 0 var(--ink); padding:5px 13px; color:var(--orange); font-size:13px; font-weight:950; letter-spacing:.04em; }}
h1 {{ margin:14px 0 8px; font-size:clamp(42px, 6vw, 74px); line-height:1.05; font-weight:950; letter-spacing:0; word-break:keep-all; }}
.subtitle {{ margin:0; max-width:54ch; color:var(--soft); font-size:clamp(17px, 2vw, 21px); font-weight:800; word-break:keep-all; }}
.meta {{ display:grid; gap:8px; min-width:190px; justify-items:end; font-size:13px; font-weight:900; color:var(--soft); }}
.meta strong {{ display:inline-flex; align-items:center; border:3px solid var(--ink); border-radius:999px; background:var(--paper); box-shadow:3px 3px 0 var(--ink); padding:8px 14px; color:var(--ink); font-size:15px; }}
.flow-strip {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin:0 0 20px; }}
.flow-step {{ border:3px solid var(--ink); background:#FFF9DA; padding:10px 12px; min-height:88px; display:grid; grid-template-rows:auto 1fr; gap:6px; box-shadow:3px 3px 0 var(--ink); }}
.flow-step b {{ color:var(--red); font-size:14px; }}
.flow-step span {{ font-size:14px; font-weight:900; line-height:1.35; word-break:keep-all; }}
.panel-grid {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:24px; align-items:stretch; }}
.panel {{ position:relative; background:var(--paper); border:4px solid var(--ink); box-shadow:6px 7px 0 var(--ink); padding:20px 18px 16px; min-height:368px; display:grid; grid-template-rows:auto auto 1fr auto; gap:12px; }}
.panel-no {{ position:absolute; left:-4px; top:-4px; min-width:58px; height:54px; padding:0 12px; display:grid; place-items:center; background:var(--ink); color:var(--paper); font-size:30px; font-weight:950; }}
.panel-title {{ margin:0 0 0 58px; min-height:42px; font-size:clamp(28px, 3vw, 36px); line-height:1.08; font-weight:950; word-break:keep-all; }}
.sketch {{ border:3px solid var(--ink); border-radius:12px; background:#FFFDF6; min-height:132px; display:grid; place-items:center; overflow:hidden; }}
.sketch svg {{ width:100%; max-width:290px; height:132px; display:block; }}
.panel-visual-img {{ width:100%; height:100%; min-height:132px; object-fit:cover; display:block; }}
.points {{ margin:0; padding:0; list-style:none; display:grid; gap:8px; }}
.points li {{ position:relative; padding-left:22px; font-size:clamp(16px, 1.9vw, 19px); line-height:1.38; font-weight:900; word-break:keep-all; }}
.points li::before {{ content:""; position:absolute; left:0; top:.55em; width:9px; height:9px; border:2px solid var(--ink); border-radius:999px; background:var(--yellow); }}
.caption {{ border-top:3px solid var(--ink); padding-top:9px; color:var(--soft); font-size:13px; font-weight:900; }}
.message-band {{ display:grid; grid-template-columns:auto 1fr; gap:20px; align-items:center; margin-top:24px; border:4px solid var(--red); background:#FFFDF6; padding:20px 22px; box-shadow:5px 6px 0 var(--ink); }}
.message-band b {{ display:block; font-size:32px; line-height:1.05; font-weight:950; color:var(--red); }}
.message-band p {{ margin:0; font-size:clamp(22px, 3vw, 34px); line-height:1.2; font-weight:950; word-break:keep-all; }}
.message-band mark {{ background:linear-gradient(transparent 52%, var(--yellow) 52%); padding:0 .08em; }}
.footer-note {{ margin:18px 0 0; text-align:right; color:var(--muted); font-size:12px; font-weight:800; }}
@media (max-width: 920px) {{ main {{ padding:18px 14px 42px; }} .poster {{ padding:20px; }} .masthead {{ grid-template-columns:1fr; }} .meta {{ justify-items:start; }} .panel-grid {{ grid-template-columns:1fr; }} .panel {{ min-height:auto; }} .panel-title {{ font-size:32px; }} .message-band {{ grid-template-columns:1fr; }} }}
@media print {{ body {{ background:#fff; }} main {{ padding:0; }} .poster,.panel,.flow-step,.message-band {{ box-shadow:none; }} .panel {{ break-inside:avoid; }} }}
</style>
</head>
<body>
<main>
<section class="poster" aria-label="카드뉴스 인포그래픽">
<header class="masthead">
<div>
<span class="kicker">기획 카드뉴스</span>
<h1>{escape(title)}</h1>
<p class="subtitle">{escape(subtitle)}</p>
</div>
<div class="meta">
<strong>REPORT CARD NEWS</strong>
<span>승인 카드 {len(cards)}개 · provider {escape(payload["provider"])}</span>
</div>
</header>
<section class="flow-strip" aria-label="요약 흐름">
{flow}
</section>
<section class="panel-grid" aria-label="카드뉴스 본문">
{panels}
</section>
<section class="message-band" aria-label="핵심 메시지">
<b>핵심<br>메시지</b>
<p>{message}</p>
</section>
<p class="footer-note">VibeLign 보고서 카드뉴스 HTML</p>
</section>
</main>
</body>
</html>
"""


def _render_flow_item(card: VisualCardDict, index: int) -> str:
    label = _card_heading(card)
    return f"""<article class="flow-step">
<b>{index:02d}</b>
<span>{escape(label)}</span>
</article>"""


def _render_panel(card: VisualCardDict, index: int, context: _RenderContext) -> str:
    points = "\n".join(f"<li>{escape(item)}</li>" for item in _body_lines(card["body"]))
    visual = _render_visual(card, context)
    return f"""<article class="panel" aria-label="{escape(_card_heading(card))}">
<div class="panel-no">{index}</div>
<h2 class="panel-title">{escape(_card_heading(card))}</h2>
<figure class="sketch">{visual}</figure>
<ul class="points">
{points}
</ul>
<div class="caption">{escape(card["caption"])}</div>
</article>"""


def _render_visual(card: VisualCardDict, context: _RenderContext) -> str:
    image_src = _safe_image_src(card, context)
    if image_src is not None:
        return f'<img class="panel-visual-img" src="{escape(image_src)}" alt="" loading="lazy">'
    return render_card_sketch_svg(card)


def _safe_image_src(card: VisualCardDict, context: _RenderContext) -> str | None:
    asset_path = card["image"]["asset_path"].strip()
    if not asset_path:
        return None
    candidate = Path(asset_path).expanduser()
    if not candidate.is_absolute():
        candidate = context.root / candidate
    try:
        resolved = candidate.resolve(strict=False)
        _ = resolved.relative_to(context.root)
    except (OSError, ValueError):
        return None
    if not resolved.exists():
        return None
    relative = os.path.relpath(resolved, context.html_dir.resolve(strict=False))
    return Path(relative).as_posix()


def _poster_title(cards: list[VisualCardDict]) -> str:
    first = cards[0]
    first_body = _first_body_phrase(first["body"])
    if first["title"] in _GENERIC_TITLES and first_body:
        return first_body
    return first["title"] or first_body or "카드뉴스 결과물"


def _poster_subtitle(cards: list[VisualCardDict]) -> str:
    count = len(cards)
    return f"보고서의 핵심 흐름을 누구나 빠르게 이해하도록 {count}장으로 정리했어요."


def _card_heading(card: VisualCardDict) -> str:
    return card["title"] or _first_body_phrase(card["body"]) or "요약"


def _first_body_phrase(body: str) -> str:
    lines = _body_lines(body)
    return lines[0] if lines else ""


def _body_lines(body: str) -> list[str]:
    raw_lines = [line.strip(" -•\t") for line in body.replace("。", ".").splitlines()]
    lines = _clean_body_lines(raw_lines)
    if len(lines) >= 2:
        return lines[:4]
    if body.strip():
        return _clean_body_lines([body.strip()])[:4]
    sentences = [item.strip() for item in body.replace("!", ".").replace("?", ".").split(".") if item.strip()]
    return _clean_body_lines(sentences)[:4] if sentences else ["요약 내용 없음"]


def _clean_body_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        for item in line.split(" / "):
            text = _clean_body_item(item)
            if text:
                cleaned.append(text)
    return cleaned


def _clean_body_item(item: str) -> str:
    return item.replace("**", "").replace("__", "").strip(" -•\t")


def _core_message(cards: list[VisualCardDict]) -> str:
    first = _poster_title(cards)
    return f"<mark>{escape(first)}</mark>의 핵심은 기능을 많이 나열하는 것이 아니라, 사용자가 바로 이해하고 실행할 흐름을 정하는 것입니다."


# === ANCHOR: REPORT_CARD_NEWS_HTML_END ===
