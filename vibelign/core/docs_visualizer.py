# === ANCHOR: DOCS_VISUALIZER_START ===
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional

from . import docs_cache as _DOCS_CACHE
from .docs_visualizer_models import (
    AIEnhancedFields,
    ActionItem,
    DiagramBlock,
    DiagramCandidate,
    DiagramSignals,
    DocsVisualArtifact,
    GlossaryEntry,
    HeuristicEnhancedFields,
    VisualSection,
)
from .docs_visualizer_text import (
    ACTION_HEADING_RE,
    BULLET_RE,
    CHECKLIST_RE,
    COMMAND_HINT_RE,
    COMPONENT_CAP,
    COMPONENTS_HEADING_RE,
    CRITERIA_HEADING_RE,
    DECISION_HINT_RE,
    DOC_KIND_HINTS,
    EDGE_HEADING_RE,
    FILE_LIKE_RE,
    GLOSSARY_LINE_RE,
    HEADING_RE,
    HUGE_DOC_LINE_THRESHOLD,
    MAX_VISUAL_ACTION_ITEMS,
    MAX_VISUAL_DIAGRAMS,
    MAX_VISUAL_GLOSSARY,
    MAX_VISUAL_SECTIONS,
    MERMAID_FENCE_RE,
    MERMAID_LEADING_RE,
    ORDERED_DIGIT_RE,
    ORDERED_STAGE_RE,
    ORDERED_STEP_RE,
    RULES_HEADING_RE,
    STEP_CAP,
    TABLE_SEPARATOR_RE,
    TItem,
    TOP_HEADING_CAP,
    WARNING_HINT_RE,
    _MERMAID_UNSAFE_RE,
    _circled_number,
    _dedupe_keep_order,
    _extract_heading_ranges,
    _first_meaningful_paragraph,
    _iter_non_code_lines,
    _ordered_step_parts,
    _overview_override_hint,
    _readme_override_hint,
    _slugify,
    _split_mermaid_aware_lines,
    _split_table_row,
    _strip_inline_markdown,
    current_generated_at,
    source_generated_at,
)
from .docs_visualizer_extract import (
    _extract_action_items,
    _extract_bullet_section,
    _extract_checklist_steps,
    _extract_components,
    _extract_decision_lines,
    _extract_file_like_items,
    _extract_glossary,
    _extract_ordered_steps,
    _extract_sections,
    _extract_table_rows,
    _extract_warnings,
    _section_body_preview,
    _section_summary,
)
from .docs_visualizer_diagram import (
    _build_component_candidate,
    _build_decision_candidate,
    _build_heading_candidate,
    _build_step_candidate,
    _collect_diagram_signals,
    _extract_mermaid_blocks,
    _generate_heuristic_diagrams,
    _is_example_mermaid_context,
    _render_component_flow,
    _render_heading_mindmap,
    _render_step_flowchart,
    _safe_mermaid_label,
    _select_best_candidate,
    _signal_score,
    _usable_authored_diagrams,
)

DOCS_VISUAL_GENERATOR_VERSION = _DOCS_CACHE.DOCS_VISUAL_GENERATOR_VERSION
DOCS_VISUAL_SCHEMA_VERSION = _DOCS_CACHE.DOCS_VISUAL_SCHEMA_VERSION
compute_source_hash = _DOCS_CACHE.compute_source_hash
docs_visual_contract = _DOCS_CACHE.docs_visual_contract
normalize_doc_text_bytes = _DOCS_CACHE.normalize_doc_text_bytes
read_document_text = _DOCS_CACHE.read_document_text


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


__all__ = [
    "ACTION_HEADING_RE",
    "AIEnhancedFields",
    "ActionItem",
    "BULLET_RE",
    "CHECKLIST_RE",
    "COMMAND_HINT_RE",
    "COMPONENTS_HEADING_RE",
    "COMPONENT_CAP",
    "CRITERIA_HEADING_RE",
    "DECISION_HINT_RE",
    "DOCS_VISUAL_GENERATOR_VERSION",
    "DOCS_VISUAL_SCHEMA_VERSION",
    "DOC_KIND_HINTS",
    "DiagramBlock",
    "DiagramCandidate",
    "DiagramSignals",
    "DocsVisualArtifact",
    "EDGE_HEADING_RE",
    "FILE_LIKE_RE",
    "GLOSSARY_LINE_RE",
    "GlossaryEntry",
    "HEADING_RE",
    "HUGE_DOC_LINE_THRESHOLD",
    "HeuristicEnhancedFields",
    "MAX_VISUAL_ACTION_ITEMS",
    "MAX_VISUAL_DIAGRAMS",
    "MAX_VISUAL_GLOSSARY",
    "MAX_VISUAL_SECTIONS",
    "MERMAID_FENCE_RE",
    "MERMAID_LEADING_RE",
    "ORDERED_DIGIT_RE",
    "ORDERED_STAGE_RE",
    "ORDERED_STEP_RE",
    "RULES_HEADING_RE",
    "STEP_CAP",
    "TABLE_SEPARATOR_RE",
    "TItem",
    "TOP_HEADING_CAP",
    "VisualSection",
    "WARNING_HINT_RE",
    "_MERMAID_UNSAFE_RE",
    "_build_component_candidate",
    "_build_decision_candidate",
    "_build_heading_candidate",
    "_build_step_candidate",
    "_circled_number",
    "_collect_diagram_signals",
    "_dedupe_keep_order",
    "_derive_summary",
    "_derive_title",
    "_extract_action_items",
    "_extract_bullet_section",
    "_extract_checklist_steps",
    "_extract_components",
    "_extract_decision_lines",
    "_extract_file_like_items",
    "_extract_glossary",
    "_extract_heading_ranges",
    "_extract_mermaid_blocks",
    "_extract_ordered_steps",
    "_extract_sections",
    "_extract_table_rows",
    "_extract_tldr_one_liner",
    "_extract_warnings",
    "_first_meaningful_paragraph",
    "_generate_heuristic_diagrams",
    "_is_example_mermaid_context",
    "_iter_non_code_lines",
    "_ordered_step_parts",
    "_overview_override_hint",
    "_readme_override_hint",
    "_render_component_flow",
    "_render_heading_mindmap",
    "_render_step_flowchart",
    "_safe_mermaid_label",
    "_section_body_preview",
    "_section_summary",
    "_select_best_candidate",
    "_signal_score",
    "_slugify",
    "_split_mermaid_aware_lines",
    "_split_table_row",
    "_strip_inline_markdown",
    "_truncate_with_warning",
    "_usable_authored_diagrams",
    "build_artifact_shell",
    "compute_source_hash",
    "current_generated_at",
    "docs_visual_contract",
    "is_trusted_visual_artifact",
    "normalize_doc_text_bytes",
    "read_document_text",
    "source_generated_at",
    "trust_failure_reason",
    "visualize_markdown_bytes",
    "visualize_markdown_file",
]
# === ANCHOR: DOCS_VISUALIZER_END ===
