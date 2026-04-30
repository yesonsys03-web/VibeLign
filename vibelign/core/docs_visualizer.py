# === ANCHOR: DOCS_VISUALIZER_START ===
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Optional, TypeVar

from . import docs_cache as _DOCS_CACHE

DOCS_VISUAL_GENERATOR_VERSION = _DOCS_CACHE.DOCS_VISUAL_GENERATOR_VERSION
DOCS_VISUAL_SCHEMA_VERSION = _DOCS_CACHE.DOCS_VISUAL_SCHEMA_VERSION
compute_source_hash = _DOCS_CACHE.compute_source_hash
docs_visual_contract = _DOCS_CACHE.docs_visual_contract
normalize_doc_text_bytes = _DOCS_CACHE.normalize_doc_text_bytes
read_document_text = _DOCS_CACHE.read_document_text


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_VISUALSECTION_START ===
class VisualSection:
    id: str
    title: str
    level: int
    summary: str = ""
# === ANCHOR: DOCS_VISUALIZER_VISUALSECTION_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_GLOSSARYENTRY_START ===
class GlossaryEntry:
    term: str
    definition: str
# === ANCHOR: DOCS_VISUALIZER_GLOSSARYENTRY_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_ACTIONITEM_START ===
class ActionItem:
    text: str
    checked: bool = False
# === ANCHOR: DOCS_VISUALIZER_ACTIONITEM_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMBLOCK_START ===
class DiagramBlock:
    id: str
    kind: str
    title: str = ""
    source: str = ""
    provenance: str = "authored"
    generator: str = ""
    confidence: str = "high"
    warnings: list[str] = field(default_factory=list)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMBLOCK_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_START ===
class HeuristicEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "heuristic"
    generator: str = "heuristic-v2"
    generated_at: str = ""
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_START ===
class AIEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "ai_draft"
    model: str = ""
    provider: str = ""
    generated_at: str = ""
    source_hash: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_START ===
class DocsVisualArtifact:
    source_path: str
    source_hash: str
    generated_at: str
    generator_version: str
    schema_version: int
    title: str
    summary: str
    sections: list[VisualSection] = field(default_factory=list)
    glossary: list[GlossaryEntry] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    diagram_blocks: list[DiagramBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    heuristic_fields: Optional["HeuristicEnhancedFields"] = None
    ai_fields: Optional["AIEnhancedFields"] = None

    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_START ===
    def to_dict(self) -> dict[str, Any]:
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_END ===
        return asdict(self)
    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMSIGNALS_START ===
class DiagramSignals:
    title: str
    summary: str
    top_headings: list[str]
    ordered_steps: list[str]
    checklist_steps: list[str]
    decision_lines: list[str]
    file_like_items: list[str]
    table_rows: list[list[str]]
    readme_override: bool = False
    overview_override: bool = False
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMSIGNALS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMCANDIDATE_START ===
class DiagramCandidate:
    name: str
    title: str
    source: str
    generator: str
    confidence: str
    warnings: list[str]
    score: int
    supported: bool = True
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMCANDIDATE_END ===


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


# === ANCHOR: DOCS_VISUALIZER_BUILD_ARTIFACT_SHELL_START ===
def build_artifact_shell(
    source_path: Path, *, title: str, summary: str = ""
# === ANCHOR: DOCS_VISUALIZER_BUILD_ARTIFACT_SHELL_END ===
) -> DocsVisualArtifact:
    resolved = source_path.resolve()
    return DocsVisualArtifact(
        source_path=resolved.as_posix(),
        source_hash=compute_source_hash(resolved),
        generated_at=source_generated_at(resolved),
        generator_version=DOCS_VISUAL_GENERATOR_VERSION,
        schema_version=DOCS_VISUAL_SCHEMA_VERSION,
        title=title,
        summary=summary,
    )


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
TOP_HEADING_CAP = 8
STEP_CAP = 8
COMPONENT_CAP = 6
TItem = TypeVar("TItem")


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


# === ANCHOR: DOCS_VISUALIZER__SECTION_SUMMARY_START ===
def _section_summary(section_lines: list[str]) -> str:
    return _first_meaningful_paragraph(section_lines)
# === ANCHOR: DOCS_VISUALIZER__SECTION_SUMMARY_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_SECTIONS_START ===
def _extract_sections(lines: list[str]) -> list[VisualSection]:
    ranges = _extract_heading_ranges(lines)
    counts: dict[str, int] = {}
    sections: list[VisualSection] = []
    for start, end, level, title in ranges:
        base = _slugify(title)
        seen = counts.get(base, 0)
        counts[base] = seen + 1
        section_id = base if seen == 0 else f"{base}-{seen + 1}"
        sections.append(
            VisualSection(
                id=section_id,
                title=title,
                level=level,
                summary=_section_summary(lines[start + 1 : end]),
            )
        )
    return sections
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_SECTIONS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_GLOSSARY_START ===
def _extract_glossary(lines: list[str]) -> list[GlossaryEntry]:
    entries: list[GlossaryEntry] = []
    for line in lines:
        match = GLOSSARY_LINE_RE.match(line)
        if match:
            entries.append(
                GlossaryEntry(
                    term=_strip_inline_markdown(match.group("term")),
                    definition=_strip_inline_markdown(match.group("definition")),
                )
            )
    return entries
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_GLOSSARY_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_ACTION_ITEMS_START ===
def _extract_action_items(lines: list[str]) -> list[ActionItem]:
    actions: list[ActionItem] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, _level, title in heading_ranges:
        action_heading = bool(ACTION_HEADING_RE.search(title))
        for line in lines[start + 1 : end]:
            checklist = CHECKLIST_RE.match(line)
            if checklist:
                actions.append(
                    ActionItem(
                        text=_strip_inline_markdown(checklist.group("text")),
                        checked=checklist.group("checked").lower() == "x",
                    )
                )
                continue
            bullet = BULLET_RE.match(line)
            if action_heading and bullet:
                actions.append(
                    ActionItem(text=_strip_inline_markdown(bullet.group("text")))
                )
    return actions
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_ACTION_ITEMS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_BULLET_SECTION_START ===
def _extract_bullet_section(lines: list[str], heading_re: re.Pattern[str]) -> list[str]:
    items: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, _level, title in heading_ranges:
        if not heading_re.search(title):
            continue
        for line in lines[start + 1 : end]:
            checklist = CHECKLIST_RE.match(line)
            if checklist:
                items.append(_strip_inline_markdown(checklist.group("text")))
                continue
            bullet = BULLET_RE.match(line)
            if bullet:
                items.append(_strip_inline_markdown(bullet.group("text")))
    return _dedupe_keep_order(items)
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_BULLET_SECTION_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_COMPONENTS_START ===
def _extract_components(lines: list[str]) -> list[str]:
    items: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, level, title in heading_ranges:
        if level != 2:
            continue
        summary = _first_meaningful_paragraph(lines[start + 1 : end])
        if not summary:
            continue
        parts = re.split(r"(?<=[.!?。？！])\s+|(?<=[.!?。？！])$", summary)
        first = next((part.strip() for part in parts if part.strip()), "")
        if not first:
            continue
        items.append(f"{title} — {first}")
        if len(items) >= COMPONENT_CAP:
            break
    return items
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_COMPONENTS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_WARNINGS_START ===
def _extract_warnings(lines: list[str]) -> list[str]:
    warnings: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, _level, title in heading_ranges:
        if WARNING_HINT_RE.search(title):
            summary = _section_summary(lines[start + 1 : end])
            warnings.append(f"{title}: {summary}" if summary else title)
    for line in lines:
        text = _strip_inline_markdown(line)
        if not text:
            continue
        if (
            text.startswith("⚠")
            or text.lower().startswith("warning:")
            or text.startswith("주의:")
        ):
            warnings.append(text)
    return list(dict.fromkeys(warnings))
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_WARNINGS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_ORDERED_STEPS_START ===
def _extract_ordered_steps(lines: list[str]) -> list[str]:
    steps: list[str] = []
    current: list[str] = []
    last_num: Optional[int] = None
    last_indent: Optional[int] = None
    in_code = False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if len(current) >= 3:
                steps.extend(current)
            current = []
            last_num = None
            last_indent = None
            continue
        if in_code:
            continue
        if HEADING_RE.match(raw) or not stripped:
            if len(current) >= 3:
                steps.extend(current)
            current = []
            last_num = None
            last_indent = None
            continue
        num, text, indent = _ordered_step_parts(raw)
        if num is None or not text:
            if len(current) >= 3:
                steps.extend(current)
            current = []
            last_num = None
            last_indent = None
            continue
        if last_num is None:
            current = [text]
            last_num = num
            last_indent = indent
            continue
        if indent == last_indent and num == last_num + 1:
            current.append(text)
            last_num = num
            continue
        if len(current) >= 3:
            steps.extend(current)
        current = [text]
        last_num = num
        last_indent = indent
    if len(current) >= 3:
        steps.extend(current)
    return steps
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_ORDERED_STEPS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_CHECKLIST_STEPS_START ===
def _extract_checklist_steps(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw in _iter_non_code_lines(lines):
        match = CHECKLIST_RE.match(raw)
        if match:
            items.append(_strip_inline_markdown(match.group("text")))
    return items
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_CHECKLIST_STEPS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_DECISION_LINES_START ===
def _extract_decision_lines(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw in _iter_non_code_lines(lines):
        text = _strip_inline_markdown(raw)
        if text and DECISION_HINT_RE.search(text):
            items.append(text)
    return _dedupe_keep_order(items)[:6]
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_DECISION_LINES_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TABLE_ROWS_START ===
def _extract_table_rows(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in _iter_non_code_lines(lines):
        stripped = raw.strip()
        if "|" not in stripped or TABLE_SEPARATOR_RE.match(stripped):
            continue
        parts = _split_table_row(stripped)
        if len(parts) >= 2:
            rows.append(parts)
    return rows
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TABLE_ROWS_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_FILE_LIKE_ITEMS_START ===
def _extract_file_like_items(
    lines: list[str], sections: list[VisualSection]
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_FILE_LIKE_ITEMS_END ===
) -> list[str]:
    items: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    heading_by_start = {start: title for start, _end, _level, title in heading_ranges}
    active_heading = ""
    in_code = False
    for index, raw in enumerate(lines):
        if index in heading_by_start:
            active_heading = heading_by_start[index]
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped or COMMAND_HINT_RE.match(stripped):
            continue
        lowered_heading = active_heading.lower().strip()
        if any(
            hint in lowered_heading
            for hint in (
                "signal",
                "template",
                "템플릿",
                "예시",
                "example",
                "sample",
                "regex",
            )
        ):
            continue
        cleaned = _strip_inline_markdown(raw)
        items.extend(FILE_LIKE_RE.findall(cleaned))
    for section in sections:
        lowered_title = section.title.lower().strip()
        if any(
            hint in lowered_title
            for hint in (
                "signal",
                "template",
                "템플릿",
                "예시",
                "example",
                "sample",
                "regex",
            )
        ):
            continue
        items.extend(FILE_LIKE_RE.findall(section.title))
        items.extend(FILE_LIKE_RE.findall(section.summary))
    return _dedupe_keep_order([item.replace("\\", "/") for item in items])


# === ANCHOR: DOCS_VISUALIZER__SIGNAL_SCORE_START ===
def _signal_score(texts: list[str], key: str) -> int:
    hints = DOC_KIND_HINTS[key]
    score = 0
    for text in texts:
        lowered = text.lower()
        score += sum(1 for hint in hints if hint in lowered)
    return score
# === ANCHOR: DOCS_VISUALIZER__SIGNAL_SCORE_END ===


# === ANCHOR: DOCS_VISUALIZER__COLLECT_DIAGRAM_SIGNALS_START ===
def _collect_diagram_signals(
    source_path: Path,
    *,
    lines: list[str],
    title: str,
    summary: str,
    sections: list[VisualSection],
    action_items: list[ActionItem],
# === ANCHOR: DOCS_VISUALIZER__COLLECT_DIAGRAM_SIGNALS_END ===
) -> DiagramSignals:
    top_headings = [section.title for section in sections if section.level == 2][
        : TOP_HEADING_CAP + 1
    ]
    return DiagramSignals(
        title=title,
        summary=summary,
        top_headings=top_headings,
        ordered_steps=_extract_ordered_steps(lines),
        checklist_steps=[item.text for item in action_items if item.text]
        or _extract_checklist_steps(lines),
        decision_lines=_extract_decision_lines(lines),
        file_like_items=_extract_file_like_items(lines, sections),
        table_rows=_extract_table_rows(lines),
        readme_override=_readme_override_hint(source_path, title),
        overview_override=_overview_override_hint(source_path, title, top_headings),
    )


# === ANCHOR: DOCS_VISUALIZER__SAFE_MERMAID_LABEL_START ===
def _safe_mermaid_label(text: str, max_len: int = 32) -> str:
    value = text.replace("\r", "").replace("\\", "/")
    value = _MERMAID_UNSAFE_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"
# === ANCHOR: DOCS_VISUALIZER__SAFE_MERMAID_LABEL_END ===


# === ANCHOR: DOCS_VISUALIZER__RENDER_STEP_FLOWCHART_START ===
def _render_step_flowchart(steps: list[str], warnings: list[str]) -> str:
    trimmed = steps[:STEP_CAP]
    lines = ["flowchart TD"]
    for index, step in enumerate(trimmed, start=1):
        lines.append(f'S{index}["{_safe_mermaid_label(step, 36)}"]')
        if index > 1:
            lines.append(f"S{index - 1} --> S{index}")
    if len(steps) > STEP_CAP:
        extra = len(steps) - STEP_CAP
        warnings.append(
            f"auto_diagram_truncated: step_flow omitted {extra} additional steps"
        )
        more_id = f"S{len(trimmed) + 1}"
        lines.append(f'{more_id}["… {extra} more steps"]')
        lines.append(f"S{len(trimmed)} --> {more_id}")
    return "\n".join(lines)
# === ANCHOR: DOCS_VISUALIZER__RENDER_STEP_FLOWCHART_END ===


# === ANCHOR: DOCS_VISUALIZER__RENDER_HEADING_MINDMAP_START ===
def _render_heading_mindmap(
    title: str, headings: list[str], warnings: list[str]
# === ANCHOR: DOCS_VISUALIZER__RENDER_HEADING_MINDMAP_END ===
) -> str:
    trimmed = headings[:TOP_HEADING_CAP]
    if len(headings) > TOP_HEADING_CAP:
        warnings.append(
            f"auto_diagram_truncated: heading_mindmap capped at {TOP_HEADING_CAP} headings"
        )
    root = _safe_mermaid_label(title or "Untitled", 28) or "Untitled"
    lines = ["mindmap", f'  root(("{root}"))']
    for heading in trimmed:
        lines.append(f'    "{_safe_mermaid_label(heading, 28)}"')
    return "\n".join(lines)


# === ANCHOR: DOCS_VISUALIZER__RENDER_COMPONENT_FLOW_START ===
def _render_component_flow(components: list[str]) -> str:
    trimmed = components[:COMPONENT_CAP]
    lines = ["flowchart TB", 'subgraph DOC["Component Summary"]']
    for index, item in enumerate(trimmed, start=1):
        lines.append(f'C{index}["{_safe_mermaid_label(item, 28)}"]')
    lines.append("end")
    return "\n".join(lines)
# === ANCHOR: DOCS_VISUALIZER__RENDER_COMPONENT_FLOW_END ===


# === ANCHOR: DOCS_VISUALIZER__BUILD_STEP_CANDIDATE_START ===
def _build_step_candidate(signals: DiagramSignals) -> Optional[DiagramCandidate]:
    steps = signals.ordered_steps or signals.checklist_steps
    if len(steps) < 3:
        return None
    score = 4 if len(signals.ordered_steps) >= 3 else 3
    score += min(_signal_score([signals.title, signals.summary], "step"), 2)
    if len(signals.checklist_steps) >= 3:
        score += 1
    confidence = "high" if len(signals.ordered_steps) >= 4 else "medium"
    local_warnings: list[str] = []
    return DiagramCandidate(
        name="step_flow",
        title="실행 흐름",
        source=_render_step_flowchart(steps, local_warnings),
        generator="step-flow-v1",
        confidence=confidence,
        warnings=local_warnings,
        score=score,
    )
# === ANCHOR: DOCS_VISUALIZER__BUILD_STEP_CANDIDATE_END ===


# === ANCHOR: DOCS_VISUALIZER__BUILD_DECISION_CANDIDATE_START ===
def _build_decision_candidate(signals: DiagramSignals) -> Optional[DiagramCandidate]:
    if len(signals.decision_lines) < 2:
        return None
    return DiagramCandidate(
        name="decision_flow",
        title="결정 흐름",
        source="",
        generator="decision-flow-v1",
        confidence="medium",
        warnings=[],
        score=4 + min(len(signals.decision_lines), 2),
        supported=False,
    )
# === ANCHOR: DOCS_VISUALIZER__BUILD_DECISION_CANDIDATE_END ===


# === ANCHOR: DOCS_VISUALIZER__BUILD_HEADING_CANDIDATE_START ===
def _build_heading_candidate(signals: DiagramSignals) -> Optional[DiagramCandidate]:
    if len(signals.top_headings) < 3 and not signals.readme_override:
        return None
    score = 4 if len(signals.top_headings) >= 4 else 3
    score += min(_signal_score([signals.title, signals.summary], "overview"), 2)
    if len(signals.ordered_steps) < 3:
        score += 1
    confidence = "high" if len(signals.top_headings) >= 4 else "medium"
    local_warnings: list[str] = []
    headings = signals.top_headings or [signals.title]
    return DiagramCandidate(
        name="heading_mindmap",
        title="문서 구조",
        source=_render_heading_mindmap(signals.title, headings, local_warnings),
        generator="heading-mindmap-v1",
        confidence=confidence,
        warnings=local_warnings,
        score=score,
    )
# === ANCHOR: DOCS_VISUALIZER__BUILD_HEADING_CANDIDATE_END ===


# === ANCHOR: DOCS_VISUALIZER__BUILD_COMPONENT_CANDIDATE_START ===
def _build_component_candidate(signals: DiagramSignals) -> Optional[DiagramCandidate]:
    components = signals.file_like_items[:]
    for row in signals.table_rows:
        components.extend(FILE_LIKE_RE.findall(" ".join(row)))
    components = _dedupe_keep_order([item.replace("\\", "/") for item in components])
    if len(components) < 3:
        return None
    score = 3 + min(len(components), 2)
    score += min(_signal_score([signals.title, signals.summary], "component"), 2)
    confidence = (
        "high" if len(components) >= 4 or len(signals.table_rows) >= 2 else "medium"
    )
    return DiagramCandidate(
        name="component_flow",
        title="구성 요소 요약",
        source=_render_component_flow(components),
        generator="component-flow-v1",
        confidence=confidence,
        warnings=["auto_diagram_note: component flow is a structural summary"],
        score=score,
    )
# === ANCHOR: DOCS_VISUALIZER__BUILD_COMPONENT_CANDIDATE_END ===


# === ANCHOR: DOCS_VISUALIZER__SELECT_BEST_CANDIDATE_START ===
def _select_best_candidate(
    signals: DiagramSignals, candidates: list[DiagramCandidate]
# === ANCHOR: DOCS_VISUALIZER__SELECT_BEST_CANDIDATE_END ===
) -> Optional[DiagramCandidate]:
    valid = [candidate for candidate in candidates if candidate.score >= 4]
    if not valid:
        return None
    if signals.readme_override or signals.overview_override:
        for candidate in valid:
            if candidate.name == "heading_mindmap" and candidate.supported:
                return candidate
    if len(signals.top_headings) >= 5:
        for candidate in valid:
            if candidate.name == "heading_mindmap" and candidate.supported:
                return candidate
    priority = {
        "step_flow": 0,
        "decision_flow": 1,
        "heading_mindmap": 2,
        "component_flow": 3,
    }
    ordered = sorted(
        valid,
        key=lambda candidate: (-candidate.score, priority.get(candidate.name, 99)),
    )
    for candidate in ordered:
        if candidate.supported and candidate.source.strip():
            return candidate
    return None


# === ANCHOR: DOCS_VISUALIZER__GENERATE_HEURISTIC_DIAGRAMS_START ===
def _generate_heuristic_diagrams(
    source_path: Path,
    *,
    lines: list[str],
    title: str,
    summary: str,
    sections: list[VisualSection],
    action_items: list[ActionItem],
    warnings: list[str],
# === ANCHOR: DOCS_VISUALIZER__GENERATE_HEURISTIC_DIAGRAMS_END ===
) -> list[DiagramBlock]:
    signals = _collect_diagram_signals(
        source_path,
        lines=lines,
        title=title,
        summary=summary,
        sections=sections,
        action_items=action_items,
    )
    candidates = [
        candidate
        for candidate in (
            _build_step_candidate(signals),
            _build_decision_candidate(signals),
            _build_heading_candidate(signals),
            _build_component_candidate(signals),
        )
        if candidate is not None
    ]
    chosen = _select_best_candidate(signals, candidates)
    if not chosen:
        warnings.append("auto_diagram_skipped: low confidence (score<4)")
        return []
    warnings.extend(
        warning
        for warning in chosen.warnings
        if warning != "auto_diagram_note: component flow is a structural summary"
    )
    return [
        DiagramBlock(
            id="diagram-heuristic-1",
            kind="mermaid",
            title=chosen.title,
            source=chosen.source,
            provenance="heuristic",
            generator=chosen.generator,
            confidence=chosen.confidence,
            warnings=chosen.warnings,
        )
    ]


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_MERMAID_BLOCKS_START ===
def _extract_mermaid_blocks(
    text: str, sections: list[VisualSection]
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_MERMAID_BLOCKS_END ===
) -> list[DiagramBlock]:
    lines = _split_mermaid_aware_lines(text)
    heading_ranges = _extract_heading_ranges(lines)
    heading_by_start = {start: title for start, _end, _level, title in heading_ranges}
    diagrams: list[DiagramBlock] = []
    active_title = ""
    in_mermaid = False
    mermaid_title = ""
    mermaid_lines: list[str] = []

    for index, line in enumerate(lines):
        if index in heading_by_start:
            active_title = heading_by_start[index]

        stripped = line.strip()
        if not in_mermaid and stripped == "```mermaid":
            in_mermaid = True
            mermaid_title = active_title
            mermaid_lines = []
            continue

        if in_mermaid and stripped.startswith("```"):
            diagrams.append(
                DiagramBlock(
                    id=f"diagram-{len(diagrams) + 1}",
                    kind="mermaid",
                    title=mermaid_title,
                    source="\n".join(mermaid_lines).strip(),
                    provenance="authored",
                    generator="authored-mermaid-v1",
                    confidence="high",
                )
            )
            in_mermaid = False
            mermaid_title = ""
            mermaid_lines = []
            continue

        if in_mermaid:
            mermaid_lines.append(line)

    return diagrams


# === ANCHOR: DOCS_VISUALIZER__IS_EXAMPLE_MERMAID_CONTEXT_START ===
def _is_example_mermaid_context(title: str) -> bool:
    lowered = title.lower().strip()
    return any(
        hint in lowered
        for hint in ("mermaid 템플릿", "template", "예시", "example", "sample")
    )
# === ANCHOR: DOCS_VISUALIZER__IS_EXAMPLE_MERMAID_CONTEXT_END ===


# === ANCHOR: DOCS_VISUALIZER__USABLE_AUTHORED_DIAGRAMS_START ===
def _usable_authored_diagrams(
    diagrams: list[DiagramBlock], warnings: list[str]
# === ANCHOR: DOCS_VISUALIZER__USABLE_AUTHORED_DIAGRAMS_END ===
) -> list[DiagramBlock]:
    usable: list[DiagramBlock] = []
    for diagram in diagrams:
        if _is_example_mermaid_context(diagram.title):
            warnings.append("auto_diagram_note: illustrative mermaid example ignored")
            continue
        source = diagram.source.strip()
        if not source:
            warnings.append("auto_diagram_note: empty authored mermaid block ignored")
            continue
        if not MERMAID_LEADING_RE.match(source):
            warnings.append("auto_diagram_note: invalid authored mermaid block ignored")
            continue
        usable.append(
            replace(
                diagram,
                provenance="authored",
                generator="authored-mermaid-v1",
                confidence="high",
                warnings=list(diagram.warnings),
            )
        )
    return usable


# === ANCHOR: DOCS_VISUALIZER__DERIVE_TITLE_START ===
def _derive_title(lines: list[str], source_path: Path) -> str:
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            return _strip_inline_markdown(match.group(2)) or source_path.stem
    for line in lines:
        text = _strip_inline_markdown(line)
        if text:
            return text[:80]
    return source_path.stem.replace("-", " ").replace("_", " ") or source_path.name
# === ANCHOR: DOCS_VISUALIZER__DERIVE_TITLE_END ===


# === ANCHOR: DOCS_VISUALIZER__DERIVE_SUMMARY_START ===
def _derive_summary(lines: list[str], sections: list[VisualSection]) -> str:
    paragraph = _first_meaningful_paragraph(lines)
    if paragraph:
        return paragraph
    if sections:
        parts = [section.title for section in sections[:3]]
        return "Sections: " + ", ".join(parts)
    return "Empty markdown document."
# === ANCHOR: DOCS_VISUALIZER__DERIVE_SUMMARY_END ===


# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TLDR_ONE_LINER_START ===
def _extract_tldr_one_liner(lines: list[str]) -> str:
    paragraph = _first_meaningful_paragraph(lines)
    if not paragraph:
        return ""
    parts = re.split(r"(?<=[.!?。？！])\s+|(?<=[.!?。？！])$", paragraph)
    first = next((part.strip() for part in parts if part.strip()), "")
    return first[:180]
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TLDR_ONE_LINER_END ===


# === ANCHOR: DOCS_VISUALIZER__TRUNCATE_WITH_WARNING_START ===
def _truncate_with_warning(
    items: list[TItem],
    limit: int,
    warnings: list[str],
    label: str,
# === ANCHOR: DOCS_VISUALIZER__TRUNCATE_WITH_WARNING_END ===
) -> list[TItem]:
    if len(items) <= limit:
        return items
    warnings.append(
        f"enhancement_partial_disabled: {label}가 {len(items)}개여서 상위 {limit}개만 유지했습니다."
    )
    return items[:limit]


# === ANCHOR: DOCS_VISUALIZER_VISUALIZE_MARKDOWN_BYTES_START ===
def visualize_markdown_bytes(source_path: Path, raw: bytes) -> DocsVisualArtifact:
    normalized = normalize_doc_text_bytes(raw)
    lines = _split_mermaid_aware_lines(normalized)
    warnings: list[str] = []
    sections = _extract_sections(lines)
    title = _derive_title(lines, source_path)
    summary = _derive_summary(lines, sections)
    glossary = _extract_glossary(lines)
    action_items = _extract_action_items(lines)
    authored_diagrams = _usable_authored_diagrams(
        _extract_mermaid_blocks(normalized, sections), warnings
    )
    warnings.extend(_extract_warnings(lines))

    huge_doc = len(lines) > HUGE_DOC_LINE_THRESHOLD
    if huge_doc:
        warnings.append(
            "enhancement_partial_disabled: 문서가 매우 길어서 일부 enhancement를 축약 모드로 표시합니다."
        )
        if not authored_diagrams:
            warnings.append(
                "auto_diagram_skipped_huge_doc: inferred diagrams are disabled for very large documents"
            )
        glossary = glossary[:8]
        action_items = action_items[:12]
        sections = sections[:24]

    if authored_diagrams:
        diagram_blocks = authored_diagrams
    elif huge_doc:
        diagram_blocks = []
    else:
        diagram_blocks = _generate_heuristic_diagrams(
            source_path,
            lines=lines,
            title=title,
            summary=summary,
            sections=sections,
            action_items=action_items,
            warnings=warnings,
        )

    sections = _truncate_with_warning(
        sections, MAX_VISUAL_SECTIONS, warnings, "sections"
    )
    glossary = _truncate_with_warning(
        glossary, MAX_VISUAL_GLOSSARY, warnings, "glossary"
    )
    action_items = _truncate_with_warning(
        action_items, MAX_VISUAL_ACTION_ITEMS, warnings, "action_items"
    )
    diagram_blocks = _truncate_with_warning(
        diagram_blocks, MAX_VISUAL_DIAGRAMS, warnings, "diagram_blocks"
    )

    artifact = build_artifact_shell(source_path, title=title, summary=summary)
    heuristic_fields = HeuristicEnhancedFields(
        tldr_one_liner=_extract_tldr_one_liner(lines),
        key_rules=_extract_bullet_section(lines, RULES_HEADING_RE),
        success_criteria=_extract_bullet_section(lines, CRITERIA_HEADING_RE),
        edge_cases=_extract_bullet_section(lines, EDGE_HEADING_RE),
        components=_extract_components(lines),
        generator=DOCS_VISUAL_GENERATOR_VERSION,
        generated_at=artifact.generated_at,
    )

    return DocsVisualArtifact(
        source_path=artifact.source_path,
        source_hash=compute_source_hash(source_path.resolve()),
        generated_at=artifact.generated_at,
        generator_version=artifact.generator_version,
        schema_version=artifact.schema_version,
        title=artifact.title,
        summary=artifact.summary,
        sections=sections,
        glossary=glossary,
        action_items=action_items,
        diagram_blocks=diagram_blocks,
        warnings=warnings,
        heuristic_fields=heuristic_fields,
        ai_fields=None,
    )
# === ANCHOR: DOCS_VISUALIZER_VISUALIZE_MARKDOWN_BYTES_END ===


# === ANCHOR: DOCS_VISUALIZER_VISUALIZE_MARKDOWN_FILE_START ===
def visualize_markdown_file(source_path: Path) -> DocsVisualArtifact:
    resolved = source_path.resolve()
    try:
        text = read_document_text(resolved)
    except OSError as exc:
        raise ValueError(f"문서를 읽을 수 없어요: {exc}") from exc
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    return visualize_markdown_bytes(resolved, text.encode("utf-8"))
# === ANCHOR: DOCS_VISUALIZER_VISUALIZE_MARKDOWN_FILE_END ===


# === ANCHOR: DOCS_VISUALIZER_TRUST_FAILURE_REASON_START ===
def trust_failure_reason(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return "corrupt_json"

    contract = docs_visual_contract()
    required = contract["minimum_required_fields"]
    if not isinstance(required, list):
        return "corrupt_contract"

    for key in required:
        if key not in payload:
            return "missing_required_fields"

    if payload.get("schema_version") != DOCS_VISUAL_SCHEMA_VERSION:
        return "schema_version_mismatch"

    if payload.get("generator_version") != DOCS_VISUAL_GENERATOR_VERSION:
        return "generator_version_mismatch"

    return None
# === ANCHOR: DOCS_VISUALIZER_TRUST_FAILURE_REASON_END ===


# === ANCHOR: DOCS_VISUALIZER_IS_TRUSTED_VISUAL_ARTIFACT_START ===
def is_trusted_visual_artifact(payload: Any) -> bool:
    return trust_failure_reason(payload) is None
# === ANCHOR: DOCS_VISUALIZER_IS_TRUSTED_VISUAL_ARTIFACT_END ===
# === ANCHOR: DOCS_VISUALIZER_END ===
