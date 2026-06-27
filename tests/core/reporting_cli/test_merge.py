from __future__ import annotations

from vibelign.core.reporting_cli.merge import merge_models
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _pair():
    base = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="S", blocks=[Block(kind="summary", text="원본")])],
    )
    polished = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="S", blocks=[Block(kind="summary", text="다듬")])],
    )
    return base, polished


def test_no_reject_keeps_all_polished():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[])
    assert merged.sections[0].blocks[0].text == "다듬"


def test_reject_keeps_base_for_that_block():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[(0, 0)])
    assert merged.sections[0].blocks[0].text == "원본"


def test_reject_out_of_range_is_ignored():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[(9, 9)])
    assert merged.sections[0].blocks[0].text == "다듬"
