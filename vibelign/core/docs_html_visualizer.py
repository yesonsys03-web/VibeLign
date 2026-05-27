# === ANCHOR: DOCS_HTML_VISUALIZER_START ===
from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import docs_cache as _DOCS_CACHE
from . import docs_visualizer as _DOCS_VISUALIZER

RAW_HTML_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-src 'none'"


@dataclass(frozen=True)
# === ANCHOR: DOCS_HTML_VISUALIZER_DOCSHTMLARTIFACT_START ===
class DocsHtmlArtifact:
    source_path: str
    source_hash: str
    generated_at: str
    generator_version: str
    schema_version: int
    title: str
    html: str
    csp: str = RAW_HTML_CSP
    mode: str = "raw_html"

    # === ANCHOR: DOCS_HTML_VISUALIZER_TO_DICT_START ===
    def to_dict(self) -> dict[str, Any]:
# === ANCHOR: DOCS_HTML_VISUALIZER_DOCSHTMLARTIFACT_END ===
        return asdict(self)
    # === ANCHOR: DOCS_HTML_VISUALIZER_TO_DICT_END ===


# === ANCHOR: DOCS_HTML_VISUALIZER__TITLE_FROM_TEXT_START ===
def _title_from_text(source_path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or source_path.stem
        if stripped:
            return stripped[:80]
    return source_path.stem.replace("-", " ").replace("_", " ").strip() or source_path.name
# === ANCHOR: DOCS_HTML_VISUALIZER__TITLE_FROM_TEXT_END ===


# === ANCHOR: DOCS_HTML_VISUALIZER__INLINE_MARKDOWN_HTML_START ===
def _inline_markdown_html(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
# === ANCHOR: DOCS_HTML_VISUALIZER__INLINE_MARKDOWN_HTML_END ===


# === ANCHOR: DOCS_HTML_VISUALIZER__MARKDOWNISH_TO_RAW_HTML_START ===
def _markdownish_to_raw_html(text: str) -> str:
    blocks: list[str] = []
    in_code = False
    code_lines: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []

    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_PARAGRAPH_START ===
    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline_markdown_html(' '.join(paragraph))}</p>")
            paragraph.clear()
    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_PARAGRAPH_END ===

    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_LIST_START ===
    def flush_list() -> None:
        if list_items:
            items = "".join(f"<li>{item}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
            list_items.clear()
    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_LIST_END ===

    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_TABLE_START ===
    def flush_table() -> None:
        if table_rows:
            rows = "".join(
                "<tr>" + "".join(f"<td>{_inline_markdown_html(cell)}</td>" for cell in row) + "</tr>"
                for row in table_rows
            )
            blocks.append(f"<table>{rows}</table>")
            table_rows.clear()
    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_TABLE_END ===

    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_STRUCTURAL_BLOCKS_START ===
    def flush_structural_blocks() -> None:
        flush_paragraph()
        flush_list()
        flush_table()
    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_STRUCTURAL_BLOCKS_END ===

    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_CODE_START ===
    def flush_code() -> None:
        if code_lines:
            code_text = "\n".join(code_lines)
            blocks.append(f"<pre><code>{html.escape(code_text)}</code></pre>")
            code_lines.clear()
    # === ANCHOR: DOCS_HTML_VISUALIZER_FLUSH_CODE_END ===

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_structural_blocks()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_structural_blocks()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_structural_blocks()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{_inline_markdown_html(heading.group(2).strip())}</h{level}>")
            continue
        if re.fullmatch(r"\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?", stripped):
            flush_paragraph()
            flush_list()
            continue
        if "|" in stripped and stripped.startswith("|"):
            flush_paragraph()
            flush_list()
            table_rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
            continue
        bullet = re.match(r"^[-*]\s+(?:\[[ xX]\]\s+)?(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet or ordered:
            flush_paragraph()
            flush_table()
            list_items.append(_inline_markdown_html((bullet or ordered).group(1).strip()))
            continue
        if stripped.startswith("<") and stripped.endswith(">"):
            flush_structural_blocks()
# === ANCHOR: DOCS_HTML_VISUALIZER__MARKDOWNISH_TO_RAW_HTML_END ===
            blocks.append(stripped)
            continue
        flush_list()
        flush_table()
        paragraph.append(stripped)

    flush_structural_blocks()
    if in_code:
        flush_code()
    return "\n".join(blocks)


# === ANCHOR: DOCS_HTML_VISUALIZER_BUILD_RAW_HTML_DOCUMENT_START ===
def build_raw_html_document(source_path: Path, text: str) -> str:
    title = _title_from_text(source_path, text)
    body = _markdownish_to_raw_html(text)
    return f"""<!doctype html>
# === ANCHOR: DOCS_HTML_VISUALIZER_BUILD_RAW_HTML_DOCUMENT_END ===
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta http-equiv=\"Content-Security-Policy\" content=\"{RAW_HTML_CSP}\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(title)} Raw HTML Canvas</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin: 0; padding: 28px; font-family: Georgia, \"Times New Roman\", serif; background: linear-gradient(135deg, #fff8df, #f3ead2); color: #1a1a1a; }}
    main {{ max-width: 920px; margin: 0 auto; border: 2px solid #1a1a1a; box-shadow: 6px 6px 0 #1a1a1a; background: #fffdf7; padding: clamp(22px, 4vw, 42px); }}
    h1, h2, h3, h4 {{ font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; line-height: 1.08; letter-spacing: -0.03em; margin: 1.25em 0 0.45em; }}
    h1:first-child, h2:first-child, h3:first-child {{ margin-top: 0; }}
    h1 {{ font-size: clamp(34px, 6vw, 64px); border-bottom: 4px solid #1a1a1a; padding-bottom: 12px; }}
    h2 {{ font-size: clamp(25px, 4vw, 42px); }}
    h3 {{ font-size: clamp(20px, 3vw, 30px); }}
    p {{ font-size: 18px; line-height: 1.82; margin: 0 0 1em; }}
    ul {{ display: grid; gap: 10px; padding: 0; margin: 0 0 1.2em; list-style: none; }}
    li {{ position: relative; padding: 12px 14px 12px 42px; border: 2px solid #1a1a1a; background: #fff4a8; box-shadow: 3px 3px 0 #1a1a1a; font-size: 17px; line-height: 1.55; }}
    li::before {{ content: \"\"; position: absolute; left: 14px; top: 1.05em; width: 12px; height: 12px; border: 2px solid #1a1a1a; border-radius: 50%; background: #4dff91; }}
    code {{ font-family: \"IBM Plex Mono\", ui-monospace, SFMono-Regular, Menlo, monospace; background: #f0eadb; padding: 0.08em 0.32em; }}
    pre {{ overflow-x: auto; background: #171a13; color: #7dff6b; padding: 16px; border: 2px solid #1a1a1a; box-shadow: 3px 3px 0 #1a1a1a; }}
    pre code {{ background: transparent; padding: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1em 0 1.3em; font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
    td {{ border: 2px solid #1a1a1a; padding: 10px 12px; vertical-align: top; }}
    tr:nth-child(odd) td {{ background: #e7ddff; }}
    tr:nth-child(even) td {{ background: #fff; }}
  </style>
</head>
<body>
  <main data-vibelign-raw-html=\"true\">
    {body}
  </main>
</body>
</html>"""


# === ANCHOR: DOCS_HTML_VISUALIZER_BUILD_DOCS_HTML_ARTIFACT_START ===
def build_docs_html_artifact(source_path: Path) -> DocsHtmlArtifact:
    resolved = source_path.resolve()
    text = _DOCS_CACHE.read_document_text(resolved)
    return DocsHtmlArtifact(
        source_path=resolved.as_posix(),
        source_hash=_DOCS_CACHE.compute_source_hash_from_text(text),
        generated_at=_DOCS_VISUALIZER.source_generated_at(resolved),
        generator_version=_DOCS_CACHE.DOCS_HTML_GENERATOR_VERSION,
        schema_version=_DOCS_CACHE.DOCS_HTML_SCHEMA_VERSION,
        title=_title_from_text(resolved, text),
        html=build_raw_html_document(resolved, text),
    )
# === ANCHOR: DOCS_HTML_VISUALIZER_BUILD_DOCS_HTML_ARTIFACT_END ===
# === ANCHOR: DOCS_HTML_VISUALIZER_END ===
