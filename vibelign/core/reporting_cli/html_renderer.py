from __future__ import annotations

from html import escape

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.templates import REPORT_TYPE_LABELS
from vibelign.core.reporting_cli.themes import get_theme

_HEAD_OPEN = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<title>'
_HEAD_MID = "</title>\n<style>"
_HEAD_CLOSE = "\n</style>\n</head>\n<body>"


def _head(title: str, css: str) -> str:
    """테마 CSS 를 끼운 <head>…<body> 를 만든다. 시맨틱 HTML 구조는 테마와 무관하게 동일."""
    return f"{_HEAD_OPEN}{title}{_HEAD_MID}{css}{_HEAD_CLOSE}"


_TAIL = "</body>\n</html>"


def _render_block(block: Block) -> str:
    if block.kind == "bullets":
        items = "".join(f"<li>{escape(item)}</li>" for item in block.items)
        return f"<ul>{items}</ul>"
    if block.kind == "summary":
        return f'<p class="summary">{escape(block.text)}</p>'
    return f"<p>{escape(block.text)}</p>"


def _render_section(section: Section) -> str:
    blocks = "\n".join(_render_block(b) for b in section.blocks)
    return f"<section>\n<h2>{escape(section.heading)}</h2>\n{blocks}\n</section>"


def render_html(model: ReportModel, theme: str = "classic") -> str:
    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    css = get_theme(theme).html_css
    parts = [
        _head(escape(model.title), css),
        f"<h1>{escape(model.title)}</h1>",
        f'<p class="meta">{escape(label)} · {escape(model.date)}</p>',
    ]
    parts.extend(_render_section(s) for s in model.sections)
    parts.append(_TAIL)
    return "\n".join(parts)
