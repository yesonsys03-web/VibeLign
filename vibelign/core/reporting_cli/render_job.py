# === ANCHOR: RENDER_JOB_START ===
from __future__ import annotations

import unicodedata
from pathlib import Path

from vibelign.core.reporting_cli import (
    render_docx,
    render_html,
    render_pptx,
    write_report,
    write_report_bytes,
)
from vibelign.core.reporting_cli.font_sizes import ReportFontSizes
from vibelign.core.reporting_cli.fonts import ReportFonts
from vibelign.core.reporting_cli.models import ReportModel


def _normalize_model_nfc(model: ReportModel) -> None:
    """모델의 모든 표시 텍스트를 유니코드 NFC(조합형)로 정규화한다.
    macOS 파일시스템은 한글을 NFD(자모 분해)로 저장해, 파일명에서 유래한 텍스트가
    Word/PPT 에서 자모가 분리돼 보인다(=한글 풀림). 출력 직전 한 곳에서 합쳐 모든
    포맷을 일관되게 만든다. NFC 는 멱등이라 이미 조합형인 텍스트엔 영향이 없다."""
    def nfc(s: str) -> str:
        return unicodedata.normalize("NFC", s)

    model.title = nfc(model.title)
    model.author = nfc(model.author)
    for section in model.sections:
        section.heading = nfc(section.heading)
        for block in section.blocks:
            block.text = nfc(block.text)
            block.items = [nfc(item) for item in block.items]


def render_and_write(
    root: Path,
    model: ReportModel,
    fmt: str,
    *,
    slug_source: str,
    output: str | None,
    force: bool,
    theme: str = "classic",
    page_numbers: bool = False,
    font_sizes: ReportFontSizes | None = None,
    fonts: ReportFonts | None = None,
) -> Path:
    """모델을 fmt 로 렌더해 저장하고 경로를 반환한다.
    예외는 호출자가 처리: ReportRendererUnavailable / FileExistsError / ValueError."""
    _normalize_model_nfc(model)
    if fmt == "docx":
        data_bytes = render_docx(
            model,
            theme=theme,
            page_numbers=page_numbers,
            font_sizes=font_sizes,
            fonts=fonts,
        )
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".docx", output=output, force=force
        )
    if fmt == "pptx":
        data_bytes = render_pptx(model, theme=theme, font_sizes=font_sizes, fonts=fonts)
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".pptx", output=output, force=force
        )
    html = render_html(model, theme=theme, font_sizes=font_sizes, fonts=fonts)
    return write_report(root, model, html, slug_source=slug_source, output=output, force=force)
# === ANCHOR: RENDER_JOB_END ===
