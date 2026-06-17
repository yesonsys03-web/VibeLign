# === ANCHOR: MODEL_JSON_START ===
from __future__ import annotations

from vibelign.core.reporting_cli.models import Block, ReportModel, Section

_ALLOWED_KINDS = {"paragraph", "bullets", "summary"}


def model_to_dict(model: ReportModel) -> dict:
    """ReportModel 을 JSON 직렬화 가능한 dict 로. (dataclasses.asdict 와 동일 구조)"""
    return {
        "title": model.title,
        "report_type": model.report_type,
        "date": model.date,
        "source_plan_path": model.source_plan_path,
        "author": model.author,
        "sections": [
            {
                "heading": s.heading,
                "blocks": [
                    {"kind": b.kind, "text": b.text, "items": list(b.items)}
                    for b in s.blocks
                ],
            }
            for s in model.sections
        ],
    }


def model_from_dict(data: object) -> ReportModel:
    """dict 를 ReportModel 로 복원하며 스키마를 검증한다. 신뢰 못 할 입력의 관문."""
    if not isinstance(data, dict):
        raise ValueError("model 은 객체여야 합니다")
    for required in ("title", "report_type", "date"):
        if required not in data:
            raise ValueError(f"model 필수 필드 누락: {required}")
    sections_raw = data.get("sections", [])
    if not isinstance(sections_raw, list):
        raise ValueError("sections 는 리스트여야 합니다")
    sections: list[Section] = []
    for s in sections_raw:
        if not isinstance(s, dict) or "heading" not in s:
            raise ValueError("section 에 heading 이 필요합니다")
        blocks: list[Block] = []
        for b in s.get("blocks", []):
            kind = b.get("kind") if isinstance(b, dict) else None
            if kind not in _ALLOWED_KINDS:
                raise ValueError(f"잘못된 block kind: {kind!r}")
            blocks.append(
                Block(kind=kind, text=b.get("text", ""), items=list(b.get("items", [])))
            )
        sections.append(Section(heading=s["heading"], blocks=blocks))
    return ReportModel(
        title=data["title"],
        report_type=data["report_type"],
        date=data["date"],
        source_plan_path=data.get("source_plan_path", ""),
        author=data.get("author", ""),
        sections=sections,
    )
# === ANCHOR: MODEL_JSON_END ===
