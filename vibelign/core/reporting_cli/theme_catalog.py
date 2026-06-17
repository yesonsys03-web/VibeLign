# === ANCHOR: THEME_CATALOG_START ===
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Theme:
    id: str
    label: str
    html_css: str
    accent: str
    ink: str
    paper: str
    heading_font: str
    body_font: str


@dataclass(frozen=True, slots=True)
class Palette:
    id: str
    label: str
    accent: str
    ink: str
    paper: str
    tint: str


@dataclass(frozen=True, slots=True)
class Layout:
    id: str
    label: str
    max_width: int
    h1: str
    h2: str
    section: str
    summary: str
    body_font: str
    heading_font: str


@dataclass(frozen=True, slots=True)
class Density:
    id: str
    label: str
    padding: str
    line_height: str
    body_size: str
    section_gap: str


BASE_THEME_IDS: Final[tuple[str, ...]] = ("classic", "minimal", "executive", "compact", "pastel")

_CLASSIC_CSS: Final[str] = """
  :root { --ink:#1A1A1A; --paper:#F7F7F2; --accent:#9B1B1B; }
  * { box-sizing:border-box; }
  body { font-family:"Noto Serif KR","Apple SD Gothic Neo",serif; color:var(--ink); background:var(--paper);
         max-width:760px; margin:0 auto; padding:48px 40px; line-height:1.7; }
  h1 { font-size:26px; border-bottom:3px solid var(--accent); padding-bottom:10px; }
  h2 { font-size:17px; color:var(--accent); margin-top:28px; }
  p.meta { color:#666; font-size:13px; margin-top:4px; }
  p.summary { font-weight:700; font-size:16px; }
  ul { padding-left:20px; } li { margin:4px 0; }
  @media print { body { background:#fff; max-width:none; padding:0; } h2 { break-after:avoid; } section { break-inside:avoid; } }
"""

_MINIMAL_CSS: Final[str] = """
  :root { --ink:#222; --paper:#fff; --accent:#444; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif; color:var(--ink); background:var(--paper);
         max-width:720px; margin:0 auto; padding:64px 48px; line-height:1.8; letter-spacing:-0.01em; }
  h1 { font-size:28px; font-weight:800; }
  h2 { font-size:14px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:.08em; margin-top:36px; }
  p.meta { color:#999; font-size:12px; margin-top:6px; }
  p.summary { font-weight:600; font-size:16px; color:#000; }
  ul { padding-left:18px; } li { margin:6px 0; }
  section { border-top:1px solid #eee; padding-top:8px; }
  @media print { body { padding:0; max-width:none; } }
"""

_EXECUTIVE_CSS: Final[str] = """
  :root { --ink:#1c2430; --paper:#fff; --accent:#1B3A6B; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",sans-serif; color:var(--ink); background:var(--paper);
         max-width:800px; margin:0 auto; padding:0 0 48px; line-height:1.7; }
  h1 { font-size:30px; font-weight:900; color:#fff; background:var(--accent); margin:0; padding:36px 40px; }
  p.meta { color:#fff; background:var(--accent); margin:0; padding:0 40px 24px; font-size:13px; opacity:.85; }
  section { padding-left:40px; padding-right:40px; }
  h2 { font-size:18px; color:var(--accent); border-left:5px solid var(--accent); padding:2px 0 2px 12px; margin:30px 0 8px; }
  p.summary { font-weight:700; font-size:17px; background:#f0f4fa; padding:14px 16px; border-radius:6px; }
  ul { padding-left:20px; } li { margin:5px 0; }
  @media print { body { padding:0; } }
"""

_COMPACT_CSS: Final[str] = """
  :root { --ink:#222; --paper:#fff; --accent:#2f6f46; }
  * { box-sizing:border-box; }
  body { font-family:"Apple SD Gothic Neo","Pretendard",sans-serif; color:var(--ink); background:var(--paper);
         max-width:680px; margin:0 auto; padding:28px 28px; line-height:1.45; font-size:13px; }
  h1 { font-size:20px; border-bottom:2px solid var(--accent); padding-bottom:6px; margin:0 0 4px; }
  h2 { font-size:13px; color:var(--accent); margin:16px 0 4px; font-weight:800; }
  p.meta { color:#777; font-size:11px; margin:0 0 8px; }
  p.summary { font-weight:700; }
  p { margin:4px 0; } ul { padding-left:16px; margin:4px 0; } li { margin:1px 0; }
  @media print { body { padding:0; } }
"""

_PASTEL_CSS: Final[str] = """
  :root { --ink:#4a3f35; --paper:#FBF6EE; --accent:#C97B5A; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",sans-serif; color:var(--ink); background:var(--paper);
         max-width:740px; margin:0 auto; padding:48px 40px; line-height:1.8; }
  h1 { font-size:26px; color:var(--accent); }
  h2 { font-size:16px; color:var(--accent); margin-top:28px; }
  p.meta { color:#a08e7d; font-size:13px; margin-top:4px; }
  p.summary { font-weight:700; background:#fff3e9; padding:12px 14px; border-radius:12px; }
  section { background:#fff; border-radius:14px; padding:6px 18px 12px; margin:14px 0; box-shadow:0 1px 4px rgba(0,0,0,.04); }
  ul { padding-left:20px; } li { margin:4px 0; }
  @media print { body { background:#fff; } section { box-shadow:none; } }
"""

BASE_THEMES: Final[tuple[Theme, ...]] = (
    Theme("classic", "클래식", _CLASSIC_CSS, "#9B1B1B", "#1A1A1A", "#F7F7F2", '"Noto Serif KR", serif', '"Noto Serif KR", serif'),
    Theme("minimal", "모던 미니멀", _MINIMAL_CSS, "#444444", "#222222", "#FFFFFF", '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    Theme("executive", "임원 보고형", _EXECUTIVE_CSS, "#1B3A6B", "#1C2430", "#FFFFFF", '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    Theme("compact", "컴팩트", _COMPACT_CSS, "#2F6F46", "#222222", "#FFFFFF", '"Apple SD Gothic Neo", sans-serif', '"Apple SD Gothic Neo", sans-serif'),
    Theme("pastel", "부드러운 파스텔", _PASTEL_CSS, "#C97B5A", "#4A3F35", "#FBF6EE", '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
)

PALETTES: Final[tuple[Palette, ...]] = (
    Palette("indigo", "인디고", "#3157A4", "#19233A", "#FFFFFF", "#EEF3FF"),
    Palette("teal", "틸", "#147A73", "#173331", "#FFFFFF", "#EAF7F4"),
    Palette("forest", "포레스트", "#2F6F46", "#1F2E24", "#FFFFFF", "#EEF7EF"),
    Palette("wine", "와인", "#8A2545", "#2B1720", "#FFFFFF", "#FFF0F5"),
    Palette("amber", "앰버", "#A75B12", "#2F2417", "#FFFFFF", "#FFF5E6"),
    Palette("slate", "슬레이트", "#475569", "#1E293B", "#FFFFFF", "#F1F5F9"),
    Palette("violet", "바이올렛", "#6D4AFF", "#221A3E", "#FFFFFF", "#F3F0FF"),
    Palette("coral", "코랄", "#C94F3D", "#3A1F1A", "#FFFFFF", "#FFF1ED"),
    Palette("olive", "올리브", "#687A2F", "#272D19", "#FFFFFF", "#F4F7E8"),
    Palette("mono", "모노", "#111827", "#111827", "#FFFFFF", "#F3F4F6"),
)

LAYOUTS: Final[tuple[Layout, ...]] = (
    Layout("plain", "기본형", 760, "font-size:27px;font-weight:850;border-bottom:3px solid var(--accent);padding-bottom:10px;", "font-size:17px;color:var(--accent);margin-top:28px;", "", "font-weight:750;font-size:16px;", '"Pretendard","Apple SD Gothic Neo",sans-serif', '"Pretendard","Apple SD Gothic Neo",sans-serif'),
    Layout("letter", "공문형", 720, "font-size:25px;font-weight:800;text-align:center;margin-bottom:6px;", "font-size:16px;color:var(--accent);border-bottom:1px solid var(--accent);padding-bottom:4px;margin-top:30px;", "", "font-weight:700;border-left:4px solid var(--accent);padding-left:12px;", '"Noto Serif KR","Apple SD Gothic Neo",serif', '"Noto Serif KR","Apple SD Gothic Neo",serif'),
    Layout("board", "임원형", 820, "font-size:30px;font-weight:900;color:#fff;background:var(--accent);margin:0;padding:34px 40px;", "font-size:18px;color:var(--accent);border-left:5px solid var(--accent);padding-left:12px;margin-top:30px;", "padding-left:40px;padding-right:40px;", "font-weight:800;background:var(--tint);padding:14px 16px;border-radius:6px;", '"Pretendard","Apple SD Gothic Neo",sans-serif', '"Pretendard","Apple SD Gothic Neo",sans-serif'),
    Layout("cards", "카드형", 760, "font-size:28px;font-weight:850;color:var(--accent);", "font-size:16px;color:var(--accent);margin-top:0;", "background:#fff;border:1px solid var(--tint);border-radius:12px;padding:10px 18px 14px;margin:14px 0;", "font-weight:750;background:var(--tint);padding:12px 14px;border-radius:10px;", '"Pretendard","Apple SD Gothic Neo",sans-serif', '"Pretendard","Apple SD Gothic Neo",sans-serif'),
    Layout("memo", "메모형", 680, "font-size:22px;font-weight:850;border-bottom:2px solid var(--accent);padding-bottom:6px;", "font-size:14px;color:var(--accent);margin:18px 0 4px;font-weight:850;", "", "font-weight:750;", '"Apple SD Gothic Neo","Pretendard",sans-serif', '"Apple SD Gothic Neo","Pretendard",sans-serif'),
)

DENSITIES: Final[tuple[Density, ...]] = (
    Density("balanced", "표준", "48px 40px", "1.7", "14px", "24px"),
    Density("dense", "촘촘", "30px 30px", "1.48", "13px", "14px"),
)


def _theme_css(layout: Layout, palette: Palette, density: Density) -> str:
    return f"""
  :root {{ --ink:{palette.ink}; --paper:{palette.paper}; --accent:{palette.accent}; --tint:{palette.tint}; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:{layout.body_font}; color:var(--ink); background:var(--paper);
         max-width:{layout.max_width}px; margin:0 auto; padding:{density.padding}; line-height:{density.line_height}; font-size:{density.body_size}; }}
  h1 {{ {layout.h1} }}
  h2 {{ {layout.h2} }}
  p.meta {{ color:#707070; font-size:12px; margin-top:6px; }}
  p.summary {{ {layout.summary} }}
  section {{ margin-top:{density.section_gap}; {layout.section} }}
  p {{ margin:6px 0; }} ul {{ padding-left:20px; }} li {{ margin:4px 0; }}
  @media print {{ body {{ background:#fff; max-width:none; padding:0; }} section {{ break-inside:avoid; }} h2 {{ break-after:avoid; }} }}
"""


def generated_themes() -> tuple[Theme, ...]:
    themes: list[Theme] = []
    for layout in LAYOUTS:
        for palette in PALETTES:
            for density in DENSITIES:
                theme_id = f"{layout.id}-{palette.id}-{density.id}"
                label = f"{layout.label} · {palette.label} · {density.label}"
                themes.append(
                    Theme(
                        theme_id,
                        label,
                        _theme_css(layout, palette, density),
                        palette.accent,
                        palette.ink,
                        palette.paper,
                        layout.heading_font,
                        layout.body_font,
                    )
                )
    return tuple(themes)


def all_themes() -> tuple[Theme, ...]:
    return (*BASE_THEMES, *generated_themes())
# === ANCHOR: THEME_CATALOG_END ===
