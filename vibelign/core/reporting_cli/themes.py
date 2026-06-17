# === ANCHOR: THEMES_START ===
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    html_css: str
    accent: str
    ink: str
    paper: str
    heading_font: str
    body_font: str


THEME_IDS: tuple[str, ...] = ("classic", "minimal", "executive", "compact", "pastel")

_CLASSIC_CSS = """
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

_MINIMAL_CSS = """
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

_EXECUTIVE_CSS = """
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

_COMPACT_CSS = """
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

_PASTEL_CSS = """
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

THEMES: dict[str, Theme] = {
    "classic": Theme("classic", "클래식", _CLASSIC_CSS, "#9B1B1B", "#1A1A1A", "#F7F7F2",
                     '"Noto Serif KR", serif', '"Noto Serif KR", serif'),
    "minimal": Theme("minimal", "모던 미니멀", _MINIMAL_CSS, "#444444", "#222222", "#FFFFFF",
                     '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    "executive": Theme("executive", "임원 보고형", _EXECUTIVE_CSS, "#1B3A6B", "#1C2430", "#FFFFFF",
                       '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    "compact": Theme("compact", "컴팩트", _COMPACT_CSS, "#2F6F46", "#222222", "#FFFFFF",
                     '"Apple SD Gothic Neo", sans-serif', '"Apple SD Gothic Neo", sans-serif'),
    "pastel": Theme("pastel", "부드러운 파스텔", _PASTEL_CSS, "#C97B5A", "#4A3F35", "#FBF6EE",
                    '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
}


def get_theme(theme_id: str) -> Theme:
    """테마 조회. 모르는/빈 id 는 classic 으로 폴백한다(렌더가 안 깨지게)."""
    return THEMES.get(theme_id) or THEMES["classic"]
# === ANCHOR: THEMES_END ===
