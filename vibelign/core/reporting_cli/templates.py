# === ANCHOR: TEMPLATES_START ===
from __future__ import annotations

from dataclasses import dataclass

from vibelign.core.reporting_cli.models import (
    Block,
    PlanningData,
    ReportModel,
    Section,
)


@dataclass(frozen=True)
# === ANCHOR: TEMPLATES_SECTIONSPEC_START ===
class SectionSpec:
    heading: str  # 보고서에 보일 제목
    source: str  # PlanningData 필드명
    style: str  # "paragraph" | "bullets" | "summary"
# === ANCHOR: TEMPLATES_SECTIONSPEC_END ===


REPORT_TEMPLATES: dict[str, list[SectionSpec]] = {
    "work": [
        SectionSpec("개요", "idea", "summary"),
        SectionSpec("대상 / 배경", "target_users", "paragraph"),
        SectionSpec("핵심 내용", "features", "bullets"),
        SectionSpec("진행 / 사용 흐름", "flows", "bullets"),
        SectionSpec("주요 결정", "decisions", "bullets"),
        SectionSpec("이슈 / 남은 질문", "open_questions", "bullets"),
    ],
    "proposal": [
        SectionSpec("제안 요약", "idea", "summary"),
        SectionSpec("배경 / 문제", "problem", "paragraph"),
        SectionSpec("대상", "target_users", "paragraph"),
        SectionSpec("핵심 기능 / 가치", "features", "bullets"),
        SectionSpec("사용 흐름", "flows", "bullets"),
        SectionSpec("기대 효과 / 결정 사항", "decisions", "bullets"),
        SectionSpec("범위 제외", "exclusions", "bullets"),
    ],
    "result": [
        SectionSpec("목표", "idea", "summary"),
        SectionSpec("수행 내용", "features", "bullets"),
        SectionSpec("진행 흐름", "flows", "bullets"),
        SectionSpec("주요 결정", "decisions", "bullets"),
        SectionSpec("제외 / 미결", "open_questions", "bullets"),
        SectionSpec("참고 맥락", "context_notes", "paragraph"),
    ],
}

REPORT_TYPE_LABELS: dict[str, str] = {
    "work": "업무 보고",
    "proposal": "제안서",
    "result": "결과 보고",
    "doc": "문서 보고서",
}


# === ANCHOR: TEMPLATES__BLOCKS_FOR_START ===
def _blocks_for(value: object, style: str) -> list[Block]:
    if isinstance(value, list):
        items = [v for v in value if v]
        return [Block(kind="bullets", items=items)] if items else []
    text = str(value or "").strip()
    if not text:
        return []
    kind = "summary" if style == "summary" else "paragraph"
    return [Block(kind=kind, text=text)]
# === ANCHOR: TEMPLATES__BLOCKS_FOR_END ===


# === ANCHOR: TEMPLATES_META_LINE_START ===
def meta_line(model: ReportModel) -> str:
    """메타 줄: '{종류 라벨} · {날짜}', author 있으면 '· 작성자: {author}' 추가."""
    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    base = f"{label} · {model.date}"
    return f"{base} · 작성자: {model.author}" if getattr(model, "author", "") else base
# === ANCHOR: TEMPLATES_META_LINE_END ===


# === ANCHOR: TEMPLATES_BUILD_REPORT_MODEL_START ===
def build_report_model(
    data: PlanningData, report_type: str, *, date: str, source_plan_path: str = "", author: str = ""
# === ANCHOR: TEMPLATES_BUILD_REPORT_MODEL_END ===
) -> ReportModel:
    specs = REPORT_TEMPLATES.get(report_type)
    if specs is None:
        raise ValueError(f"unknown report type: {report_type}")
    sections: list[Section] = []
    for spec in specs:
        blocks = _blocks_for(getattr(data, spec.source), spec.style)
        if blocks:
            sections.append(Section(heading=spec.heading, blocks=blocks))
    title = data.title or data.idea or "보고서"
    return ReportModel(
        title=title,
        report_type=report_type,
        date=date,
        source_plan_path=source_plan_path,
        author=author,
        sections=sections,
    )
# === ANCHOR: TEMPLATES_END ===
