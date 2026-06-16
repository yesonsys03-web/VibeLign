from __future__ import annotations

from html import escape

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.templates import REPORT_TYPE_LABELS

_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ --ink: #1A1A1A; --paper: #F7F7F2; --accent: #9B1B1B; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Noto Serif KR", "Apple SD Gothic Neo", serif;
    color: var(--ink); background: var(--paper);
    max-width: 760px; margin: 0 auto; padding: 48px 40px; line-height: 1.7;
  }}
  h1 {{ font-size: 26px; border-bottom: 3px solid var(--accent); padding-bottom: 10px; }}
  h2 {{ font-size: 17px; color: var(--accent); margin-top: 28px; }}
  p.meta {{ color: #666; font-size: 13px; margin-top: 4px; }}
  p.summary {{ font-weight: 700; font-size: 16px; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  @media print {{
    body {{ background: #fff; max-width: none; padding: 0; }}
    h2 {{ break-after: avoid; }}
    section {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>"""

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


def render_html(model: ReportModel) -> str:
    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    parts = [
        _HEAD.format(title=escape(model.title)),
        f"<h1>{escape(model.title)}</h1>",
        f'<p class="meta">{escape(label)} · {escape(model.date)}</p>',
    ]
    parts.extend(_render_section(s) for s in model.sections)
    parts.append(_TAIL)
    return "\n".join(parts)
