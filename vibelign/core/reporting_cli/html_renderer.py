# === ANCHOR: HTML_RENDERER_START ===
from __future__ import annotations

from html import escape

from vibelign.core.reporting_cli.font_sizes import (
    ReportFontSizes,
    font_size_override_css,
)
from vibelign.core.reporting_cli.fonts import ReportFonts, font_family_override_css
from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.templates import meta_line
from vibelign.core.reporting_cli.themes import get_theme

_HEAD_OPEN = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<title>'
_HEAD_MID = "</title>\n<style>"
_HEAD_CLOSE = "\n</style>\n</head>\n<body>"


# === ANCHOR: HTML_RENDERER__HEAD_START ===
def _head(title: str, css: str) -> str:
    """테마 CSS 를 끼운 <head>…<body> 를 만든다. 시맨틱 HTML 구조는 테마와 무관하게 동일."""
    return f"{_HEAD_OPEN}{title}{_HEAD_MID}{css}{_HEAD_CLOSE}"
# === ANCHOR: HTML_RENDERER__HEAD_END ===


_TAIL = "</body>\n</html>"


# === ANCHOR: HTML_RENDERER__RENDER_BLOCK_START ===
def _render_block(block: Block) -> str:
    if block.kind == "bullets":
        items = "".join(f"<li>{escape(item)}</li>" for item in block.items)
        return f"<ul>{items}</ul>"
    if block.kind == "summary":
        return f'<p class="summary">{escape(block.text)}</p>'
    return f"<p>{escape(block.text)}</p>"
# === ANCHOR: HTML_RENDERER__RENDER_BLOCK_END ===


# === ANCHOR: HTML_RENDERER__RENDER_SECTION_START ===
def _render_section(section: Section) -> str:
    blocks = "\n".join(_render_block(b) for b in section.blocks)
    return f"<section>\n<h2>{escape(section.heading)}</h2>\n{blocks}\n</section>"
# === ANCHOR: HTML_RENDERER__RENDER_SECTION_END ===


# === ANCHOR: HTML_RENDERER_RENDER_HTML_START ===
def render_html(
    model: ReportModel,
    theme: str = "classic",
    font_sizes: ReportFontSizes | None = None,
    fonts: ReportFonts | None = None,
) -> str:
    theme_obj = get_theme(theme)
    css = theme_obj.html_css
    if font_sizes is not None:
        css = "\n".join(part for part in (css, font_size_override_css(font_sizes)) if part)
    if fonts is not None:
        font_css = font_family_override_css(
            fonts,
            default_heading=theme_obj.heading_font,
            default_body=theme_obj.body_font,
        )
        css = "\n".join(part for part in (css, font_css) if part)
    parts = [
        _head(escape(model.title), css),
        f"<h1>{escape(model.title)}</h1>",
        f'<p class="meta">{escape(meta_line(model))}</p>',
    ]
    parts.extend(_render_section(s) for s in model.sections)
    parts.append(_TAIL)
    return "\n".join(parts)
# === ANCHOR: HTML_RENDERER_RENDER_HTML_END ===
# === ANCHOR: HTML_RENDERER_END ===
