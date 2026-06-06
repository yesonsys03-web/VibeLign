# === ANCHOR: DOCS_VISUALIZER_DIAGRAM_START ===
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
from typing import Optional

from .docs_visualizer_models import (
    ActionItem,
    DiagramBlock,
    DiagramCandidate,
    DiagramSignals,
    VisualSection,
)
from .docs_visualizer_text import (
    COMPONENT_CAP,
    DOC_KIND_HINTS,
    FILE_LIKE_RE,
    MERMAID_LEADING_RE,
    STEP_CAP,
    TOP_HEADING_CAP,
    _MERMAID_UNSAFE_RE,
    _dedupe_keep_order,
    _extract_heading_ranges,
    _overview_override_hint,
    _readme_override_hint,
    _split_mermaid_aware_lines,
)
from .docs_visualizer_extract import (
    _extract_checklist_steps,
    _extract_decision_lines,
    _extract_file_like_items,
    _extract_ordered_steps,
    _extract_table_rows,
)


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
# === ANCHOR: DOCS_VISUALIZER_DIAGRAM_END ===
