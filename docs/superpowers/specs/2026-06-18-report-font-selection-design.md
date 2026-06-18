# 보고서 폰트 선택 기능 — 설계 문서

- 날짜: 2026-06-18
- 브랜치: `feat/report-export-integrate`
- 상태: 승인됨 (사용자 승인 2026-06-18)

## 1. 목표

보고서 작성 기능에서 사용자가 **제목용 / 본문용 폰트를 독립적으로 선택**할 수 있게 한다.
satgat(github.com/unclejobs-ai/satgat)이 제공하는 한글 무료 폰트와 동일하게, **전부 OFL(SIL Open Font License)** 폰트만 사용하여 상업적 사용·임베딩·재배포가 무료로 허용되도록 한다.

적용 범위: **PDF(인앱 미리보기 포함) + Word(docx) + PPT(pptx) 전부.**

## 2. 동작 모델 — 테마 위의 오버라이드

- 현재 폰트는 테마(`theme_catalog.py`)에 `heading_font`/`body_font`로 고정되어 있고 사용자가 못 바꾼다.
- 폰트 선택은 **테마 CSS 위에 덧씌우는 오버라이드 레이어**로 구현한다. 이는 폰트 크기(`font_sizes`)가 이미 동작하는 방식과 **1:1 동일한 패턴**이다.
- 각 드롭다운의 기본값 = **"테마 기본값"**.
  - 사용자가 고르지 않으면 → 오버라이드 없음 → 기존 75개 테마의 폰트가 그대로 유지된다(비파괴적).
  - 사용자가 고르면 → 해당 폰트로 덮어쓴다.
- 제목 폰트와 본문 폰트는 **독립 선택**한다.

## 3. 번들 폰트 (경량 5종, 전부 OFL)

| ID | 표시명 | 분류 | 굵기 |
|---|---|---|---|
| `pretendard` | Pretendard | 고딕(가변) | 가변(전 굵기) |
| `nanum-myeongjo` | 나눔명조 | 명조 | Regular/Bold |
| `gowun-batang` | 고운바탕 | 명조 | Regular/Bold |
| `gowun-dodum` | 고운돋움 | 고딕 | Regular(단일) |
| `black-han-sans` | 검은고딕 | 강조 고딕 | Regular(단일) |

- 무거운 Noto Serif KR은 용량 절감을 위해 제외(명조는 나눔명조·고운바탕으로 충분).
- 예상 번들 증가량: **약 8–12MB** (woff2, Regular/Bold 위주).
- woff2 파일은 **Python 패키지** `vibelign/core/reporting_cli/fonts/` 에 둔다.
  - 렌더 주체가 `vib report`(Python)이므로 폰트 파일에 Python이 직접 접근해야 HTML 임베딩이 가능하다.
- 각 폰트 디렉터리에 OFL 라이선스 파일(`OFL.txt`)을 동봉한다.

## 4. PDF / 인앱 미리보기 — @font-face base64 임베딩

- PDF는 네이티브 웹뷰(macOS `WKWebView.createPDF`, Windows `WebView2.PrintToPdf`)로 렌더된다.
- Python이 HTML 생성 시 **선택된 폰트만** woff2를 base64 data-URI로 `@font-face`에 임베딩하고, 테마 CSS **뒤에** `font-family` 오버라이드 CSS를 추가한다.
  - data-URI 방식은 파일 경로/CORS 문제가 없어 오프스크린 웹뷰에서 가장 안정적이다.
  - 선택된 1~2종만 임베딩하므로 HTML 크기 증가는 렌더당 수 MB로 제한된다.
- 웹뷰가 이 HTML을 렌더 → PDF에 폰트가 **임베딩**된다(오프라인·미설치 환경에서도 정상).
- 인앱 미리보기(pdf.js)는 PDF에 임베딩된 폰트를 그대로 표시 → **추가 작업 없음**.

## 5. Word / PPT

- `python-docx` / `python-pptx`에서 제목/본문 run에 `run.font.name = <패밀리명>`을 지정한다.
- **한계(합의됨):** Office 문서에는 폰트 **이름만** 기록된다(파일 임베딩 아님). 수신자 PC에 해당 폰트가 없으면 폴백된다. 진짜 폰트 임베딩은 별개의 큰 작업으로 이번 범위에서 제외한다.

## 6. 배관 (폰트 크기 경로와 1:1 대응)

```
[신규] ReportFontSelect.tsx (드롭다운 2개: 제목, 본문)
  → ReportComposer.tsx 옵션 패널에 fonts 상태 추가 + onReviewRequest/generate*에 전달
  → [신규] reportFonts.ts (모델 + reportFontArgs(): --heading-font / --body-font)
  → report.ts 의 generatePlanningReport/generateReportPdf/generateReportOffice 에 인자 추가
  → vib_report_cmd.py ReportArgs 확장(heading_font, body_font) + 검증(알려진 ID만)
  → [신규] fonts.py (폰트 레지스트리 + font_family_override_css())
  → html_renderer.py(오버라이드 CSS append) / docx_renderer.py / pptx_renderer.py (font.name)
  → render_job.py 가 fonts 인자를 각 렌더러로 라우팅
```

### 기존 파일 변경 지점 (앵커 경계 준수)
- `vibelign-gui/src/components/plan-doc/ReportComposer.tsx` — fonts 상태/전달
- `vibelign-gui/src/lib/vib/report.ts` — 3개 generate 함수에 fonts 인자
- `vibelign-gui/src/pages/ReportView.tsx` — onReviewRequest 시그니처에 fonts 추가(현재 fontSizes도 누락 상태이므로 함께 정합화 검토)
- `vibelign/commands/vib_report_cmd.py` — ReportArgs + 파싱
- `vibelign/core/reporting_cli/html_renderer.py` — 오버라이드 CSS append
- `vibelign/core/reporting_cli/docx_renderer.py` — run.font.name
- `vibelign/core/reporting_cli/pptx_renderer.py` — run.font.name
- `vibelign/core/reporting_cli/render_job.py` — fonts 라우팅

### 신규 파일
- `vibelign-gui/src/components/plan-doc/ReportFontSelect.tsx`
- `vibelign-gui/src/lib/vib/reportFonts.ts`
- `vibelign/core/reporting_cli/fonts.py`
- `vibelign/core/reporting_cli/fonts/<font>/*.woff2` + `OFL.txt`

## 7. 추가 작업 / 리스크

- **PyInstaller `vib.spec`**: fonts 디렉터리를 `datas`로 추가해야 번들 sidecar에서 폰트 파일에 접근할 수 있다(기존 hidden_imports 함정과 동일 계열).
- **폰트 굵기**: Pretendard(가변)·나눔명조·고운바탕은 Bold 보유. 고운돋움·검은고딕은 단일 굵기 → 제목에 쓰일 때 합성 볼드로 폴백.
- **폰트 패밀리명 일치**: HTML `font-family`에 쓰는 이름과 Word/PPT `run.font.name`에 쓰는 이름이 폰트 파일의 실제 패밀리명과 정확히 일치해야 한다. 레지스트리(`fonts.py`)를 단일 진실원천으로 삼는다.

## 8. 테스트

- TS: `reportFonts.ts`의 인자 변환(reportFontArgs) 단위 테스트.
- Python:
  - `vib_report_cmd` 가 `--heading-font`/`--body-font` 를 파싱하고 미지의 ID를 거부.
  - HTML 출력에 `@font-face` + `font-family` 오버라이드가 포함됨.
  - docx/pptx 출력 run에 `font.name`이 설정됨.
  - "테마 기본값"(미지정) 시 오버라이드가 추가되지 않아 기존 테마 동작이 유지됨(회귀).

## 9. 범위 밖 (YAGNI)

- Word/PPT의 실제 폰트 파일 임베딩.
- 사용자 임의 폰트 업로드.
- 4분할(제목/머리말/소제목/본문) 단위의 폰트 지정 — 제목/본문 2분할로 충분.
- Noto Serif KR 등 추가 폰트 — 추후 레지스트리에 항목만 추가하면 확장 가능.
