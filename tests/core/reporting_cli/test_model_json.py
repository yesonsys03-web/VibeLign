from __future__ import annotations

import pytest

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.model_json import model_from_dict, model_to_dict


def _sample() -> ReportModel:
    return ReportModel(
        title="예약 앱",
        report_type="work",
        date="2026-06-17",
        source_plan_path="plans/p.md",
        sections=[
            Section(heading="개요", blocks=[Block(kind="summary", text="요약")]),
            Section(heading="핵심", blocks=[Block(kind="bullets", items=["a", "b"])]),
        ],
    )


def test_roundtrip_preserves_model():
    model = _sample()
    restored = model_from_dict(model_to_dict(model))
    assert restored == model


def test_from_dict_rejects_invalid_block_kind():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"][0]["kind"] = "evil"
    with pytest.raises(ValueError):
        model_from_dict(bad)


def test_from_dict_rejects_missing_field():
    with pytest.raises(ValueError):
        model_from_dict({"title": "x", "sections": []})  # report_type/date 누락


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", 1),
        ("report_type", 1),
        ("date", 1),
        ("source_plan_path", 1),
        ("author", 1),
    ],
)
def test_from_dict_rejects_non_string_display_fields(field: str, value: int):
    bad = model_to_dict(_sample())
    bad[field] = value

    with pytest.raises(ValueError, match=field):
        model_from_dict(bad)


def test_from_dict_rejects_non_dict_section():
    bad = model_to_dict(_sample())
    bad["sections"] = ["not-section"]

    with pytest.raises(ValueError, match="section"):
        model_from_dict(bad)


def test_from_dict_rejects_non_string_section_heading():
    bad = model_to_dict(_sample())
    bad["sections"][0]["heading"] = 1

    with pytest.raises(ValueError, match="heading"):
        model_from_dict(bad)


def test_from_dict_rejects_non_list_blocks():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"] = "not-blocks"

    with pytest.raises(ValueError, match="blocks"):
        model_from_dict(bad)


def test_from_dict_rejects_non_dict_block():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"] = ["not-block"]

    with pytest.raises(ValueError, match="block"):
        model_from_dict(bad)


def test_from_dict_rejects_non_string_block_text():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"][0]["text"] = 1

    with pytest.raises(ValueError, match="text"):
        model_from_dict(bad)


def test_from_dict_rejects_non_list_items():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"][0]["items"] = 1

    with pytest.raises(ValueError, match="items"):
        model_from_dict(bad)


def test_from_dict_rejects_non_string_item_entries():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"][0]["items"] = ["ok", 1]

    with pytest.raises(ValueError, match="items"):
        model_from_dict(bad)


def test_image_model_preserves_source(tmp_path) -> None:
    from vibelign.core.reporting_cli.report_card_news_payload import load_visual_cards_payload
    payload = tmp_path / "p.json"
    payload.write_text(
        '{"schema_version":"report-visual-cards-v1","status":"ready","provider":"agy",'
        '"cards":[{"id":"c1","title":"t","body":"b","caption":"","visual_prompt":"",'
        '"negative_prompt":"","source_refs":[],"approved":true,'
        '"image":{"provider":"agy","asset_path":"","prompt":"","generated":true,"source":"llm"}}]}',
        encoding="utf-8",
    )
    loaded = load_visual_cards_payload(payload)
    assert loaded["cards"][0]["image"]["source"] == "llm"


def test_author_roundtrips():
    m = ReportModel(title="t", report_type="work", date="d", author="홍길동", sections=[])
    assert model_from_dict(model_to_dict(m)).author == "홍길동"


def test_report_model_json_excludes_emit_sidecars():
    model = _sample()
    serialized = model_to_dict(model)
    serialized["quality"] = {"schema_version": "report-quality-v1", "findings": []}
    serialized["assistance"] = {"schema_version": "report-assist-v1", "status": "not_requested"}

    restored = model_from_dict(serialized)
    roundtripped = model_to_dict(restored)

    assert "quality" not in model_to_dict(model)
    assert "assistance" not in model_to_dict(model)
    assert "quality" not in roundtripped
    assert "assistance" not in roundtripped
    assert restored == model
