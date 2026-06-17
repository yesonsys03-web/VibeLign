# Plan 2 — PDF 페이지 번호 후처리 스탬프 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** `export_report_pdf`(Rust, html→pdf) 가 만든 PDF 에 페이지 번호("N / M")를 후처리로 찍는다. WKWebView/WebView2 print 가 CSS 페이지 카운터를 무시하므로 pypdf+reportlab 오버레이로 해결.

**Architecture:** 순수 코어 `pdf_stamp.stamp_page_numbers(pdf_path) -> pages`(reportlab 오버레이 → pypdf merge → in-place 교체). 얇은 CLI `vib report-stamp-pdf <pdf> --json`. GUI 는 PDF 생성 후 `page_numbers` 면 이 CLI 를 호출. 실패해도 원본 PDF 유지(graceful).

**의존성:** `pypdf`, `reportlab`(report extras). **Plan 1 선행**(page_numbers 토글·author 가 이미 흐름).

**Tech Stack:** Python/pytest, React/TS/Vitest, PyInstaller spec.

---

## Task 1: 의존성 설치 (개발 환경)

- [ ] **Step 1: report extras 에 추가** — `pyproject.toml` 의 report extra(현재 docx/pptx/lxml/PIL 있는 곳)에 `pypdf>=4`, `reportlab>=4` 추가.
- [ ] **Step 2: venv 설치** — `.venv/bin/pip install pypdf reportlab`
- [ ] **Step 3: import 확인** — `.venv/bin/python -c "import pypdf, reportlab; print('ok')"` → `ok`
- [ ] **Step 4: 커밋** — `git add pyproject.toml && git commit -m "build(report): PDF 스탬프용 pypdf/reportlab 의존성 추가"`

## Task 2: `pdf_stamp.py` 코어

**Files:** Create `reporting_cli/pdf_stamp.py`; Test `tests/core/reporting_cli/test_pdf_stamp.py`

- [ ] **Step 1: 실패 테스트**
```python
# tests/core/reporting_cli/test_pdf_stamp.py
from __future__ import annotations
from pathlib import Path


def _two_page_pdf(p: Path) -> None:
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(p))
    c.drawString(72, 720, "page one"); c.showPage()
    c.drawString(72, 720, "page two"); c.showPage()
    c.save()


def test_stamp_adds_n_of_m(tmp_path: Path):
    from pypdf import PdfReader
    from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers
    pdf = tmp_path / "r.pdf"; _two_page_pdf(pdf)
    pages = stamp_page_numbers(pdf)
    assert pages == 2
    text = "".join(pg.extract_text() or "" for pg in PdfReader(str(pdf)).pages)
    assert "1 / 2" in text and "2 / 2" in text


def test_stamp_bad_pdf_raises(tmp_path: Path):
    from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers
    bad = tmp_path / "bad.pdf"; bad.write_bytes(b"not a pdf")
    import pytest
    with pytest.raises(Exception):
        stamp_page_numbers(bad)
```
- [ ] **Step 2: 실패 확인** — `pytest tests/core/reporting_cli/test_pdf_stamp.py -q` → FAIL(모듈 없음)
- [ ] **Step 3: 구현(앵커 스텁 ≤30줄 → Edit)**
스텁:
```python
# === ANCHOR: PDF_STAMP_START ===
from __future__ import annotations

import io
from pathlib import Path
# === ANCHOR: PDF_STAMP_END ===
```
Edit 로 본문 추가(앵커 END 위):
```python
def stamp_page_numbers(pdf_path: Path) -> int:
    """PDF 각 페이지 하단 중앙에 'N / M' 을 찍고 in-place 교체한다. 페이지 수 반환."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        w = float(page.mediabox.width) or A4[0]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, float(page.mediabox.height) or A4[1]))
        c.setFont("Helvetica", 9)
        c.drawCentredString(w / 2, 24, f"{i} / {total}")
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
```
- [ ] **Step 4: 통과** — PASS(2 / 2 텍스트, bad→예외)
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): PDF 페이지 번호 스탬프 코어(pypdf+reportlab)"`

## Task 3: `report-stamp-pdf` CLI

**Files:** Create `commands/vib_report_stamp_cmd.py`; Modify `cli/cli_command_groups.py`; Test `tests/cli/test_vib_report_stamp_cmd.py`

- [ ] **Step 1: 실패 테스트**
```python
# tests/cli/test_vib_report_stamp_cmd.py
import json
from argparse import Namespace
from pathlib import Path


def _two_page_pdf(p):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(p)); c.drawString(72,720,"a"); c.showPage(); c.drawString(72,720,"b"); c.showPage(); c.save()


def test_stamp_cmd_json(tmp_path, capsys):
    from vibelign.commands.vib_report_stamp_cmd import run_vib_report_stamp
    pdf = tmp_path / "r.pdf"; _two_page_pdf(pdf)
    run_vib_report_stamp(Namespace(pdf=str(pdf), json=True))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["pages"] == 2 and out["path"] == str(pdf)


def test_stamp_cmd_missing_file(tmp_path, capsys):
    import pytest
    from vibelign.commands.vib_report_stamp_cmd import run_vib_report_stamp
    with pytest.raises(SystemExit):
        run_vib_report_stamp(Namespace(pdf=str(tmp_path / "nope.pdf"), json=True))
    assert json.loads(capsys.readouterr().out)["ok"] is False
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현(앵커 스텁→Edit, 신규 production 소스)**
```python
# vibelign/commands/vib_report_stamp_cmd.py
# === ANCHOR: VIB_REPORT_STAMP_CMD_START ===
from __future__ import annotations

import json
import sys
from pathlib import Path
# === ANCHOR: VIB_REPORT_STAMP_CMD_END ===
```
Edit 로 추가:
```python
def run_vib_report_stamp(args) -> None:
    pdf = Path(getattr(args, "pdf", "")).expanduser()
    want_json = bool(getattr(args, "json", False))
    if not pdf.exists():
        msg = f"PDF 를 찾을 수 없어요: {pdf}"
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False) if want_json else msg,
              file=sys.stderr if not want_json else sys.stdout)
        raise SystemExit(1)
    try:
        from vibelign.core.reporting_cli.pdf_stamp import stamp_page_numbers
        pages = stamp_page_numbers(pdf)
    except Exception as exc:  # graceful: 호출자가 원본 PDF 유지
        print(json.dumps({"ok": False, "error": f"페이지 번호 스탬프 실패: {exc}"}, ensure_ascii=False))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "path": str(pdf), "pages": pages}, ensure_ascii=False))
```
  - `cli_command_groups`: report 서브파서 근처에 `report-stamp-pdf` 등록:
    ```python
    sp = sub.add_parser("report-stamp-pdf", help="PDF 에 페이지 번호 스탬프")
    sp.add_argument("pdf", help="대상 PDF 경로")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=lazy_command("vibelign.commands.vib_report_stamp_cmd", "run_vib_report_stamp"))
    ```
    (실제 sub 변수명·패턴은 기존 report 등록부와 동일하게 맞춘다.)
- [ ] **Step 4: 통과** — `pytest tests/cli/test_vib_report_stamp_cmd.py -q` PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): vib report-stamp-pdf CLI"`

## Task 4: PyInstaller 번들 hidden_imports

**Files:** Modify `vib.spec`

- [ ] **Step 1** — `vib.spec` hidden_imports 에 `vibelign.commands.vib_report_stamp_cmd`, `vibelign.core.reporting_cli.pdf_stamp`, `pypdf`, `reportlab`, `reportlab.pdfgen.canvas` 추가(`[[memory:project_pyinstaller_lazy_command_hidden_imports]]` 패턴: lazy_command 모듈은 명시 필요).
- [ ] **Step 2: 커밋** — `git commit -m "build(report): 번들에 pdf_stamp/pypdf/reportlab hidden_imports"`

## Task 5: GUI 스탬프 래퍼 + PDF 흐름

**Files:** Modify `lib/vib/report.ts`, `pages/ReportView.tsx`; Test `__tests__/report.test.ts`

- [ ] **Step 1: 실패 테스트**
```ts
test("stampPdfPageNumbers → report-stamp-pdf 호출", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.pdf", pages: 2 }), stderr: "", exit_code: 0 });
  const ok = await stampPdfPageNumbers("/proj", "/p/r.pdf");
  expect(ok).toBe(true);
  expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["report-stamp-pdf", "/p/r.pdf"]));
});
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현**
  - `report.ts`: 
    ```ts
    export async function stampPdfPageNumbers(cwd: string, pdfPath: string): Promise<boolean> {
      const res = await runVib(["report-stamp-pdf", pdfPath, "--json"], cwd);
      try { return JSON.parse(res.stdout.trim()).ok === true; } catch { return false; }
    }
    ```
  - `generateReportPdf`: `export_report_pdf` 성공 후 `if (pageNumbers) await stampPdfPageNumbers(cwd, saved)`(실패해도 saved 반환 — graceful). `generateReportPdf` 시그니처에 이미 pageNumbers(Plan1) 있으면 사용; 없으면 추가.
  - `ReportView.handleReviewConfirm`: PDF 분기에서 `export_report_pdf` 후 `if (review.pageNumbers) await stampPdfPageNumbers(projectDir, finalPath)`.
- [ ] **Step 4: 통과 + tsc** — `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/report.test.ts && npx tsc --noEmit` PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(gui-report): PDF 생성 후 페이지번호 스탬프 호출"`

## Task 6: 실제 E2E
- [ ] **Step 1** — 임시 기획안 → `vib report ... --format html` → (수동 또는 스킵: Rust export_report_pdf 는 헤드리스 불가) → 대신 `report-stamp-pdf` 를 reportlab 로 만든 2페이지 PDF 에 직접 실행해 "1 / 2","2 / 2" 확인(Task 2/3 테스트로 커버). GUI 실제 PDF 스탬프는 앱 수동 확인 항목으로 기록.

## 완료 기준
- `pytest tests/core/reporting_cli/test_pdf_stamp.py tests/cli/test_vib_report_stamp_cmd.py` 통과.
- `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/report.test.ts && npx tsc --noEmit` 무오류.
- reportlab 2페이지 PDF 에 스탬프 시 "N / M" 텍스트 확인. 스탬프 실패해도 원본 PDF 살아있음.
