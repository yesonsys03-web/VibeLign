# === ANCHOR: PDF_STAMP_START ===
from __future__ import annotations

import io
from pathlib import Path


def stamp_page_numbers(pdf_path: Path) -> int:
    """PDF 각 페이지 하단 중앙에 'N / M' 을 찍고 in-place 교체한다. 페이지 수 반환.
    손상 PDF 등은 예외를 던진다(호출자가 graceful 처리)."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width) or A4[0]
        height = float(page.mediabox.height) or A4[1]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(width, height))
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, 24, f"{i} / {total}")
        c.save()
        buf.seek(0)
        overlay = PdfReader(buf).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)
    tmp = pdf_path.with_suffix(".pdf.tmp")
    with open(tmp, "wb") as f:
        writer.write(f)
    tmp.replace(pdf_path)
    return total
# === ANCHOR: PDF_STAMP_END ===
