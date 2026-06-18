from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli.fonts import ReportFonts
from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.render_job import render_and_write


def _model():
    return ReportModel(
        title="리포트", report_type="work", date="2026-06-17",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text="요약")])],
    )


def test_render_and_write_html(tmp_path: Path):
    dest = render_and_write(tmp_path, _model(), "html", slug_source="리포트", output=None, force=False)
    assert dest.exists()
    assert dest.suffix == ".html"
    assert "요약" in dest.read_text(encoding="utf-8")


def test_render_and_write_html_embeds_selected_font(tmp_path: Path):
    dest = render_and_write(
        tmp_path, _model(), "html", slug_source="t", output=None, force=False,
        fonts=ReportFonts(body="pretendard"),
    )
    assert '"Pretendard"' in dest.read_text(encoding="utf-8")
