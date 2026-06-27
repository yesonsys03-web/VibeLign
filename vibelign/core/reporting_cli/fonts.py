# === ANCHOR: FONTS_START ===
from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Final

# 패키지 내 폰트 디렉터리. 런타임 woff2 접근은 _face_traversable()(importlib.resources)
# 을 쓴다 — PyInstaller onedir 같은 frozen 번들에서 __file__ 경로가 신뢰 불가하기 때문
# (schema_contracts._load_schema 와 동일한 검증된 패턴). FONTS_DIR 는 dev/sdist 디스크
# 검증 테스트용 편의 경로일 뿐, 런타임 로딩 경로가 아니다.
_FONTS_ANCHOR_PKG: Final = "vibelign.core.reporting_cli"
FONTS_DIR: Final = Path(__file__).resolve().parent / "fonts"


def _face_traversable(face_rel_path: str):
    """번들 환경 무관하게 woff2 리소스를 가리키는 Traversable 을 돌려준다.
    face_rel_path 예: 'pretendard/pretendard-400.woff2'."""
    return resources.files(_FONTS_ANCHOR_PKG).joinpath("fonts", *face_rel_path.split("/"))

_SANS_FALLBACK: Final = '"Apple SD Gothic Neo","Malgun Gothic",sans-serif'
_SERIF_FALLBACK: Final = '"Apple SD Gothic Neo","Batang",serif'


@dataclass(frozen=True)
class FontFace:
    file: str
    weight: int


@dataclass(frozen=True)
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
    """woff2 리소스를 base64 data URI 로 돌려준다(frozen 번들 안전)."""
    raw = _face_traversable(face_rel_path).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


@dataclass(frozen=True)
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
        # 번들에 woff2 가 없으면(부분 설치 등) 임베딩만 건너뛴다. font-family 규칙은
        # 호출부가 그대로 emit 하므로 시스템 설치 폰트/폴백 체인으로 degrade — 렌더는 안 깨진다.
        if not _face_traversable(face.file).is_file():
            continue
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
