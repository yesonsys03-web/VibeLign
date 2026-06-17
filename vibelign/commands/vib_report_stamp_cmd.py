# === ANCHOR: VIB_REPORT_STAMP_CMD_START ===
from __future__ import annotations

import json
import sys
from pathlib import Path


def run_vib_report_stamp(args: object) -> None:
    """생성된 PDF 에 페이지 번호를 스탬프한다. 실패해도 원본 PDF 는 보존(호출자가 graceful)."""
    pdf = Path(getattr(args, "pdf", "")).expanduser()
    want_json = bool(getattr(args, "json", False))
    if not pdf.exists():
        msg = f"PDF 를 찾을 수 없어요: {pdf}"
        if want_json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        raise SystemExit(1)
    try:
        from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers

        pages = stamp_page_numbers(pdf)
    except Exception as exc:  # noqa: BLE001 — graceful: 원본 PDF 유지
        print(json.dumps({"ok": False, "error": f"페이지 번호 스탬프 실패: {exc}"}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps({"ok": True, "path": str(pdf), "pages": pages}, ensure_ascii=False))
# === ANCHOR: VIB_REPORT_STAMP_CMD_END ===
