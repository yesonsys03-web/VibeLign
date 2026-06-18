# 보고서 폰트 선택 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보고서 작성에서 사용자가 제목용/본문용 한글 폰트(전부 OFL 무료)를 독립 선택하고, PDF·미리보기·Word·PPT 전부에 반영한다.

**Architecture:** 폰트 크기(`font_sizes`)가 이미 동작하는 경로(UI → CLI 인자 → Python 렌더러)를 1:1로 따라 "폰트 종류"를 추가한다. 폰트는 테마 CSS 위에 덧씌우는 **오버라이드 레이어**다. PDF/미리보기는 선택된 woff2를 base64 `@font-face`로 HTML에 임베딩하고, Word/PPT는 `run.font.name`(+한글용 eastAsia XML)으로 이름을 지정한다.

**Tech Stack:** Python 3.12 (pytest, ruff), python-docx/pptx, fontTools(woff2 변환), React + TypeScript (vitest), Tauri.

## Global Constraints

- **OFL 폰트만 사용** — 번들 5종: `pretendard`, `nanum-myeongjo`, `gowun-batang`, `gowun-dodum`, `black-han-sans`. 각 폰트 디렉터리에 OFL 라이선스 동봉.
- **앵커 경계 준수** — `# === ANCHOR: NAME_START ===` ~ `_END` 사이만 수정. 기존 앵커 밖 코드 변경 금지.
- **최소 패치** — 요청 범위 밖 리팩터링 금지. 기존 함수 시그니처는 새 인자를 **기본값 있는 선택 인자**로만 추가(하위호환).
- **기본값 "테마 기본값"** — 폰트 미지정 시 오버라이드 0 → 기존 75개 테마 동작 불변(회귀 보장).
- **폰트 ID는 단일 진실원천** — Python `fonts.py` 레지스트리와 TS `reportFonts.ts` 의 ID 목록이 정확히 일치해야 함: `pretendard / nanum-myeongjo / gowun-batang / gowun-dodum / black-han-sans`.
- 테스트: Python `pytest`, 린트 `ruff check`. TS `cd vibelign-gui && npm test` (vitest).

---

## File Structure

**신규 (Python)**
- `vibelign/core/reporting_cli/fonts.py` — 폰트 레지스트리 + `ReportFonts` + `normalize_report_fonts()` + `font_family_override_css()`
- `vibelign/core/reporting_cli/fonts/<id>/*.woff2` + `OFL.txt` — 번들 폰트 자산
- `scripts/vendor_report_fonts.py` — 폰트 다운로드·woff2 변환 1회용 스크립트
- `tests/core/reporting_cli/test_fonts.py` — 레지스트리/CSS 단위 테스트

**수정 (Python)**
- `vibelign/core/reporting_cli/html_renderer.py` — `render_html(..., fonts=None)` + 오버라이드 CSS append
- `vibelign/core/reporting_cli/docx_renderer.py` — `render_docx(..., fonts=None)` + 한글 eastAsia 폰트 지정
- `vibelign/core/reporting_cli/pptx_renderer.py` — `render_pptx(..., fonts=None)` + 한글 ea 폰트 지정
- `vibelign/core/reporting_cli/render_job.py` — `render_and_write(..., fonts=None)` 라우팅
- `vibelign/commands/vib_report_cmd.py` — `ReportArgs` 확장 + `normalize_report_fonts` 호출 + 두 render 호출에 `fonts=` 전달
- `vibelign/cli/cli_command_groups.py` — `--heading-font` / `--body-font` argparse 등록
- `vib.spec` — fonts 디렉터리를 `datas` + `fonts` 모듈을 `hiddenimports` 에 추가

**신규 (TS)**
- `vibelign-gui/src/lib/vib/reportFonts.ts` — `ReportFonts` 타입 + 옵션 목록 + `reportFontArgs()`
- `vibelign-gui/src/components/plan-doc/ReportFontSelect.tsx` — 제목/본문 폰트 드롭다운
- `vibelign-gui/src/lib/vib/__tests__/reportFonts.test.ts` — `reportFontArgs` 단위 테스트

**수정 (TS)**
- `vibelign-gui/src/lib/vib/report.ts` — `generatePlanningReport`/`generateReportPdf`/`generateReportOffice`/`renderReportWithDecisions` 에 `fonts` 인자
- `vibelign-gui/src/components/plan-doc/ReportComposer.tsx` — `fonts` 상태 + UI + 전달
- `vibelign-gui/src/pages/ReportView.tsx` — review 경로에 `fonts`(+누락된 `fontSizes`) 정합화

---

## Task 1: 폰트 레지스트리 + 자산 벤더링

**Files:**
- Create: `vibelign/core/reporting_cli/fonts.py`
- Create: `scripts/vendor_report_fonts.py`
- Create: `vibelign/core/reporting_cli/fonts/<id>/*.woff2`, `OFL.txt`
- Test: `tests/core/reporting_cli/test_fonts.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True, slots=True) class FontFace: file: str; weight: int`
  - `@dataclass(frozen=True, slots=True) class FontDef: id: str; label: str; office_name: str; css_stack: str; faces: tuple[FontFace, ...]`
  - `REPORT_FONTS: dict[str, FontDef]` (5개)
  - `FONTS_DIR: Path` — woff2 자산 루트
  - `def font_def(font_id: str) -> FontDef | None`

- [ ] **Step 1: 벤더링 스크립트 작성**

`scripts/vendor_report_fonts.py`:

```python
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


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "vibelign-vendor"})
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return resp.read()


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


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 벤더링 실행**

Run:
```bash
uv pip install fonttools brotli
uv run python scripts/vendor_report_fonts.py
```
Expected: `vibelign/core/reporting_cli/fonts/<id>/` 아래에 8개 woff2 + 5개 OFL.txt 생성. 각 woff2 매직바이트 `wOF2`. (URL 변동 시 SOURCES 의 경로를 해당 저장소 최신 경로로 수정.)

- [ ] **Step 3: 레지스트리 모듈 작성**

`vibelign/core/reporting_cli/fonts.py`:

```python
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
                (FontFace("pretendard-400.woff2", 400), FontFace("pretendard-700.woff2", 700))),
        FontDef("nanum-myeongjo", "나눔명조", "나눔명조",
                f'"NanumMyeongjo",{_SERIF_FALLBACK}',
                (FontFace("nanum-myeongjo-400.woff2", 400), FontFace("nanum-myeongjo-700.woff2", 700))),
        FontDef("gowun-batang", "고운바탕", "고운바탕",
                f'"Gowun Batang",{_SERIF_FALLBACK}',
                (FontFace("gowun-batang-400.woff2", 400), FontFace("gowun-batang-700.woff2", 700))),
        FontDef("gowun-dodum", "고운돋움", "고운돋움",
                f'"Gowun Dodum",{_SANS_FALLBACK}',
                (FontFace("gowun-dodum-400.woff2", 400),)),
        FontDef("black-han-sans", "검은고딕", "Black Han Sans",
                f'"Black Han Sans",{_SANS_FALLBACK}',
                (FontFace("black-han-sans-400.woff2", 400),)),
    )
}


def font_def(font_id: str) -> FontDef | None:
    return REPORT_FONTS.get(font_id)


@lru_cache(maxsize=16)
def _face_data_uri(file: str) -> str:
    raw = (FONTS_DIR / file).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")
# === ANCHOR: FONTS_END ===
```

- [ ] **Step 4: 레지스트리 테스트 작성**

`tests/core/reporting_cli/test_fonts.py`:

```python
from vibelign.core.reporting_cli.fonts import FONTS_DIR, REPORT_FONTS, font_def


def test_registry_has_five_fonts():
    assert set(REPORT_FONTS) == {
        "pretendard", "nanum-myeongjo", "gowun-batang", "gowun-dodum", "black-han-sans",
    }


def test_every_registered_face_file_exists_and_is_woff2():
    for fdef in REPORT_FONTS.values():
        for face in fdef.faces:
            path = FONTS_DIR / face.file
            assert path.exists(), f"missing {path}"
            assert path.read_bytes()[:4] == b"wOF2", f"not woff2: {path}"


def test_font_def_unknown_returns_none():
    assert font_def("nope") is None
    assert font_def("pretendard").office_name == "Pretendard"
```

- [ ] **Step 5: 실행해서 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_fonts.py -v`
Expected: 3 PASS. (woff2 파일이 없으면 Step 2 재실행.)

- [ ] **Step 6: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/fonts.py scripts/vendor_report_fonts.py
git add vibelign/core/reporting_cli/fonts.py vibelign/core/reporting_cli/fonts scripts/vendor_report_fonts.py tests/core/reporting_cli/test_fonts.py
git commit -m "feat(report): OFL 한글 폰트 5종 번들 + 레지스트리"
```

---

## Task 2: 폰트 오버라이드 CSS 생성

**Files:**
- Modify: `vibelign/core/reporting_cli/fonts.py` (ANCHOR `FONTS_START`~`FONTS_END` 내부에 추가)
- Test: `tests/core/reporting_cli/test_fonts.py`

**Interfaces:**
- Consumes: `REPORT_FONTS`, `_face_data_uri` (Task 1)
- Produces:
  - `@dataclass(frozen=True, slots=True) class ReportFonts: heading: str | None = None; body: str | None = None` + `has_overrides() -> bool`
  - `def normalize_report_fonts(*, heading: str | None = None, body: str | None = None) -> ReportFonts` (미지 ID → `ValueError`)
  - `def font_family_override_css(fonts: ReportFonts, *, default_heading: str, default_body: str) -> str`

- [ ] **Step 1: 실패 테스트 작성**

`tests/core/reporting_cli/test_fonts.py` 에 추가:

```python
import pytest
from vibelign.core.reporting_cli.fonts import (
    ReportFonts, font_family_override_css, normalize_report_fonts,
)


def test_no_overrides_returns_empty():
    css = font_family_override_css(
        ReportFonts(), default_heading='"X", serif', default_body='"Y", serif'
    )
    assert css == ""


def test_heading_override_embeds_face_and_sets_h1_h2():
    css = font_family_override_css(
        ReportFonts(heading="pretendard"),
        default_heading='"X", serif', default_body='"Y", serif',
    )
    assert "@font-face" in css
    assert "data:font/woff2;base64," in css
    assert '"Pretendard"' in css
    # 제목만 바꿨으면 본문은 default 유지
    assert '"Y"' in css


def test_body_override_only_does_not_change_heading():
    css = font_family_override_css(
        ReportFonts(body="gowun-batang"),
        default_heading='"X", serif', default_body='"Y", serif',
    )
    assert '"Gowun Batang"' in css
    assert '"X"' in css  # 제목은 default 유지


def test_normalize_rejects_unknown_id():
    with pytest.raises(ValueError):
        normalize_report_fonts(heading="nope")


def test_normalize_blank_becomes_none():
    fonts = normalize_report_fonts(heading="", body="pretendard")
    assert fonts.heading is None
    assert fonts.body == "pretendard"
    assert fonts.has_overrides() is True
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/core/reporting_cli/test_fonts.py -k "override or normalize" -v`
Expected: FAIL (`ImportError`/`AttributeError` — 심볼 미정의).

- [ ] **Step 3: 구현 추가**

`fonts.py` 의 `# === ANCHOR: FONTS_END ===` **바로 위**에 삽입:

```python
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
            f"@font-face {{ font-family:{fdef.css_stack.split(',', 1)[0]}; "
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
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_fonts.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/fonts.py
git add vibelign/core/reporting_cli/fonts.py tests/core/reporting_cli/test_fonts.py
git commit -m "feat(report): 폰트 오버라이드 CSS·정규화 추가"
```

---

## Task 3: HTML 렌더러에 폰트 연결

**Files:**
- Modify: `vibelign/core/reporting_cli/html_renderer.py` (ANCHOR `HTML_RENDERER_RENDER_HTML_START`~`_END` 및 상단 import)
- Test: `tests/core/reporting_cli/test_html_renderer.py`

**Interfaces:**
- Consumes: `ReportFonts`, `font_family_override_css` (Task 2); `get_theme(theme).heading_font/.body_font` (기존)
- Produces: `render_html(model, theme="classic", font_sizes=None, fonts: ReportFonts | None = None) -> str`

- [ ] **Step 1: 실패 테스트 작성**

`tests/core/reporting_cli/test_html_renderer.py` 에 추가:

```python
def test_font_family_override_injected_after_theme_css():
    from vibelign.core.reporting_cli.fonts import ReportFonts
    html = render_html(_model(), theme="classic", fonts=ReportFonts(heading="pretendard"))
    assert "@font-face" in html
    assert '"Pretendard"' in html
    assert "h1, h2 { font-family:" in html


def test_no_fonts_keeps_theme_default_unchanged():
    assert render_html(_model(), theme="classic") == render_html(
        _model(), theme="classic", fonts=None
    )
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/core/reporting_cli/test_html_renderer.py -k font_family -v`
Expected: FAIL (`render_html() got unexpected keyword 'fonts'`).

- [ ] **Step 3: 구현**

`html_renderer.py` 상단 import 블록(ANCHOR `HTML_RENDERER_START` 내부)에 추가:

```python
from vibelign.core.reporting_cli.fonts import ReportFonts, font_family_override_css
```

`render_html` 본문을 교체 (ANCHOR `HTML_RENDERER_RENDER_HTML_START`~`_END`):

```python
def render_html(
    model: ReportModel,
    theme: str = "classic",
    font_sizes: ReportFontSizes | None = None,
    fonts: ReportFonts | None = None,
) -> str:
    theme_obj = get_theme(theme)
    css = theme_obj.html_css
    if font_sizes is not None:
        css = "\n".join(part for part in (css, font_size_override_css(font_sizes)) if part)
    if fonts is not None:
        font_css = font_family_override_css(
            fonts,
            default_heading=theme_obj.heading_font,
            default_body=theme_obj.body_font,
        )
        css = "\n".join(part for part in (css, font_css) if part)
    parts = [
        _head(escape(model.title), css),
        f"<h1>{escape(model.title)}</h1>",
        f'<p class="meta">{escape(meta_line(model))}</p>',
    ]
    parts.extend(_render_section(s) for s in model.sections)
    parts.append(_TAIL)
    return "\n".join(parts)
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_html_renderer.py -v`
Expected: 전부 PASS (기존 + 신규).

- [ ] **Step 5: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/html_renderer.py
git add vibelign/core/reporting_cli/html_renderer.py tests/core/reporting_cli/test_html_renderer.py
git commit -m "feat(report): HTML 렌더러에 폰트 오버라이드 연결"
```

---

## Task 4: Word(docx) 렌더러에 폰트 연결 (한글 eastAsia 포함)

**Files:**
- Modify: `vibelign/core/reporting_cli/docx_renderer.py` (ANCHOR `DOCX_RENDERER_RENDER_DOCX_START`~`_END` 및 상단 import)
- Test: `tests/core/reporting_cli/test_docx_renderer.py`

**Interfaces:**
- Consumes: `ReportFonts`, `font_def` (Task 1/2)
- Produces: `render_docx(model, theme="classic", page_numbers=False, font_sizes=None, fonts: ReportFonts | None = None) -> bytes`

- [ ] **Step 1: 실패 테스트 작성**

`tests/core/reporting_cli/test_docx_renderer.py` 에 추가:

```python
@pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx 미설치")
def test_docx_font_family_sets_ascii_and_eastasia():
    from docx.oxml.ns import qn
    from vibelign.core.reporting_cli.fonts import ReportFonts
    data = render_docx(_model(), fonts=ReportFonts(heading="pretendard", body="gowun-batang"))
    from docx import Document
    d = Document(io.BytesIO(data))
    title_run = {p.text: p for p in d.paragraphs if p.text}["예약 앱"].runs[0]
    rfonts = title_run._element.rPr.rFonts
    assert rfonts.get(qn("w:ascii")) == "Pretendard"
    assert rfonts.get(qn("w:eastAsia")) == "Pretendard"
    body_run = {p.text: p for p in d.paragraphs if p.text}["미용실 예약 앱"].runs[0]
    assert body_run._element.rPr.rFonts.get(qn("w:eastAsia")) == "고운바탕"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/core/reporting_cli/test_docx_renderer.py -k font_family -v`
Expected: FAIL (`render_docx() got unexpected keyword 'fonts'`).

- [ ] **Step 3: 구현**

`docx_renderer.py` 상단 import(ANCHOR `DOCX_RENDERER_START` 내부)에 추가:

```python
from vibelign.core.reporting_cli.fonts import ReportFonts, font_def
```

`render_docx` 시그니처에 `fonts` 추가하고, 본문에 폰트 적용 헬퍼와 호출을 넣는다. ANCHOR `DOCX_RENDERER_RENDER_DOCX_START`~`_END` 내부를 다음으로 교체:

```python
def render_docx(
    model: ReportModel,
    theme: str = "classic",
    page_numbers: bool = False,
    font_sizes: ReportFontSizes | None = None,
    fonts: ReportFonts | None = None,
) -> bytes:
    if not DOCX_AVAILABLE:
        raise ReportRendererUnavailable(
            "Word 내보내기에 python-docx 가 필요합니다. (pip install python-docx)"
        )
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    accent = RGBColor.from_string(get_theme(theme).accent.lstrip("#"))
    heading_name = (
        font_def(fonts.heading).office_name if fonts and fonts.heading else None
    )
    body_name = font_def(fonts.body).office_name if fonts and fonts.body else None

    def _accent(heading) -> None:
        for r in heading.runs:
            r.font.color.rgb = accent

    def _size(paragraph, value: int | None) -> None:
        if value is None:
            return
        for run in paragraph.runs:
            run.font.size = Pt(value)

    def _font(paragraph, name: str | None) -> None:
        if name is None:
            return
        for run in paragraph.runs:
            run.font.name = name
            rpr = run._element.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = rpr.makeelement(qn("w:rFonts"), {})
                rpr.insert(0, rfonts)
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rfonts.set(qn(attr), name)

    doc = Document()
    title = doc.add_heading(model.title, level=0)
    _accent(title)
    _size(title, font_sizes.title if font_sizes is not None else None)
    _font(title, heading_name)
    meta_para = doc.add_paragraph(meta_line(model))
    _size(meta_para, (font_sizes.meta or font_sizes.body) if font_sizes is not None else None)
    _font(meta_para, body_name)
    for section in model.sections:
        heading = doc.add_heading(section.heading, level=1)
        _accent(heading)
        _size(heading, font_sizes.heading if font_sizes is not None else None)
        _font(heading, heading_name)
        for block in section.blocks:
            if block.kind == "bullets":
                for item in block.items:
                    p = doc.add_paragraph(item, style="List Bullet")
                    _size(p, font_sizes.body if font_sizes is not None else None)
                    _font(p, body_name)
            elif block.kind == "summary":
                p = doc.add_paragraph()
                run = p.add_run(block.text)
                run.bold = True
                _size(p, font_sizes.body if font_sizes is not None else None)
                _font(p, body_name)
            else:  # paragraph
                p = doc.add_paragraph(block.text)
                _size(p, font_sizes.body if font_sizes is not None else None)
                _font(p, body_name)
    if page_numbers:
        _add_page_number_footer(doc)
    buf = io.BytesIO()
```

> 주의: `_END` 앵커 뒤의 `doc.save(buf)` / `return buf.getvalue()` 는 그대로 둔다.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_docx_renderer.py -v`
Expected: 전부 PASS (기존 폰트크기/accent/페이지번호 테스트 포함).

- [ ] **Step 5: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/docx_renderer.py
git add vibelign/core/reporting_cli/docx_renderer.py tests/core/reporting_cli/test_docx_renderer.py
git commit -m "feat(report): Word 렌더러에 폰트 지정(한글 eastAsia 포함)"
```

---

## Task 5: PPT(pptx) 렌더러에 폰트 연결 (한글 ea 포함)

**Files:**
- Modify: `vibelign/core/reporting_cli/pptx_renderer.py` (ANCHOR `PPTX_RENDERER_RENDER_PPTX_START`~`_END` 및 상단 import)
- Test: `tests/core/reporting_cli/test_pptx_renderer.py`

**Interfaces:**
- Consumes: `ReportFonts`, `font_def`
- Produces: `render_pptx(model, theme="classic", font_sizes=None, fonts: ReportFonts | None = None) -> bytes`

- [ ] **Step 1: 실패 테스트 작성**

`tests/core/reporting_cli/test_pptx_renderer.py` 에 추가(파일 없으면 신규 생성, 아래 헤더 포함):

```python
import io

import pytest

from vibelign.core.reporting_cli.pptx_renderer import render_pptx, PPTX_AVAILABLE
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _model():
    return ReportModel(
        title="예약 앱", report_type="work", date="2026-06-18",
        sections=[Section("개요", [Block(kind="summary", text="미용실 예약 앱")])],
    )


@pytest.mark.skipif(not PPTX_AVAILABLE, reason="python-pptx 미설치")
def test_pptx_font_sets_latin_and_ea():
    from pptx import Presentation
    from pptx.oxml.ns import qn
    from vibelign.core.reporting_cli.fonts import ReportFonts
    data = render_pptx(_model(), fonts=ReportFonts(heading="pretendard"))
    prs = Presentation(io.BytesIO(data))
    title = prs.slides[0].shapes.title
    run = title.text_frame.paragraphs[0].runs[0]
    rpr = run._r.get_or_add_rPr()
    assert rpr.find(qn("a:latin")).get("typeface") == "Pretendard"
    assert rpr.find(qn("a:ea")).get("typeface") == "Pretendard"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/core/reporting_cli/test_pptx_renderer.py -k font -v`
Expected: FAIL (`render_pptx() got unexpected keyword 'fonts'`).

- [ ] **Step 3: 구현**

`pptx_renderer.py` 상단 import(ANCHOR `PPTX_RENDERER_START` 내부)에 추가:

```python
from vibelign.core.reporting_cli.fonts import ReportFonts, font_def
```

ANCHOR `PPTX_RENDERER_RENDER_PPTX_START`~`_END` 내부를 교체:

```python
def render_pptx(
    model: ReportModel,
    theme: str = "classic",
    font_sizes: ReportFontSizes | None = None,
    fonts: ReportFonts | None = None,
) -> bytes:
    if not PPTX_AVAILABLE:
        raise ReportRendererUnavailable(
            "PPT 내보내기에 python-pptx 가 필요합니다. (pip install python-pptx)"
        )
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.oxml.ns import qn
    from pptx.util import Pt

    accent = RGBColor.from_string(get_theme(theme).accent.lstrip("#"))
    heading_name = font_def(fonts.heading).office_name if fonts and fonts.heading else None
    body_name = font_def(fonts.body).office_name if fonts and fonts.body else None

    def _accent_title(shape) -> None:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.font.color.rgb = accent

    def _size_text(shape, value: int | None) -> None:
        if value is None or not shape.has_text_frame:
            return
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.font.size = Pt(value)

    def _font_text(shape, name: str | None) -> None:
        if name is None or not shape.has_text_frame:
            return
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.font.name = name
                rpr = run._r.get_or_add_rPr()
                for tag in ("a:ea", "a:cs"):
                    el = rpr.find(qn(tag))
                    if el is None:
                        el = rpr.makeelement(qn(tag), {})
                        rpr.append(el)
                    el.set("typeface", name)

    prs = Presentation()
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = model.title
    _accent_title(title_slide.shapes.title)
    _size_text(title_slide.shapes.title, font_sizes.title if font_sizes is not None else None)
    _font_text(title_slide.shapes.title, heading_name)
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = meta_line(model)
        _size_text(
            title_slide.placeholders[1],
            (font_sizes.meta or font_sizes.body) if font_sizes is not None else None,
        )
        _font_text(title_slide.placeholders[1], body_name)
    for section in model.sections:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = section.heading
        _accent_title(slide.shapes.title)
        _size_text(slide.shapes.title, font_sizes.heading if font_sizes is not None else None)
        _font_text(slide.shapes.title, heading_name)
        body = _section_text(section)
        if len(slide.placeholders) > 1 and body:
            slide.placeholders[1].text = body
            _size_text(slide.placeholders[1], font_sizes.body if font_sizes is not None else None)
            _font_text(slide.placeholders[1], body_name)
    buf = io.BytesIO()
```

> 주의: `_END` 앵커 뒤 `prs.save(buf)` / `return buf.getvalue()` 는 그대로 둔다. `run.font.name` 설정이 `a:latin` 을 만들어 주므로 `a:ea`/`a:cs` 만 추가 설정하면 된다.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_pptx_renderer.py -v`
Expected: PASS.

- [ ] **Step 5: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/pptx_renderer.py
git add vibelign/core/reporting_cli/pptx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py
git commit -m "feat(report): PPT 렌더러에 폰트 지정(한글 ea 포함)"
```

---

## Task 6: render_job 라우팅에 fonts 전달

**Files:**
- Modify: `vibelign/core/reporting_cli/render_job.py` (ANCHOR `RENDER_JOB_START`~`_END`)
- Test: `tests/core/reporting_cli/test_render_job.py` (없으면 신규)

**Interfaces:**
- Consumes: `ReportFonts`; `render_docx/render_pptx/render_html(..., fonts=)` (Task 3/4/5)
- Produces: `render_and_write(..., fonts: ReportFonts | None = None) -> Path`

- [ ] **Step 1: 실패 테스트 작성**

`tests/core/reporting_cli/test_render_job.py` (신규):

```python
from pathlib import Path

from vibelign.core.reporting_cli.fonts import ReportFonts
from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.render_job import render_and_write


def _model():
    return ReportModel(
        title="t", report_type="work", date="2026-06-18",
        sections=[Section("개요", [Block(kind="summary", text="요약")])],
    )


def test_render_and_write_html_embeds_selected_font(tmp_path: Path):
    dest = render_and_write(
        tmp_path, _model(), "html", slug_source="t", output=None, force=False,
        fonts=ReportFonts(body="pretendard"),
    )
    assert '"Pretendard"' in dest.read_text(encoding="utf-8")
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/core/reporting_cli/test_render_job.py -v`
Expected: FAIL (`render_and_write() got unexpected keyword 'fonts'`).

- [ ] **Step 3: 구현**

`render_job.py` 상단 import(ANCHOR 내부)에 추가:

```python
from vibelign.core.reporting_cli.fonts import ReportFonts
```

`render_and_write` 시그니처에 `fonts: ReportFonts | None = None` 를 `font_sizes` 다음 줄에 추가하고, 세 렌더 호출에 `fonts=fonts` 를 넘긴다:

```python
    fonts: ReportFonts | None = None,
) -> Path:
    """모델을 fmt 로 렌더해 저장하고 경로를 반환한다.
    예외는 호출자가 처리: ReportRendererUnavailable / FileExistsError / ValueError."""
    if fmt == "docx":
        data_bytes = render_docx(
            model, theme=theme, page_numbers=page_numbers, font_sizes=font_sizes, fonts=fonts,
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
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/core/reporting_cli/test_render_job.py -v`
Expected: PASS.

- [ ] **Step 5: 린트 + 커밋**

```bash
uv run ruff check vibelign/core/reporting_cli/render_job.py
git add vibelign/core/reporting_cli/render_job.py tests/core/reporting_cli/test_render_job.py
git commit -m "feat(report): render_job 에 fonts 라우팅"
```

---

## Task 7: CLI 인자 + vib_report_cmd 연결

**Files:**
- Modify: `vibelign/cli/cli_command_groups.py:714-720` (argparse 등록, 기존 폰트크기 인자 뒤)
- Modify: `vibelign/commands/vib_report_cmd.py` (ANCHOR `VIB_REPORT_CMD_REPORTARGS_*`, `VIB_REPORT_CMD_RUN_VIB_REPORT_*`)
- Test: `tests/cli/test_vib_report_cmd.py`

**Interfaces:**
- Consumes: `normalize_report_fonts` (Task 2); `render_and_write(..., fonts=)` (Task 6)
- Produces: CLI 플래그 `--heading-font <id>` / `--body-font <id>`

- [ ] **Step 1: 실패 테스트 작성**

`tests/cli/test_vib_report_cmd.py` 의 패턴을 확인 후, 폰트 인자가 HTML 에 반영되는 테스트를 추가한다(기존 폰트크기 테스트와 동일한 호출 방식 사용). 예:

```python
def test_report_cli_applies_heading_font(tmp_path, capsys, monkeypatch):
    # 기존 테스트의 픽스처/헬퍼로 plan.md 를 만들고 run_vib_report 를 호출한 뒤
    # 생성된 html 에 "@font-face" 와 '"Pretendard"' 가 있는지 검증.
    # args 에 heading_font="pretendard", body_font=None, format="html" 를 포함.
    ...
```

> 실제 호출 형태는 `tests/cli/test_vib_report_cmd.py` 의 기존 `title_font_size` 테스트를 복제해 `heading_font`/`body_font` 속성을 추가하는 방식으로 작성한다(같은 Args 더블 객체 재사용).

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/cli/test_vib_report_cmd.py -k font -v`
Expected: FAIL.

- [ ] **Step 3: argparse 등록**

`vibelign/cli/cli_command_groups.py` 의 718번 줄(`--meta-font-size` 등록) **뒤**에 추가:

```python
    _ = r.add_argument("--heading-font", default=None, metavar="FONT", help="제목 폰트 ID")
    _ = r.add_argument("--body-font", default=None, metavar="FONT", help="본문 폰트 ID")
```

- [ ] **Step 4: ReportArgs + 정규화 + 전달 구현**

`vib_report_cmd.py` 상단 import 에 추가:

```python
from vibelign.core.reporting_cli.fonts import normalize_report_fonts
```

ANCHOR `VIB_REPORT_CMD_REPORTARGS_START`~`_END` 의 `page_numbers: bool` 위에 추가:

```python
    heading_font: str | None
    body_font: str | None
```

`run_vib_report` 의 `font_sizes = normalize_report_font_sizes(...)` 블록 **바로 뒤**(같은 try 내부 권장이나, 별도 try 도 무방)에 추가:

```python
    try:
        report_fonts = normalize_report_fonts(
            heading=getattr(raw, "heading_font", None),
            body=getattr(raw, "body_font", None),
        )
    except ValueError as exc:
        _fail(want_json, str(exc))
        return
```

두 `render_and_write(...)` 호출(reject-blocks 경로 ~line 154, 일반 경로 ~line 187) 각각에 `font_sizes=font_sizes,` 뒤로 `fonts=report_fonts,` 를 추가.

- [ ] **Step 5: 통과 확인**

Run: `uv run pytest tests/cli/test_vib_report_cmd.py -v`
Expected: PASS.

- [ ] **Step 6: 린트 + 커밋**

```bash
uv run ruff check vibelign/cli/cli_command_groups.py vibelign/commands/vib_report_cmd.py
git add vibelign/cli/cli_command_groups.py vibelign/commands/vib_report_cmd.py tests/cli/test_vib_report_cmd.py
git commit -m "feat(report): --heading-font/--body-font CLI 인자"
```

---

## Task 8: PyInstaller 번들에 폰트 포함

**Files:**
- Modify: `vib.spec` (hidden_imports 리스트 ~line 32, datas 블록 line 88-94)

**Interfaces:** 없음(빌드 설정). 번들 sidecar 에서 `FONTS_DIR` 의 woff2 에 접근 가능해야 함.

- [ ] **Step 1: hiddenimports 에 fonts 모듈 추가**

`vib.spec` 의 `"vibelign.core.reporting_cli.themes",` (line 32) 뒤에 추가:

```python
    "vibelign.core.reporting_cli.fonts",
```

- [ ] **Step 2: datas 에 fonts 디렉터리 추가**

`vib.spec` 의 datas 블록(line 94, recovery schema append 뒤)에 추가:

```python
if Path("vibelign/core/reporting_cli/fonts").exists():
    datas.append(("vibelign/core/reporting_cli/fonts", "vibelign/core/reporting_cli/fonts"))
```

- [ ] **Step 3: 정합성 확인 (스모크)**

Run: `uv run python -c "from vibelign.core.reporting_cli.fonts import FONTS_DIR; print(sorted(p.name for p in FONTS_DIR.rglob('*.woff2')))"`
Expected: 8개 woff2 파일명 출력.

- [ ] **Step 4: 커밋**

```bash
git add vib.spec
git commit -m "build(report): PyInstaller 번들에 폰트 자산 포함"
```

> 실제 onedir 빌드 검증은 macOS sidecar 빌드 가이드(메모리: macos_sidecar_build) 절차로 별도 수행. 빌드 후 생성된 PDF 에 한글이 박히는지 육안 확인.

---

## Task 9: TS 폰트 모델

**Files:**
- Create: `vibelign-gui/src/lib/vib/reportFonts.ts`
- Test: `vibelign-gui/src/lib/vib/__tests__/reportFonts.test.ts`

**Interfaces:**
- Produces:
  - `type ReportFonts = { heading?: string; body?: string }`
  - `const REPORT_FONT_OPTIONS: readonly { id: string; label: string }[]` (5개, Python 레지스트리 ID와 일치)
  - `function reportFontArgs(fonts: ReportFonts): readonly string[]`

- [ ] **Step 1: 실패 테스트 작성**

`vibelign-gui/src/lib/vib/__tests__/reportFonts.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { REPORT_FONT_OPTIONS, reportFontArgs } from "../reportFonts";

describe("reportFonts", () => {
  it("exposes the five OFL fonts", () => {
    expect(REPORT_FONT_OPTIONS.map((f) => f.id)).toEqual([
      "pretendard", "nanum-myeongjo", "gowun-batang", "gowun-dodum", "black-han-sans",
    ]);
  });

  it("builds CLI args only for set fonts", () => {
    expect(reportFontArgs({})).toEqual([]);
    expect(reportFontArgs({ heading: "pretendard" })).toEqual(["--heading-font", "pretendard"]);
    expect(reportFontArgs({ heading: "pretendard", body: "gowun-batang" })).toEqual([
      "--heading-font", "pretendard", "--body-font", "gowun-batang",
    ]);
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportFonts.test.ts`
Expected: FAIL (모듈 없음).

- [ ] **Step 3: 구현**

`vibelign-gui/src/lib/vib/reportFonts.ts`:

```typescript
// === ANCHOR: REPORT_FONTS_START ===
export type ReportFontSlot = "heading" | "body";

export type ReportFonts = Partial<Record<ReportFontSlot, string>>;

export type ReportFontOption = { readonly id: string; readonly label: string };

// Python vibelign/core/reporting_cli/fonts.py 의 REPORT_FONTS 와 ID·순서 일치.
export const REPORT_FONT_OPTIONS = [
  { id: "pretendard", label: "Pretendard (고딕)" },
  { id: "nanum-myeongjo", label: "나눔명조" },
  { id: "gowun-batang", label: "고운바탕" },
  { id: "gowun-dodum", label: "고운돋움" },
  { id: "black-han-sans", label: "검은고딕" },
] as const satisfies readonly ReportFontOption[];

const SLOT_FLAGS: readonly { slot: ReportFontSlot; flag: string }[] = [
  { slot: "heading", flag: "--heading-font" },
  { slot: "body", flag: "--body-font" },
];

export function reportFontArgs(fonts: ReportFonts): readonly string[] {
  return SLOT_FLAGS.flatMap(({ slot, flag }) => {
    const id = fonts[slot];
    return id ? [flag, id] : [];
  });
}
// === ANCHOR: REPORT_FONTS_END ===
```

- [ ] **Step 4: 통과 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportFonts.test.ts`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/reportFonts.ts vibelign-gui/src/lib/vib/__tests__/reportFonts.test.ts
git commit -m "feat(report-gui): 폰트 선택 모델(reportFonts)"
```

---

## Task 10: report.ts 생성 함수에 fonts 인자

**Files:**
- Modify: `vibelign-gui/src/lib/vib/report.ts` (ANCHOR `REPORT_GENERATEPLANNINGREPORT_*`, `REPORT_GENERATEREPORTPDF_*`, `REPORT_GENERATEREPORTOFFICE_*`, `REPORT_RENDERREPORTWITHDECISIONS_*`, 상단 import)

**Interfaces:**
- Consumes: `reportFontArgs`, `ReportFonts` (Task 9)
- Produces: 네 함수 각각 마지막 인자로 `fonts: ReportFonts = {}` 추가하고 `...reportFontArgs(fonts)` 를 args 에 삽입

- [ ] **Step 1: import 추가**

`report.ts` 상단(ANCHOR `REPORT_START` 내부)에서 reportFontSizes import 다음 줄에 추가:

```typescript
import { reportFontArgs, type ReportFonts } from "./reportFonts";
```

- [ ] **Step 2: `generatePlanningReport` 수정**

시그니처 마지막에 `fonts: ReportFonts = {},` 추가, args 의 `...reportFontSizeArgs(fontSizes),` 다음 줄에 `...reportFontArgs(fonts),` 추가.

- [ ] **Step 3: `generateReportPdf` 수정**

시그니처 마지막에 `fonts: ReportFonts = {},` 추가, 내부 `generatePlanningReport(...)` 호출의 마지막 인자로 `fonts` 추가.

- [ ] **Step 4: `generateReportOffice` 수정**

시그니처 마지막에 `fonts: ReportFonts = {},` 추가, args 의 `...reportFontSizeArgs(fontSizes),` 다음 줄에 `...reportFontArgs(fonts),` 추가.

- [ ] **Step 5: `renderReportWithDecisions` 수정**

시그니처 마지막에 `fonts: ReportFonts = {},` 추가, args 의 `...reportFontSizeArgs(fontSizes),` 다음 줄에 `...reportFontArgs(fonts),` 추가.

- [ ] **Step 6: 타입체크 + 커밋**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: 에러 없음.
```bash
git add vibelign-gui/src/lib/vib/report.ts
git commit -m "feat(report-gui): report.ts 생성함수에 fonts 인자"
```

---

## Task 11: ReportFontSelect UI + ReportComposer 연결

**Files:**
- Create: `vibelign-gui/src/components/plan-doc/ReportFontSelect.tsx`
- Modify: `vibelign-gui/src/components/plan-doc/ReportComposer.tsx` (ANCHOR `REPORTCOMPOSER_START` import, `_REPORTCOMPOSER_START` 상태, `_OPTIONS_START` UI, `_HANDLEGENERATE_START` 호출, `onReviewRequest` 타입)

**Interfaces:**
- Consumes: `REPORT_FONT_OPTIONS`, `ReportFonts` (Task 9); `generate*`/`onReviewRequest`(Task 10)
- Produces: `ReportFontSelect({ value, onChange })` 컴포넌트

- [ ] **Step 1: ReportFontSelect 컴포넌트 작성**

`vibelign-gui/src/components/plan-doc/ReportFontSelect.tsx`:

```typescript
// === ANCHOR: REPORT_FONT_SELECT_START ===
import type { CSSProperties } from "react";
import { REPORT_FONT_OPTIONS, type ReportFonts } from "../../lib/vib/reportFonts";

export interface ReportFontSelectProps {
  readonly value: ReportFonts;
  readonly onChange: (value: ReportFonts) => void;
}

const SLOTS = [
  { slot: "heading" as const, label: "제목 폰트" },
  { slot: "body" as const, label: "본문 폰트" },
];

export function ReportFontSelect({ value, onChange }: ReportFontSelectProps) {
  return (
    <fieldset style={fieldset}>
      <legend style={legend}>폰트 종류</legend>
      <div style={grid}>
        {SLOTS.map(({ slot, label }) => (
          <label key={slot} style={labelStyle}>
            <span>{label}</span>
            <select
              aria-label={label}
              value={value[slot] ?? ""}
              onChange={(e) => onChange({ ...value, [slot]: e.target.value || undefined })}
              style={select}
            >
              <option value="">테마 기본값</option>
              {REPORT_FONT_OPTIONS.map((f) => (
                <option key={f.id} value={f.id}>{f.label}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

const fieldset: CSSProperties = {
  border: "2px solid #1A1A1A", padding: 10, margin: 0, background: "#FFFFFF",
  boxSizing: "border-box", minInlineSize: 0, width: "100%",
};
const legend: CSSProperties = { padding: "0 6px", fontSize: 12, fontWeight: 800 };
const grid: CSSProperties = {
  display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8,
};
const labelStyle: CSSProperties = { display: "grid", gap: 4, fontSize: 12, fontWeight: 700 };
const select: CSSProperties = {
  width: "100%", minWidth: 0, boxSizing: "border-box",
  border: "2px solid #1A1A1A", padding: "6px 8px", fontSize: 13, fontWeight: 700,
};
// === ANCHOR: REPORT_FONT_SELECT_END ===
```

- [ ] **Step 2: ReportComposer import 추가**

`ReportComposer.tsx` 의 `import { ReportFontSizeControls } ...` 다음에:

```typescript
import { ReportFontSelect } from "./ReportFontSelect";
import type { ReportFonts } from "../../lib/vib/reportFonts";
```

- [ ] **Step 3: onReviewRequest 타입에 fonts 추가**

`onReviewRequest` 시그니처(ANCHOR `REPORTCOMPOSER_START` 내 props)에서 `fontSizes: ReportFontSizes,` 다음에 `fonts: ReportFonts,` 추가.

- [ ] **Step 4: fonts 상태 추가**

`const [fontSizes, setFontSizes] = useState<ReportFontSizes>({});` 다음 줄에:

```typescript
  const [fonts, setFonts] = useState<ReportFonts>({});
```

- [ ] **Step 5: UI 삽입**

ANCHOR `REPORTCOMPOSER_OPTIONS_START` 내부, `<ReportFontSizeControls ... />` 를 감싼 `<div>` 다음에:

```tsx
      <div style={{ marginBottom: 12 }}>
        <ReportFontSelect value={fonts} onChange={setFonts} />
      </div>
```

- [ ] **Step 6: 생성 호출에 fonts 전달**

`handleGenerate` 에서:
- `onReviewRequest(reportType, format, theme, author, pageNumbers, fontSizes);` → 끝에 `fonts` 추가: `onReviewRequest(reportType, format, theme, author, pageNumbers, fontSizes, fonts);`
- `generatePlanningReport(..., pageNumbers, fontSizes)` → `, fonts` 추가
- `generateReportPdf(..., pageNumbers, fontSizes)` → `, fonts` 추가
- `generateReportOffice(..., pageNumbers, fontSizes)` → `, fonts` 추가

- [ ] **Step 7: 타입체크**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: `ReportView.tsx` 의 `onReviewRequest` 콜백 인자 불일치 에러가 나올 수 있음 → Task 12 에서 해결. 그 외 ReportComposer 관련 에러는 없어야 함.

- [ ] **Step 8: 커밋**

```bash
git add vibelign-gui/src/components/plan-doc/ReportFontSelect.tsx vibelign-gui/src/components/plan-doc/ReportComposer.tsx
git commit -m "feat(report-gui): 폰트 선택 UI(ReportFontSelect) 연결"
```

---

## Task 12: ReportView review 경로에 fonts(+fontSizes) 정합화

**Files:**
- Modify: `vibelign-gui/src/pages/ReportView.tsx` (ANCHOR `REPORT_VIEW_START`~`_END`)

**Interfaces:**
- Consumes: `ReportFonts`(Task 9); `renderReportWithDecisions(..., fonts)`(Task 10); `ReportComposer.onReviewRequest(...fonts)`(Task 11)
- 현재 review 경로는 `fontSizes`·`fonts` 를 모두 누락 → 둘 다 전달하도록 수정.

- [ ] **Step 1: import 추가**

`ReportView.tsx` 상단에:

```typescript
import type { ReportFontSizes } from "../lib/vib/reportFontSizes";
import type { ReportFonts } from "../lib/vib/reportFonts";
```

- [ ] **Step 2: review 상태 타입 확장**

`useState<{ payload...; pageNumbers: boolean } | null>` 의 객체 타입에 `fontSizes: ReportFontSizes; fonts: ReportFonts;` 추가.

- [ ] **Step 3: handleReviewRequest 시그니처/저장 확장**

```typescript
  async function handleReviewRequest(
    type: ReportType, format: Fmt, theme: string, author: string,
    pageNumbers: boolean, fontSizes: ReportFontSizes, fonts: ReportFonts,
  ) {
    if (!reportFor) return;
    const plan = reportFor;
    setReviewBusy(true);
    setReviewErr(null);
    reset();
    const r = await emitReportModel(projectDir, plan, type, true, author);
    setReviewBusy(false);
    if (r.ok) setReview({ payload: r.payload, plan, type, format, theme, author, pageNumbers, fontSizes, fonts });
    else setReviewErr(r.error);
  }
```

- [ ] **Step 4: handleReviewConfirm 에서 전달**

```typescript
    const { plan, type, format, payload, theme, author, pageNumbers, fontSizes, fonts } = review;
    ...
    const r = await renderReportWithDecisions(
      projectDir, plan, type, format, rejectBlocks, payload.key,
      theme, author, pageNumbers, fontSizes, fonts,
    );
```

- [ ] **Step 5: ReportComposer onReviewRequest 콜백 갱신**

```tsx
            onReviewRequest={(type, format, theme, author, pageNumbers, fontSizes, fonts) =>
              void handleReviewRequest(type, format, theme, author, pageNumbers, fontSizes, fonts)}
```

- [ ] **Step 6: 타입체크 + 전체 테스트**

Run:
```bash
cd vibelign-gui && npx tsc --noEmit && npm test
```
Expected: 타입 에러 0, 테스트 PASS.

- [ ] **Step 7: 커밋**

```bash
git add vibelign-gui/src/pages/ReportView.tsx
git commit -m "fix(report-gui): 다듬기 경로에 fonts·fontSizes 정합화"
```

---

## Task 13: 전체 검증

**Files:** 없음(검증 전용).

- [ ] **Step 1: Python 전체 테스트 + 린트**

Run:
```bash
uv run pytest tests/core/reporting_cli tests/cli/test_vib_report_cmd.py -q
uv run ruff check vibelign/
```
Expected: 전부 PASS, 린트 클린.

- [ ] **Step 2: TS 테스트 + 타입체크 + 린트**

Run:
```bash
cd vibelign-gui && npm test && npx tsc --noEmit && npm run lint
```
Expected: 전부 PASS.

- [ ] **Step 3: 수동 스모크(HTML 경로, 빌드 불필요)**

Run (실제 기획안 .md 경로로):
```bash
uv run vib report <plan.md> --type doc --format html --theme classic --heading-font black-han-sans --body-font gowun-batang --json
```
생성된 html 을 열어 `@font-face` 임베딩과 제목=검은고딕·본문=고운바탕 렌더 확인.

- [ ] **Step 4: 수동 스모크(Word/PPT)**

Run:
```bash
uv run vib report <plan.md> --type doc --format docx --heading-font pretendard --body-font nanum-myeongjo --json
uv run vib report <plan.md> --type doc --format pptx --heading-font pretendard --body-font nanum-myeongjo --json
```
Word/PPT 를 열어 폰트 이름 적용 확인(해당 폰트 설치 시 표시, 미설치 시 폴백 — 합의된 한계).

- [ ] **Step 5: GUI 육안 검증 (PDF 인앱 미리보기)**

`npm run tauri dev` 로 보고서 작성 탭 → 폰트 드롭다운 선택 → PDF 생성 → 인앱 미리보기에서 한글이 선택 폰트로 임베딩되어 보이는지 확인. (메모리: pdf_inapp_preview_pdfjs_assets / macos_sidecar_build 참고)

---

## 자체 검토 결과 (writing-plans self-review)

- **스펙 커버리지:** 동작모델(Task 3·11), 5종 번들(Task 1), @font-face PDF 임베딩(Task 2·3), Word/PPT 이름지정+한글 ea(Task 4·5), 배관(Task 6·7·9·10·11·12), PyInstaller datas(Task 8), 테마 기본값 회귀(Task 2·3 테스트). 모두 매핑됨.
- **플레이스홀더:** Task 7 Step 1 의 CLI 테스트는 기존 `test_vib_report_cmd.py` 패턴 복제를 지시(파일 미열람) — 실행자가 기존 픽스처를 보고 작성. 그 외 코드 스텝은 완성 코드 제공.
- **타입 일관성:** `ReportFonts`(TS heading/body), Python `ReportFonts`(heading/body 모두 font id), `office_name`/`css_stack`/`faces` 명칭이 Task 1→2→4→5 에서 일관. CLI 플래그 `--heading-font`/`--body-font` 가 Python(Task 7)·TS(Task 9) 동일.
- **ID 일치:** 5종 ID `pretendard / nanum-myeongjo / gowun-batang / gowun-dodum / black-han-sans` 가 Python 레지스트리·TS 옵션·테스트 전반에서 동일.
