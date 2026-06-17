from __future__ import annotations

from pathlib import Path


def _two_page_pdf(p: Path) -> None:
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(p))
    c.drawString(72, 720, "page one")
    c.showPage()
    c.drawString(72, 720, "page two")
    c.showPage()
    c.save()


def test_stamp_adds_n_of_m(tmp_path: Path):
    from pypdf import PdfReader

    from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers

    pdf = tmp_path / "r.pdf"
    _two_page_pdf(pdf)
    pages = stamp_page_numbers(pdf)
    assert pages == 2
    text = "".join(pg.extract_text() or "" for pg in PdfReader(str(pdf)).pages)
    assert "1 / 2" in text and "2 / 2" in text


def test_stamp_bad_pdf_raises(tmp_path: Path):
    import pytest

    from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(Exception):
        stamp_page_numbers(bad)
