# 보고서 작성자 이름 + 자동 페이지 번호 — 설계 스펙

- 날짜: 2026-06-17
- 대상: VibeLign 보고서 (`reporting_cli`, `vib report`, GUI `ExportReportModal`/`ReportView`, PDF 흐름)
- 산출물: 이 설계 1개 → 구현 계획서 2개 (Plan 1: 작성자+Word, Plan 2: PDF 스탬프)

## 1. 배경과 목표

보고서 메타 줄은 현재 `"{label} · {date}"` 뿐이고 작성자·페이지 번호가 없다. 사무직 보고서에 흔히 필요한 두 가지를 추가한다.

### 목표
1. **작성자 이름**: 전 포맷(HTML/PDF/Word/PPT) 메타에 표시. 선택 입력.
2. **자동 페이지 번호**: Word 는 바닥글 `PAGE/NUMPAGES` 필드, PDF 는 후처리 스탬프("N / M"). 토글(기본 ON). HTML=N/A, PPT=범위 밖.

### 비목표 (YAGNI)
- PPT 슬라이드 번호, HTML 화면 페이지네이션, 표지 페이지, 머리글.
- 작성자 다중·서명·직함(이름 1줄만).

## 2. 작성자 이름

### 모델
- `ReportModel` 에 `author: str = ""` 추가(`models.py`). `build_report_model(data, report_type, *, date, source_plan_path="", author="")`.
- 직렬화 `model_json` 에 author 포함(round-trip). polish 캐시 key 에는 불포함(메타라 다듬기 무관) — author 만 달라도 재-polish 안 함.

### 렌더
- 메타 문자열 헬퍼: `author` 비면 `"{label} · {date}"`, 있으면 `"{label} · {date} · 작성자: {author}"`.
- html/docx/pptx 세 렌더러가 같은 규칙으로 메타 작성.

### 계약·GUI
- `--author <name>` CLI 인자(기본 ""). `ReportArgs.author`. emit·render-decisions·일반 경로 모두 `build_report_model(..., author=...)`.
- GUI: 모달 작성자 텍스트 입력(선택), `localStorage("vibelign_report_author")`. 래퍼(`generatePlanningReport/Pdf/Office`, `emitReportModel`, `renderReportWithDecisions`)에 `author` 파라미터. emit/render 가 같은 author 를 받아 캐시된 polished 와 정합.

## 3. 페이지 번호

### 토글
- 모달 "페이지 번호" 체크박스(기본 ON). `--page-numbers`/`--no-page-numbers`(기본 on). `ReportArgs.page_numbers: bool`.
- docx·pdf 에만 의미. html/pptx 무시.

### Word(.docx)
- 바닥글에 `PAGE` / `NUMPAGES` 필드를 삽입해 "N / M" 중앙 표시. python-docx 는 필드 API 가 없어 footer 단락에 `w:fldSimple`(or fldChar run) XML 을 직접 추가하는 헬퍼 `add_page_number_footer(document)` 로 캡슐화.
- `render_docx(model, theme, page_numbers=True)`: page_numbers 면 바닥글 추가.

### PDF (후처리 스탬프)
- `export_report_pdf`(Rust, html→pdf) 는 변경 없음. 그 다음 단계로 스탬프.
- 신규 Python CLI: `vib report-stamp-pdf <pdf> --json` → `pypdf` 로 페이지 수, `reportlab` 로 각 페이지 하단 중앙에 "N / M" 오버레이 생성 후 `pypdf` 로 병합, in-place 교체. `{ok, path, pages}` 반환.
- 신규 코어: `reporting_cli/pdf_stamp.py` — `stamp_page_numbers(pdf_path) -> int(pages)` 순수 I/O 함수(테스트 가능). CLI 는 얇은 래퍼.
- GUI 흐름(PDF):
  - 일반: `generatePlanningReport(html)` → `export_report_pdf`(Rust) → page_numbers 면 `stampPdfPageNumbers(pdfPath)`(신규 래퍼 = `vib report-stamp-pdf`) → 최종 경로.
  - 리뷰: `renderReportWithDecisions(...,"pdf")` → html → `export_report_pdf` → 스탬프. (ReportView confirm)
- **의존성**: `pypdf`, `reportlab` 를 report extras(pyproject) 에 추가. PyInstaller `vib.spec` hidden_imports 에 `report_stamp`/`pypdf`/`reportlab` 보강(lazy_command 번들 주의 — `[[memory:project_pyinstaller_lazy_command_hidden_imports]]`).

## 4. 에러 처리
- author "" → 메타 변화 없음(현재와 동일).
- page_numbers off → footer/stamp 없음.
- PDF 스탬프 실패(라이브러리/손상 PDF) → **원본 PDF 유지 + 경고**(페이지 번호만 누락, 보고서는 살림). GUI 는 stamp 실패해도 export 성공 경로로 진행.
- 스탬프 텍스트는 숫자·슬래시뿐 → reportlab 기본 폰트로 충분(한글 폰트 이슈 없음).

## 5. 테스트
- 모델/직렬화: author round-trip. 메타 헬퍼: 빈/채움 두 케이스.
- 렌더: html/docx/pptx 메타에 "작성자: …" 포함(있을 때)·미포함(없을 때).
- docx footer: page_numbers=True → footer 에 PAGE 필드(XML `w:instrText`/`fldSimple`) 존재; False → 없음.
- pdf_stamp: 2페이지 PDF 생성→스탬프→pypdf 텍스트 추출에 "1 / 2","2 / 2"; 손상 PDF→예외 graceful.
- CLI: `--author`/`--page-numbers` 스레딩, `report-stamp-pdf` JSON 계약.
- GUI: 래퍼 인자(author/page_numbers/theme 공존), 모달 입력·체크박스, PDF 흐름이 스탬프 호출.

## 6. 구조화·범위 (계획 2분할)
- **Plan 1 (작성자 + Word 페이지번호)** — 의존성 0. 모델 author, 메타 헬퍼, 3 렌더러, docx footer, CLI `--author`/`--page-numbers`(docx 적용), GUI 입력·체크박스·래퍼. 안전하게 먼저 머지.
- **Plan 2 (PDF 스탬프)** — `pypdf`+`reportlab` 의존성, `pdf_stamp.py` + `report-stamp-pdf` CLI + `vib.spec` + GUI PDF 흐름 스탬프 단계. Plan 1 위에 얹음.

신규 파일: `reporting_cli/pdf_stamp.py`(Plan 2). docx footer 헬퍼는 `docx_renderer.py` 안. 메타 헬퍼는 `templates.py` 또는 작은 `meta.py`.

## 7. 영향 파일
| 파일 | 변경 | Plan |
|---|---|---|
| `reporting_cli/models.py` | `ReportModel.author` | 1 |
| `reporting_cli/model_json.py` | author 직렬화 | 1 |
| `reporting_cli/templates.py` | `build_report_model(author=)` + 메타 헬퍼 | 1 |
| `reporting_cli/html_renderer.py` | 메타에 author | 1 |
| `reporting_cli/docx_renderer.py` | 메타 author + page_numbers footer | 1 |
| `reporting_cli/pptx_renderer.py` | 부제 author | 1 |
| `reporting_cli/render_job.py` | page_numbers 전달 | 1 |
| `commands/vib_report_cmd.py` | `--author`/`--page-numbers` + ReportArgs | 1 |
| `cli/cli_command_groups.py` | 인자 등록 (+ report-stamp-pdf 서브커맨드) | 1/2 |
| GUI `report.ts` | author/pageNumbers 래퍼 + stampPdf | 1/2 |
| GUI `ExportReportModal.tsx` | 작성자 입력 + 페이지번호 체크박스 | 1 |
| GUI `ReportView.tsx` | author/page_numbers 리뷰 전달 + PDF 스탬프 | 1/2 |
| `reporting_cli/pdf_stamp.py`(신규) | 스탬프 코어 | 2 |
| `commands/vib_report_stamp_cmd.py`(신규) | CLI | 2 |
| `pyproject.toml` / `vib.spec` | pypdf/reportlab dep + hidden_imports | 2 |
