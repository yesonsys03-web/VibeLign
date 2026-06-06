# === ANCHOR: DOCS_VISUALIZER_EXTRACT_START ===
from __future__ import annotations

import re
from typing import Optional

from .docs_visualizer_models import ActionItem, GlossaryEntry, VisualSection
from .docs_visualizer_text import (
    ACTION_HEADING_RE,
    BULLET_RE,
    CHECKLIST_RE,
    COMMAND_HINT_RE,
    COMPONENT_CAP,
    DECISION_HINT_RE,
    FILE_LIKE_RE,
    GLOSSARY_LINE_RE,
    HEADING_RE,
    TABLE_SEPARATOR_RE,
    WARNING_HINT_RE,
    _dedupe_keep_order,
    _extract_heading_ranges,
    _first_meaningful_paragraph,
    _iter_non_code_lines,
    _ordered_step_parts,
    _slugify,
    _split_table_row,
    _strip_inline_markdown,
)


# === ANCHOR: DOCS_VISUALIZER__SECTION_SUMMARY_START ===
def _section_summary(section_lines: list[str]) -> str:
    return _first_meaningful_paragraph(section_lines)
# === ANCHOR: DOCS_VISUALIZER__SECTION_SUMMARY_END ===


def _section_body_preview(section_lines: list[str], limit: int = 5) -> list[str]:
    preview: list[str] = []
    in_code = False
    for raw in section_lines:
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped or HEADING_RE.match(raw) or TABLE_SEPARATOR_RE.match(stripped):
            continue

        checklist = CHECKLIST_RE.match(raw)
        if checklist:
            marker = "x" if checklist.group("checked").lower() == "x" else " "
            text = f"[{marker}] {_strip_inline_markdown(checklist.group('text'))}"
        else:
            ordered_num, ordered_text, _indent = _ordered_step_parts(raw)
            bullet = BULLET_RE.match(raw)
            if ordered_num is not None and ordered_text:
                text = f"{ordered_num}. {_strip_inline_markdown(ordered_text)}"
            elif bullet:
                text = _strip_inline_markdown(bullet.group("text"))
            elif stripped.startswith("|"):
                text = " | ".join(_split_table_row(stripped))
            else:
                text = _strip_inline_markdown(stripped)

        if text and text not in preview:
            preview.append(text)
        if len(preview) >= limit:
            break
    return preview


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
                body_preview=_section_body_preview(lines[start + 1 : end]),
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
# === ANCHOR: DOCS_VISUALIZER_EXTRACT_END ===
