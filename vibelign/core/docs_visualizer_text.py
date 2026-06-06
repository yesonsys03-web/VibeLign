# === ANCHOR: DOCS_VISUALIZER_TEXT_START ===
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional, TypeVar


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CHECKLIST_RE = re.compile(r"^\s*[-*]\s+\[(?P<checked>[ xX])\]\s+(?P<text>.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<text>.+?)\s*$")
MERMAID_FENCE_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
MERMAID_LEADING_RE = re.compile(
    r"^\s*(flowchart|graph|mindmap|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|pie|gantt|gitGraph|timeline)\b"
)
GLOSSARY_LINE_RE = re.compile(
    r"^\s*[-*]\s+`?(?P<term>[^:`]+?)`?\s*:\s*(?P<definition>.+)$"
)
WARNING_HINT_RE = re.compile(
    r"\b(warning|warnings|risk|risks|주의|경고)\b", re.IGNORECASE
)
ACTION_HEADING_RE = re.compile(
    r"\b(action|actions|checklist|todo|next step|task|tasks|구현|검증)\b",
    re.IGNORECASE,
)
RULES_HEADING_RE = re.compile(
    r"\b(rule|rules|principle|principles|guideline|guidelines|"
    r"규칙|원칙|지침|가이드라인)\b",
    re.IGNORECASE,
)
CRITERIA_HEADING_RE = re.compile(
    r"\b(success\s*criteria|acceptance|success|goal|goals|"
    r"성공\s*기준|기준|목표|완료\s*조건|수용)\b",
    re.IGNORECASE,
)
EDGE_HEADING_RE = re.compile(
    r"\b(edge\s*cases?|pitfall|pitfalls|caveat|caveats|gotcha|"
    r"예외|주의|주의사항|함정|엣지)\b",
    re.IGNORECASE,
)
COMPONENTS_HEADING_RE = re.compile(
    r"\b(component|components|module|modules|architecture|structure|"
    r"구성\s*요소|구성|모듈|아키텍처|구조)\b",
    re.IGNORECASE,
)
ORDERED_DIGIT_RE = re.compile(r"^(?P<indent>\s*)(?P<num>\d+)[.)]\s+(?P<text>.+)$")
ORDERED_STEP_RE = re.compile(
    r"^(?P<indent>\s*)step\s*(?P<num>\d+)[:.)]?\s*(?P<text>.+)$",
    re.IGNORECASE,
)
ORDERED_STAGE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<num>\d+)단계(?:\s*[-—:]\s*)?(?P<text>.+)$"
)
DECISION_HINT_RE = re.compile(
    r"\b(if|when|else|fallback|exists?|missing|match|mismatch|yes|no|success|fail)\b|존재\?|일치\?|없으면|실패\s*시|성공\s*시",
    re.IGNORECASE,
)
FILE_LIKE_RE = re.compile(
    r"(?:[A-Za-z]:[\\/])?(?:[\w.\-]+[\\/])*[\w.\-]+\.(?:js|ts|tsx|py|md|json|yaml|yml|rs)\b"
)
COMMAND_HINT_RE = re.compile(
    r"^\s*(?:\$\s+|npm\s+|pnpm\s+|yarn\s+|python\s+|node\s+|bash\s+|sh\s+|cp\s+|mv\s+|mkdir\s+|cd\s+)"
)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_MERMAID_UNSAFE_RE = re.compile(r'["{}\[\]()<>`|#;:]')
DOC_KIND_HINTS: dict[str, tuple[str, ...]] = {
    "step": ("설치", "사용법", "가이드", "step", "phase", "workflow", "절차", "실행"),
    "decision": ("faq", "판정", "결정", "trust", "fallback", "검증", "decision"),
    "component": ("구성", "파일", "역할", "architecture", "module", "모듈", "컴포넌트"),
    "overview": ("readme", "소개", "개요", "overview", "about"),
}
MAX_VISUAL_SECTIONS = 40
MAX_VISUAL_GLOSSARY = 16
MAX_VISUAL_ACTION_ITEMS = 16
MAX_VISUAL_DIAGRAMS = 8
HUGE_DOC_LINE_THRESHOLD = 1200
TOP_HEADING_CAP = 40
STEP_CAP = 8
COMPONENT_CAP = 6
TItem = TypeVar("TItem")


# === ANCHOR: DOCS_VISUALIZER_CURRENT_GENERATED_AT_START ===
def current_generated_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# === ANCHOR: DOCS_VISUALIZER_CURRENT_GENERATED_AT_END ===


# === ANCHOR: DOCS_VISUALIZER_SOURCE_GENERATED_AT_START ===
def source_generated_at(source_path: Path) -> str:
    timestamp = source_path.stat().st_mtime
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
# === ANCHOR: DOCS_VISUALIZER_SOURCE_GENERATED_AT_END ===


# === ANCHOR: DOCS_VISUALIZER__SLUGIFY_START ===
def _slugify(text: str) -> str:
    value = re.sub(r"[`*_~]", "", text.strip().lower())
    value = re.sub(r"[^a-z0-9가-힣\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"
# === ANCHOR: DOCS_VISUALIZER__SLUGIFY_END ===


# === ANCHOR: DOCS_VISUALIZER__STRIP_INLINE_MARKDOWN_START ===
def _strip_inline_markdown(text: str) -> str:
    value = text.strip()
    value = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", value)
    value = re.sub(r"[`*_>#]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
# === ANCHOR: DOCS_VISUALIZER__STRIP_INLINE_MARKDOWN_END ===


# === ANCHOR: DOCS_VISUALIZER__SPLIT_MERMAID_AWARE_LINES_START ===
def _split_mermaid_aware_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
# === ANCHOR: DOCS_VISUALIZER__SPLIT_MERMAID_AWARE_LINES_END ===


# === ANCHOR: DOCS_VISUALIZER__README_OVERRIDE_HINT_START ===
def _readme_override_hint(source_path: Path, title: str) -> bool:
    filename = source_path.name.lower()
    if filename == "readme.md":
        return True
    return title.strip() in {"README", "Overview", "소개", "개요"}
# === ANCHOR: DOCS_VISUALIZER__README_OVERRIDE_HINT_END ===


# === ANCHOR: DOCS_VISUALIZER__OVERVIEW_OVERRIDE_HINT_START ===
def _overview_override_hint(
    source_path: Path, title: str, top_headings: list[str]
# === ANCHOR: DOCS_VISUALIZER__OVERVIEW_OVERRIDE_HINT_END ===
) -> bool:
    normalized = source_path.as_posix().lower()
    filename = source_path.name.lower()
    title_lower = title.strip().lower()
    if filename == "index.md" and len(top_headings) >= 3:
        return True
    if "/docs/wiki/" in normalized and len(top_headings) >= 3:
        return True
    return (
        title_lower in {"project overview", "wiki", "index"} and len(top_headings) >= 3
    )


# === ANCHOR: DOCS_VISUALIZER__CIRCLED_NUMBER_START ===
def _circled_number(line: str) -> tuple[Optional[int], str, int]:
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    if not stripped:
        return None, "", indent
    circled = "①②③④⑤⑥⑦⑧⑨⑩"
    head = stripped[0]
    if head not in circled:
        return None, "", indent
    text = stripped[1:].lstrip(" .):-—")
    return circled.index(head) + 1, _strip_inline_markdown(text), indent
# === ANCHOR: DOCS_VISUALIZER__CIRCLED_NUMBER_END ===


# === ANCHOR: DOCS_VISUALIZER__ORDERED_STEP_PARTS_START ===
def _ordered_step_parts(line: str) -> tuple[Optional[int], str, int]:
    for pattern in (ORDERED_DIGIT_RE, ORDERED_STEP_RE, ORDERED_STAGE_RE):
        match = pattern.match(line)
        if match:
            return (
                int(match.group("num")),
                _strip_inline_markdown(match.group("text")),
                len(match.group("indent")),
            )
    return _circled_number(line)
# === ANCHOR: DOCS_VISUALIZER__ORDERED_STEP_PARTS_END ===


# === ANCHOR: DOCS_VISUALIZER__SPLIT_TABLE_ROW_START ===
def _split_table_row(line: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line.strip():
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    cells.append("".join(current).strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [_strip_inline_markdown(cell) for cell in cells if cell.strip()]
# === ANCHOR: DOCS_VISUALIZER__SPLIT_TABLE_ROW_END ===


# === ANCHOR: DOCS_VISUALIZER__ITER_NON_CODE_LINES_START ===
def _iter_non_code_lines(lines: list[str]) -> list[str]:
    items: list[str] = []
    in_code = False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        items.append(raw)
    return items
# === ANCHOR: DOCS_VISUALIZER__ITER_NON_CODE_LINES_END ===


# === ANCHOR: DOCS_VISUALIZER__DEDUPE_KEEP_ORDER_START ===
def _dedupe_keep_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
# === ANCHOR: DOCS_VISUALIZER__DEDUPE_KEEP_ORDER_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_HEADING_RANGES_START ===
def _extract_heading_ranges(lines: list[str]) -> list[tuple[int, int, int, str]]:
    headings: list[tuple[int, int, int, str]] = []
    in_code = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        headings.append(
            (index, len(match.group(1)), index, _strip_inline_markdown(match.group(2)))
        )

    ranges: list[tuple[int, int, int, str]] = []
    for position, (start, level, _, title) in enumerate(headings):
        next_start = (
            headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        )
        ranges.append((start, next_start, level, title))
    return ranges
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_HEADING_RANGES_END ===


# === ANCHOR: DOCS_VISUALIZER__FIRST_MEANINGFUL_PARAGRAPH_START ===
def _first_meaningful_paragraph(lines: list[str]) -> str:
    chunks: list[str] = []
    in_code = False
    for raw in lines:
        line = raw.strip()
        if raw.startswith("```"):
            in_code = not in_code
            if chunks:
                break
            continue
        if in_code:
            continue
        if not line:
            if chunks:
                break
            continue
        if (
            line.startswith("#")
            or line.startswith("|")
            or re.fullmatch(r"[-| :]+", line)
        ):
            if chunks:
                break
            continue
        if BULLET_RE.match(line) or CHECKLIST_RE.match(line):
            if chunks:
                break
            continue
        chunks.append(_strip_inline_markdown(line))
    return " ".join(part for part in chunks if part).strip()
# === ANCHOR: DOCS_VISUALIZER__FIRST_MEANINGFUL_PARAGRAPH_END ===
# === ANCHOR: DOCS_VISUALIZER_TEXT_END ===
