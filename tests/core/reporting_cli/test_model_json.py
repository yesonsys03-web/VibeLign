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


def test_author_roundtrips():
    m = ReportModel(title="t", report_type="work", date="d", author="홍길동", sections=[])
    assert model_from_dict(model_to_dict(m)).author == "홍길동"
