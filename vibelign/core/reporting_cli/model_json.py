# === ANCHOR: MODEL_JSON_START ===
from __future__ import annotations

from typing import Final, TypeAlias

from vibelign.core.reporting_cli.models import Block, ReportModel, Section

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

_ALLOWED_KINDS: Final = frozenset({"paragraph", "bullets", "summary"})


def _require_string(raw: JsonObject, field: str) -> str:
    value = raw.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} 는 문자열이어야 합니다")
    return value


def _require_string_items(raw: JsonObject) -> list[str]:
    items = raw.get("items", [])
    if not isinstance(items, list):
        raise ValueError("items 는 리스트여야 합니다")
    string_items: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError("items 항목은 문자열이어야 합니다")
        string_items.append(item)
    return string_items


def model_to_dict(model: ReportModel) -> JsonObject:
    """ReportModel 을 JSON 직렬화 가능한 dict 로. (dataclasses.asdict 와 동일 구조)"""
    sections: list[JsonValue] = []
    for section in model.sections:
        blocks: list[JsonValue] = []
        for block in section.blocks:
            items: list[JsonValue] = []
            items.extend(block.items)
            blocks.append({"kind": block.kind, "text": block.text, "items": items})
        sections.append({"heading": section.heading, "blocks": blocks})
    return {
        "title": model.title,
        "report_type": model.report_type,
        "date": model.date,
        "source_plan_path": model.source_plan_path,
        "author": model.author,
        "sections": sections,
    }


def model_from_dict(data: JsonValue) -> ReportModel:
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
        if not isinstance(s, dict):
            raise ValueError("section 은 객체여야 합니다")
        if "heading" not in s:
            raise ValueError("section 에 heading 이 필요합니다")
        blocks_raw = s.get("blocks", [])
        if not isinstance(blocks_raw, list):
            raise ValueError("blocks 는 리스트여야 합니다")
        blocks: list[Block] = []
        for b in blocks_raw:
            if not isinstance(b, dict):
                raise ValueError("block 은 객체여야 합니다")
            kind = b.get("kind")
            if not isinstance(kind, str) or kind not in _ALLOWED_KINDS:
                raise ValueError(f"잘못된 block kind: {kind!r}")
            blocks.append(
                Block(
                    kind=kind,
                    text=_require_string(b, "text"),
                    items=_require_string_items(b),
                )
            )
        sections.append(Section(heading=_require_string(s, "heading"), blocks=blocks))
    return ReportModel(
        title=_require_string(data, "title"),
        report_type=_require_string(data, "report_type"),
        date=_require_string(data, "date"),
        source_plan_path=_require_string(data, "source_plan_path"),
        author=_require_string(data, "author"),
        sections=sections,
    )
# === ANCHOR: MODEL_JSON_END ===
