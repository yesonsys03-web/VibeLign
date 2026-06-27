# === ANCHOR: VENDOR_REPORT_FONTS_START ===
"""보고서용 OFL 한글 폰트를 내려받아 woff2 로 변환해 fonts/ 에 넣는다(1회용).
사용: uv run python scripts/vendor_report_fonts.py
요구: fonttools, brotli (uv pip install fonttools brotli)
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont

DEST = Path(__file__).resolve().parent.parent / "vibelign/core/reporting_cli/fonts"
GF = "https://github.com/google/fonts/raw/main/ofl"
PRE = "https://github.com/orioncactus/pretendard/raw/main/packages/pretendard/dist/web/static"

# (font_id, [(url, out_filename, needs_woff2_conversion)], license_url)
SOURCES = [
    ("pretendard", [
        (f"{PRE}/woff2/Pretendard-Regular.woff2", "pretendard-400.woff2", False),
        (f"{PRE}/woff2/Pretendard-Bold.woff2", "pretendard-700.woff2", False),
    ], "https://github.com/orioncactus/pretendard/raw/main/LICENSE"),
    ("nanum-myeongjo", [
        (f"{GF}/nanummyeongjo/NanumMyeongjo-Regular.ttf", "nanum-myeongjo-400.woff2", True),
        (f"{GF}/nanummyeongjo/NanumMyeongjo-Bold.ttf", "nanum-myeongjo-700.woff2", True),
    ], f"{GF}/nanummyeongjo/OFL.txt"),
    ("gowun-batang", [
        (f"{GF}/gowunbatang/GowunBatang-Regular.ttf", "gowun-batang-400.woff2", True),
        (f"{GF}/gowunbatang/GowunBatang-Bold.ttf", "gowun-batang-700.woff2", True),
    ], f"{GF}/gowunbatang/OFL.txt"),
    ("gowun-dodum", [
        (f"{GF}/gowundodum/GowunDodum-Regular.ttf", "gowun-dodum-400.woff2", True),
    ], f"{GF}/gowundodum/OFL.txt"),
    ("black-han-sans", [
        (f"{GF}/blackhansans/BlackHanSans-Regular.ttf", "black-han-sans-400.woff2", True),
    ], f"{GF}/blackhansans/OFL.txt"),
]


# === ANCHOR: VENDOR_REPORT_FONTS__FETCH_START ===
def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "vibelign-vendor"})
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return resp.read()
# === ANCHOR: VENDOR_REPORT_FONTS__FETCH_END ===


# === ANCHOR: VENDOR_REPORT_FONTS_MAIN_START ===
def main() -> None:
    for font_id, files, license_url in SOURCES:
        out_dir = DEST / font_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "OFL.txt").write_bytes(_fetch(license_url))
        for url, out_name, convert in files:
            raw = _fetch(url)
            if convert:
                font = TTFont(io.BytesIO(raw))
                font.flavor = "woff2"
                buf = io.BytesIO()
                font.save(buf)
                raw = buf.getvalue()
            (out_dir / out_name).write_bytes(raw)
            print(f"  wrote {out_dir / out_name} ({len(raw) // 1024} KB)")
# === ANCHOR: VENDOR_REPORT_FONTS_MAIN_END ===


if __name__ == "__main__":
    main()
# === ANCHOR: VENDOR_REPORT_FONTS_END ===
