from __future__ import annotations

import re

from vibelign.core.reporting_cli.models import Block, PlanningData, ReportModel, Section

_FIELD_BY_HEADING = {
    "한 줄 목표": "idea",
    "만들고 싶은 이유": "problem",
    "대상 사용자": "target_users",
    "핵심 문제": "problem",
    "핵심 기능": "features",
    "화면 또는 사용 흐름": "flows",
    "사용자 흐름": "flows",
    "확정된 결정": "decisions",
    "제외할 것": "exclusions",
    "아직 결정이 필요한 질문": "open_questions",
    "구현 전에 AI가 알아야 할 맥락": "context_notes",
}

_LIST_FIELDS = {"features", "flows", "decisions", "exclusions", "open_questions"}


def _strip_placeholder(value: str) -> str:
    return "" if "아직 결정이 필요" in value else value


def _strip_bullet(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("- ") or stripped.startswith("* "):
        return stripped[2:].strip()
    numbered = re.match(r"^\d+[\.)]\s+(?P<item>.+)$", stripped)
    if numbered:
        return numbered.group("item").strip()
    return stripped


def parse_plan_markdown(text: str) -> PlanningData:
    data = PlanningData()
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if current and current not in _LIST_FIELDS:
            # GUI 합성기는 단락 필드도 불릿(- …)으로 쓰므로 마커를 벗긴다.
            joined = " ".join(s for b in buf if (s := _strip_bullet(b)))
            value = _strip_placeholder(joined)
            if value:
                setattr(data, current, value)
        buf = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            current = None
            data.title = line[2:].strip()
            continue
        if line.startswith("## "):
            flush()
            current = _FIELD_BY_HEADING.get(line[3:].strip())
            continue
        if current is None:
            continue
        if current in _LIST_FIELDS:
            item = _strip_placeholder(_strip_bullet(line))
            if item:
                getattr(data, current).append(item)
        else:
            buf.append(line)

    flush()
    return data


_BULLET_RE = re.compile(r"^(?:[-*]\s+|\d+[.)]\s+)")


def parse_generic_markdown(text: str) -> tuple[str, list[Section]]:
    """임의 마크다운을 (제목, 섹션[]) 으로 변환한다(기획 양식 무관).
    첫 '# ' → 제목, 이후 '#'~'######' → 섹션 경계, 단락 → paragraph,
    불릿/번호 → bullets. 첫 헤딩 이전 본문과 헤딩 없는 문서는 '개요' 섹션으로 보존한다.
    """
    title = ""
    sections: list[Section] = []
    heading: str | None = None
    para: list[str] = []
    bullets: list[str] = []
    blocks: list[Block] = []

    def flush_para() -> None:
        nonlocal para
        joined = " ".join(s for s in (p.strip() for p in para) if s)
        if joined:
            blocks.append(Block(kind="paragraph", text=joined))
        para = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            blocks.append(Block(kind="bullets", items=bullets))
        bullets = []

    def flush_section() -> None:
        nonlocal blocks
        flush_bullets()
        flush_para()
        if blocks:
            sections.append(Section(heading=heading or "개요", blocks=blocks))
        blocks = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        h1 = line.startswith("# ") and not line.startswith("## ")
        if h1 and not title:
            title = line[2:].strip()
            continue
        m = re.match(r"^(#{1,6})\s+(?P<h>.+)$", line)
        if m:
            flush_section()
            heading = m.group("h").strip()
            continue
        stripped = line.strip()
        if _BULLET_RE.match(stripped):
            flush_para()
            item = _strip_bullet(line)
            if item:
                bullets.append(item)
            continue
        if not stripped:
            flush_bullets()
            flush_para()
            continue
        flush_bullets()
        para.append(line)

    flush_section()
    return title, sections


def build_doc_report_model(
    text: str,
    *,
    date: str,
    source_plan_path: str = "",
    author: str = "",
    default_title: str = "문서 보고서",
) -> ReportModel:
    """임의 .md → '문서 그대로' ReportModel(report_type='doc')."""
    title, sections = parse_generic_markdown(text)
    return ReportModel(
        title=title or default_title,
        report_type="doc",
        date=date,
        source_plan_path=source_plan_path,
        author=author,
        sections=sections,
    )
