# === ANCHOR: FONTS_START ===
from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

FONTS_DIR: Final = Path(__file__).resolve().parent / "fonts"

_SANS_FALLBACK: Final = '"Apple SD Gothic Neo","Malgun Gothic",sans-serif'
_SERIF_FALLBACK: Final = '"Apple SD Gothic Neo","Batang",serif'


@dataclass(frozen=True, slots=True)
class FontFace:
    file: str
    weight: int


@dataclass(frozen=True, slots=True)
class FontDef:
    id: str
    label: str
    office_name: str          # Word/PPT run.font.name 에 쓰는 설치 폰트명
    css_stack: str            # @font-face family + 폴백 체인
    faces: tuple[FontFace, ...]

    @property
    def family(self) -> str:
        return self.css_stack.split(",", 1)[0].strip().strip('"')


REPORT_FONTS: Final[dict[str, FontDef]] = {
    f.id: f
    for f in (
        FontDef("pretendard", "Pretendard", "Pretendard",
                f'"Pretendard",{_SANS_FALLBACK}',
                (FontFace("pretendard/pretendard-400.woff2", 400), FontFace("pretendard/pretendard-700.woff2", 700))),
        FontDef("nanum-myeongjo", "나눔명조", "나눔명조",
                f'"NanumMyeongjo",{_SERIF_FALLBACK}',
                (FontFace("nanum-myeongjo/nanum-myeongjo-400.woff2", 400), FontFace("nanum-myeongjo/nanum-myeongjo-700.woff2", 700))),
        FontDef("gowun-batang", "고운바탕", "고운바탕",
                f'"Gowun Batang",{_SERIF_FALLBACK}',
                (FontFace("gowun-batang/gowun-batang-400.woff2", 400), FontFace("gowun-batang/gowun-batang-700.woff2", 700))),
        FontDef("gowun-dodum", "고운돋움", "고운돋움",
                f'"Gowun Dodum",{_SANS_FALLBACK}',
                (FontFace("gowun-dodum/gowun-dodum-400.woff2", 400),)),
        FontDef("black-han-sans", "검은고딕", "Black Han Sans",
                f'"Black Han Sans",{_SANS_FALLBACK}',
                (FontFace("black-han-sans/black-han-sans-400.woff2", 400),)),
    )
}


def font_def(font_id: str) -> FontDef | None:
    return REPORT_FONTS.get(font_id)


@lru_cache(maxsize=16)
def _face_data_uri(face_rel_path: str) -> str:
    """Return a data URI for the woff2 file at FONTS_DIR / face_rel_path."""
    raw = (FONTS_DIR / face_rel_path).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


@dataclass(frozen=True, slots=True)
class ReportFonts:
    heading: str | None = None
    body: str | None = None

    def has_overrides(self) -> bool:
        return self.heading is not None or self.body is not None


def normalize_report_fonts(*, heading: str | None = None, body: str | None = None) -> ReportFonts:
    h = heading or None
    b = body or None
    for label, fid in (("제목", h), ("본문", b)):
        if fid is not None and fid not in REPORT_FONTS:
            raise ValueError(f"알 수 없는 {label} 폰트예요: {fid}")
    return ReportFonts(heading=h, body=b)


def _face_rules(fdef: FontDef) -> str:
    rules = []
    for face in fdef.faces:
        rules.append(
            f'@font-face {{ font-family:"{fdef.family}"; '
            f"font-weight:{face.weight}; font-style:normal; font-display:swap; "
            f"src:url({_face_data_uri(face.file)}) format('woff2'); }}"
        )
    return "\n".join(rules)


def font_family_override_css(
    fonts: ReportFonts, *, default_heading: str, default_body: str
) -> str:
    if not fonts.has_overrides():
        return ""
    heading_def = REPORT_FONTS.get(fonts.heading) if fonts.heading else None
    body_def = REPORT_FONTS.get(fonts.body) if fonts.body else None
    heading_stack = heading_def.css_stack if heading_def else default_heading
    body_stack = body_def.css_stack if body_def else default_body
    parts: list[str] = []
    for fdef in {f.id: f for f in (heading_def, body_def) if f}.values():
        parts.append(_face_rules(fdef))
    parts.append(
        f"body, p, li, ul, p.summary, p.meta {{ font-family:{body_stack}; }}"
    )
    parts.append(f"h1, h2 {{ font-family:{heading_stack}; }}")
    return "\n".join(parts)
# === ANCHOR: FONTS_END ===
