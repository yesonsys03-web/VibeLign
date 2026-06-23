# === ANCHOR: REPORT_CARD_NEWS_SKETCH_START ===
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Final

from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict

# Single source of truth for the sketch marker attribute. Asset provenance classification
# (report_card_news_asset_generator._asset_source) imports this so the renderer and the
# classifier can't drift out of sync.
SKETCH_MARKER_ATTR: Final = "data-sketch-symbols"


@dataclass(frozen=True, slots=True)
class _SketchSymbol:
    key: str
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SketchDescriptor:
    symbols: tuple[_SketchSymbol, _SketchSymbol, _SketchSymbol]
    color_shift: int


_SYMBOLS: tuple[_SketchSymbol, ...] = (
    _SketchSymbol("bell", "알림", ("알람", "알림", "通知", "notification", "reminder", "울림", "푸시")),
    _SketchSymbol("calendar", "일정", ("일정", "캘린더", "날짜", "반복", "예약", "schedule", "calendar", "date")),
    _SketchSymbol("checklist", "체크리스트", ("체크", "할일", "작업", "태스크", "todo", "task", "목록", "추가", "삭제", "수정")),
    _SketchSymbol("people", "사용자", ("사용자", "고객", "대상", "팀", "persona", "user", "customer", "member")),
    _SketchSymbol("board", "기획 보드", ("기획", "결정", "선택", "흐름", "로드맵", "plan", "decision", "roadmap", "workflow")),
    _SketchSymbol("phone", "앱 화면", ("앱", "모바일", "화면", "버튼", "ui", "ux", "app", "mobile", "screen")),
    _SketchSymbol("chart", "데이터", ("데이터", "분석", "통계", "지표", "보고서", "metric", "chart", "data", "analytics")),
    _SketchSymbol("document", "문서", ("문서", "기획안", "정책", "요구사항", "spec", "document", "report", "proposal", "policy")),
    _SketchSymbol("lock", "보안", ("보안", "로그인", "인증", "권한", "security", "login", "auth", "permission")),
    _SketchSymbol("wallet", "결제", ("결제", "가격", "환불", "매출", "구독", "payment", "price", "refund", "revenue", "subscription")),
    _SketchSymbol("chat", "대화", ("대화", "메시지", "문의", "피드백", "chat", "message", "feedback", "support")),
    _SketchSymbol("map", "위치", ("위치", "지도", "장소", "경로", "location", "map", "route", "place")),
)

_PALETTE = ("#FFD84D", "#FF4D4D", "#4C9BE8", "#6CCB8E", "#FF6B2C")


def render_card_sketch_svg(card: VisualCardDict) -> str:
    descriptor = _describe_card(card)
    symbols = descriptor.symbols
    data_symbols = ",".join(symbol.key for symbol in symbols)
    aria = "카드뉴스 그림: " + ", ".join(symbol.label for symbol in symbols)
    colors = _colors(descriptor.color_shift)
    return f"""<svg viewBox="0 0 320 150" role="img" aria-label="{aria}" {SKETCH_MARKER_ATTR}="{data_symbols}">
<rect x="16" y="18" width="288" height="110" rx="16" fill="#FFF9DA" stroke="#1B1714" stroke-width="4"/>
<path d="M55 116 C95 100 126 128 164 112 S235 98 278 116" fill="none" stroke="{colors[2]}" stroke-width="5" stroke-linecap="round"/>
<path d="M92 76 C120 54 194 54 226 76" fill="none" stroke="#1B1714" stroke-width="4" stroke-linecap="round" stroke-dasharray="8 9"/>
{_symbol_svg(symbols[0].key, 72, 74, colors[0], 1.0)}
{_symbol_svg(symbols[1].key, 160, 66, colors[1], 1.08)}
{_symbol_svg(symbols[2].key, 248, 74, colors[3], 1.0)}
<circle cx="45" cy="38" r="7" fill="{colors[4]}" stroke="#1B1714" stroke-width="3"/>
<path d="M279 35 l7 13 13 5 -13 5 -7 13 -7 -13 -13 -5 13 -5z" fill="{colors[0]}" stroke="#1B1714" stroke-width="3"/>
</svg>"""


def _describe_card(card: VisualCardDict) -> _SketchDescriptor:
    text = " ".join((card["title"], card["body"], card["caption"], card["visual_prompt"], card["image"]["prompt"])).lower()
    scored = [
        (sum(1 for keyword in symbol.keywords if keyword.lower() in text), index, symbol)
        for index, symbol in enumerate(_SYMBOLS)
    ]
    selected = [symbol for score, _, symbol in sorted(scored, key=lambda item: (-item[0], item[1])) if score > 0]
    digest = sha1(text.encode("utf-8")).hexdigest()
    while len(selected) < 3:
        index = int(digest[(len(selected) * 2) : (len(selected) * 2) + 2], 16) % len(_SYMBOLS)
        fallback = _SYMBOLS[index]
        if fallback not in selected:
            selected.append(fallback)
        else:
            selected.extend(symbol for symbol in _SYMBOLS if symbol not in selected)
    return _SketchDescriptor(symbols=tuple(selected[:3]), color_shift=int(digest[:2], 16) % len(_PALETTE))


def _colors(shift: int) -> tuple[str, str, str, str, str]:
    shifted = [_PALETTE[(index + shift) % len(_PALETTE)] for index in range(len(_PALETTE))]
    return shifted[0], shifted[1], shifted[2], shifted[3], shifted[4]


def _symbol_svg(symbol: str, cx: int, cy: int, color: str, scale: float) -> str:
    size = 44 * scale
    x = cx - size / 2
    y = cy - size / 2
    if symbol == "bell":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<path d="M22 8 C11 8 8 17 8 28 v8 l-6 7 h40 l-6-7 v-8 C36 17 33 8 22 8z" fill="{color}" stroke="#1B1714" stroke-width="4" stroke-linejoin="round"/>
<path d="M17 45 C19 52 25 52 27 45" fill="none" stroke="#1B1714" stroke-width="4" stroke-linecap="round"/>
</g>"""
    if symbol == "calendar":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="4" y="8" width="40" height="34" rx="6" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<path d="M4 19 h40" stroke="#1B1714" stroke-width="4"/><path d="M14 4 v11 M34 4 v11" stroke="#1B1714" stroke-width="4" stroke-linecap="round"/>
<rect x="13" y="26" width="8" height="8" fill="{color}" stroke="#1B1714" stroke-width="3"/><rect x="27" y="26" width="8" height="8" fill="#FFFFFF" stroke="#1B1714" stroke-width="3"/>
</g>"""
    if symbol == "checklist":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="5" y="5" width="38" height="40" rx="6" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<path d="M13 17 l5 5 9-11 M13 32 l5 5 15-17" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M29 35 h7" stroke="#1B1714" stroke-width="4" stroke-linecap="round"/>
</g>"""
    if symbol == "people":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<circle cx="16" cy="17" r="10" fill="{color}" stroke="#1B1714" stroke-width="4"/><circle cx="32" cy="19" r="9" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<path d="M5 43 C8 30 22 29 27 43" fill="{color}" stroke="#1B1714" stroke-width="4"/><path d="M22 43 C24 33 39 32 43 43" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
</g>"""
    if symbol == "board":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="4" y="8" width="42" height="32" rx="5" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<rect x="11" y="15" width="11" height="9" fill="{color}" stroke="#1B1714" stroke-width="3"/><rect x="27" y="15" width="11" height="9" fill="#FFFFFF" stroke="#1B1714" stroke-width="3"/>
<path d="M13 32 h24" stroke="#1B1714" stroke-width="4" stroke-linecap="round"/>
</g>"""
    if symbol == "phone":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="12" y="3" width="26" height="44" rx="7" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<rect x="18" y="12" width="14" height="18" fill="{color}" stroke="#1B1714" stroke-width="3"/><circle cx="25" cy="39" r="3" fill="#1B1714"/>
</g>"""
    if symbol == "chart":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="5" y="7" width="40" height="36" rx="6" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/>
<path d="M13 34 v-9 M25 34 v-17 M37 34 v-24" stroke="{color}" stroke-width="7" stroke-linecap="round"/>
</g>"""
    if symbol == "lock":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="8" y="22" width="34" height="24" rx="6" fill="{color}" stroke="#1B1714" stroke-width="4"/><path d="M16 22 v-7 C16 4 34 4 34 15 v7" fill="none" stroke="#1B1714" stroke-width="5" stroke-linecap="round"/>
<circle cx="25" cy="34" r="4" fill="#1B1714"/>
</g>"""
    if symbol == "wallet":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<rect x="5" y="13" width="40" height="28" rx="7" fill="#FFFFFF" stroke="#1B1714" stroke-width="4"/><rect x="25" y="20" width="20" height="14" rx="5" fill="{color}" stroke="#1B1714" stroke-width="4"/>
<circle cx="35" cy="27" r="3" fill="#1B1714"/>
</g>"""
    if symbol == "chat":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<path d="M6 10 h38 v25 H25 l-11 9 v-9 H6z" fill="#FFFFFF" stroke="#1B1714" stroke-width="4" stroke-linejoin="round"/>
<circle cx="17" cy="23" r="4" fill="{color}"/><circle cx="27" cy="23" r="4" fill="{color}"/><circle cx="37" cy="23" r="4" fill="{color}"/>
</g>"""
    if symbol == "map":
        return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<path d="M25 47 C14 34 10 26 10 18 C10 8 18 3 25 3 C32 3 40 8 40 18 C40 26 36 34 25 47z" fill="{color}" stroke="#1B1714" stroke-width="4"/>
<circle cx="25" cy="18" r="6" fill="#FFFFFF" stroke="#1B1714" stroke-width="3"/>
</g>"""
    return f"""<g transform="translate({x:.1f} {y:.1f}) scale({scale:.2f})">
<path d="M10 4 h23 l9 9 v31 H10z" fill="#FFFFFF" stroke="#1B1714" stroke-width="4" stroke-linejoin="round"/>
<path d="M33 4 v10 h9 M17 24 h18 M17 34 h14" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
</g>"""


# === ANCHOR: REPORT_CARD_NEWS_SKETCH_END ===
