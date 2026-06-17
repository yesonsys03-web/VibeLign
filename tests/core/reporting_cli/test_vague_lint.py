from __future__ import annotations

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.vague_lint import lint_model


def _model(text: str) -> ReportModel:
    return ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text=text)])],
    )


def test_detects_vague_term_with_offset():
    out = lint_model(_model("성과가 대폭 좋아졌다"))
    assert out == [{"section": 0, "block": 0, "term": "대폭", "offset": 4}]


def test_clean_text_returns_empty():
    assert lint_model(_model("매출이 50% 늘었다")) == []


def test_ignores_bullets():
    model = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="bullets", items=["대폭 증가"])])],
    )
    assert lint_model(model) == []
