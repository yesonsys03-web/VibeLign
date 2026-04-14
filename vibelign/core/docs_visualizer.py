from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re
import sys
from typing import Any, Optional, TypeVar


def _load_docs_cache_module() -> Any:
    module_path = Path(__file__).with_name("docs_cache.py")
    spec = importlib.util.spec_from_file_location("docs_cache_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("docs_cache module을 로드할 수 없어요")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_DOCS_CACHE = _load_docs_cache_module()
DOCS_VISUAL_GENERATOR_VERSION = _DOCS_CACHE.DOCS_VISUAL_GENERATOR_VERSION
DOCS_VISUAL_SCHEMA_VERSION = _DOCS_CACHE.DOCS_VISUAL_SCHEMA_VERSION
compute_source_hash = _DOCS_CACHE.compute_source_hash
docs_visual_contract = _DOCS_CACHE.docs_visual_contract
normalize_doc_text_bytes = _DOCS_CACHE.normalize_doc_text_bytes


@dataclass(frozen=True)
class VisualSection:
    id: str
    title: str
    level: int
    summary: str = ""


@dataclass(frozen=True)
class GlossaryEntry:
    term: str
    definition: str


@dataclass(frozen=True)
class ActionItem:
    text: str
    checked: bool = False


@dataclass(frozen=True)
class DiagramBlock:
    id: str
    kind: str
    title: str = ""
    source: str = ""


@dataclass(frozen=True)
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def current_generated_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def source_generated_at(source_path: Path) -> str:
    timestamp = source_path.stat().st_mtime
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_artifact_shell(
    source_path: Path, *, title: str, summary: str = ""
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
GLOSSARY_LINE_RE = re.compile(
    r"^\s*[-*]\s+`?(?P<term>[^:`]+?)`?\s*:\s*(?P<definition>.+)$"
)
WARNING_HINT_RE = re.compile(
    r"\b(warning|warnings|risk|risks|주의|경고)\b", re.IGNORECASE
)
ACTION_HEADING_RE = re.compile(
    r"\b(action|actions|checklist|todo|next step|task|tasks|구현|검증)\b", re.IGNORECASE
)
MAX_VISUAL_SECTIONS = 40
MAX_VISUAL_GLOSSARY = 16
MAX_VISUAL_ACTION_ITEMS = 16
MAX_VISUAL_DIAGRAMS = 8
HUGE_DOC_LINE_THRESHOLD = 1200
TItem = TypeVar("TItem")


def _slugify(text: str) -> str:
    value = re.sub(r"[`*_~]", "", text.strip().lower())
    value = re.sub(r"[^a-z0-9가-힣\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"


def _strip_inline_markdown(text: str) -> str:
    value = text.strip()
    value = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", value)
    value = re.sub(r"[`*_>#]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _split_mermaid_aware_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _extract_heading_ranges(lines: list[str]) -> list[tuple[int, int, int, str]]:
    headings: list[tuple[int, int, int, str]] = []
    for index, line in enumerate(lines):
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


def _section_summary(section_lines: list[str]) -> str:
    return _first_meaningful_paragraph(section_lines)


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


def _extract_mermaid_blocks(
    text: str, sections: list[VisualSection]
) -> list[DiagramBlock]:
    matches = list(MERMAID_FENCE_RE.finditer(text))
    diagrams: list[DiagramBlock] = []
    for index, match in enumerate(matches, start=1):
        prefix = text[: match.start()]
        active_title = ""
        for section in sections:
            marker = (
                f"# {'#' * (section.level - 1)}{section.title}"
                if section.level > 1
                else f"# {section.title}"
            )
            if marker in prefix:
                active_title = section.title
        diagrams.append(
            DiagramBlock(
                id=f"diagram-{index}",
                kind="mermaid",
                title=active_title,
                source=match.group(1).strip(),
            )
        )
    return diagrams


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


def _derive_summary(lines: list[str], sections: list[VisualSection]) -> str:
    paragraph = _first_meaningful_paragraph(lines)
    if paragraph:
        return paragraph
    if sections:
        parts = [section.title for section in sections[:3]]
        return "Sections: " + ", ".join(parts)
    return "Empty markdown document."


def _truncate_with_warning(
    items: list[TItem],
    limit: int,
    warnings: list[str],
    label: str,
) -> list[TItem]:
    if len(items) <= limit:
        return items
    warnings.append(
        f"enhancement_partial_disabled: {label}가 {len(items)}개여서 상위 {limit}개만 유지했습니다."
    )
    return items[:limit]


def visualize_markdown_bytes(source_path: Path, raw: bytes) -> DocsVisualArtifact:
    normalized = normalize_doc_text_bytes(raw)
    lines = _split_mermaid_aware_lines(normalized)
    warnings: list[str] = []
    sections = _extract_sections(lines)
    title = _derive_title(lines, source_path)
    summary = _derive_summary(lines, sections)
    glossary = _extract_glossary(lines)
    action_items = _extract_action_items(lines)
    diagram_blocks = _extract_mermaid_blocks(normalized, sections)
    warnings.extend(_extract_warnings(lines))

    huge_doc = len(lines) > HUGE_DOC_LINE_THRESHOLD
    if huge_doc:
        warnings.append(
            "enhancement_partial_disabled: 문서가 매우 길어서 일부 enhancement를 축약 모드로 표시합니다."
        )
        diagram_blocks = []
        glossary = glossary[:8]
        action_items = action_items[:12]
        sections = sections[:24]

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
    )


def visualize_markdown_file(source_path: Path) -> DocsVisualArtifact:
    resolved = source_path.resolve()
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise ValueError(f"문서를 읽을 수 없어요: {exc}") from exc

    try:
        return visualize_markdown_bytes(resolved, raw)
    except UnicodeDecodeError as exc:
        raise ValueError("UTF-8 markdown만 visual artifact를 생성할 수 있어요") from exc


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


def is_trusted_visual_artifact(payload: Any) -> bool:
    return trust_failure_reason(payload) is None
