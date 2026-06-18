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


def test_render_and_write_nfc_normalizes_decomposed_korean(tmp_path: Path):
    # macOS 파일명 등에서 유입된 NFD(자모 분해) 한글이 Word 에서 풀려 보이던 버그 회귀.
    import unicodedata

    nfd = unicodedata.normalize("NFD", "기획안")
    assert any(0x1100 <= ord(c) <= 0x11FF for c in nfd)  # sanity: 입력은 분해형
    m = ReportModel(
        title=nfd, report_type="work", date="2026-06-18", author=nfd,
        sections=[Section(heading=nfd, blocks=[Block(kind="summary", text=nfd),
                                               Block(kind="bullets", items=[nfd])])],
    )
    dest = render_and_write(tmp_path, m, "html", slug_source="t", output=None, force=False)
    out = dest.read_text(encoding="utf-8")
    assert "기획안" in out
    # 출력에 결합용 자모(U+1100~U+11FF)가 남아있으면 안 된다(= 조합형으로 정규화됨).
    assert not any(0x1100 <= ord(c) <= 0x11FF for c in out)
