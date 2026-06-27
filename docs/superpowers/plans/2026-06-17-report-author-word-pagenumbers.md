# Plan 1 — 작성자 이름 + Word 페이지 번호 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** 보고서에 작성자 이름(전 포맷 메타)과 Word 바닥글 페이지 번호(N/M, 토글)를 추가한다. 의존성 0.

**Architecture:** `ReportModel.author` 필드 + 공용 메타 헬퍼(`{label} · {date}[ · 작성자: {author}]`)를 html/docx/pptx 가 공유. `render_docx(..., page_numbers=True)` 가 바닥글에 `PAGE/NUMPAGES` 필드 삽입. `--author`/`--page-numbers` 가 CLI→render_and_write→렌더러로, GUI 래퍼·모달까지 흐른다.

**Tech Stack:** Python/pytest/ruff, React/TS/Vitest.

**구조화:** 최소 패치·앵커·단일책임. 신규 파일 없음(전부 기존 확장).

---

## Task 1: ReportModel.author + 직렬화

**Files:** Modify `reporting_cli/models.py`, `reporting_cli/model_json.py`; Test `tests/core/reporting_cli/test_model_json.py`

- [ ] **Step 1: 실패 테스트**
```python
# test_model_json.py 에 추가
def test_author_roundtrips():
    from vibelign.core.reporting_cli.models import ReportModel
    from vibelign.core.reporting_cli.model_json import model_from_dict, model_to_dict
    m = ReportModel(title="t", report_type="work", date="d", author="홍길동", sections=[])
    assert model_from_dict(model_to_dict(m)).author == "홍길동"
```
- [ ] **Step 2: 실패 확인** — `pytest tests/core/reporting_cli/test_model_json.py -k author -q` → FAIL (author 미보존/필드 없음)
- [ ] **Step 3: 구현**
  - `models.py` `ReportModel` 에 `author: str = ""` 추가(sections 위, source_plan_path 뒤).
  - `model_json.model_to_dict`: dict 에 `"author": model.author` 추가.
  - `model_json.model_from_dict`: `ReportModel(..., author=data.get("author", ""), ...)`.
- [ ] **Step 4: 통과** — `pytest tests/core/reporting_cli/test_model_json.py -q` → PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): ReportModel.author 필드 + 직렬화"`

## Task 2: 메타 헬퍼 + build_report_model(author) + 3 렌더러

**Files:** Modify `templates.py`, `html_renderer.py`, `docx_renderer.py`, `pptx_renderer.py`; Test `test_html_renderer.py`, `test_docx_renderer.py`

- [ ] **Step 1: 실패 테스트**
```python
# test_html_renderer.py 에 추가 (이미 render_html, models, _model() 있음)
def test_author_shown_in_meta_when_present():
    m = _model()
    from dataclasses import replace
    html = render_html(replace(m, author="홍길동"))
    assert "작성자: 홍길동" in html

def test_author_absent_keeps_meta_plain():
    assert "작성자:" not in render_html(_model())
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현**
  - `templates.py` 에 헬퍼 추가:
    ```python
    def meta_line(model) -> str:
        label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
        base = f"{label} · {model.date}"
        return f"{base} · 작성자: {model.author}" if getattr(model, "author", "") else base
    ```
  - `build_report_model(data, report_type, *, date, source_plan_path="", author="")` — 시그니처에 author 추가, `ReportModel(..., author=author, ...)`.
  - html_renderer: `f'<p class="meta">{escape(label)} · {escape(model.date)}</p>'` → `f'<p class="meta">{escape(meta_line(model))}</p>'`(import meta_line; label 변수 불필요시 정리).
  - docx_renderer: `doc.add_paragraph(f"{label} · {model.date}")` → `doc.add_paragraph(meta_line(model))`.
  - pptx_renderer: 부제 `f"{label} · {model.date}"` → `meta_line(model)`.
- [ ] **Step 4: 통과** — `pytest tests/core/reporting_cli -q` PASS(회귀 포함)
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): 메타 줄에 작성자 표시(전 포맷)"`

## Task 3: Word 페이지 번호 바닥글

**Files:** Modify `docx_renderer.py`; Test `test_docx_renderer.py`

- [ ] **Step 1: 실패 테스트**
```python
# test_docx_renderer.py 에 추가
def test_docx_page_numbers_adds_page_field():
    import io as _io, docx as _docx
    from vibelign.core.reporting_cli.docx_renderer import render_docx as _r
    from vibelign.core.reporting_cli.models import Block, ReportModel, Section
    m = ReportModel(title="t", report_type="work", date="d",
                    sections=[Section("개요", [Block(kind="summary", text="x")])])
    data = _r(m, page_numbers=True)
    xml = _docx.Document(_io.BytesIO(data)).sections[0].footer._element.xml
    assert "PAGE" in xml  # PAGE 필드 instrText

def test_docx_no_page_numbers_no_footer_field():
    import io as _io, docx as _docx
    from vibelign.core.reporting_cli.docx_renderer import render_docx as _r
    from vibelign.core.reporting_cli.models import Block, ReportModel, Section
    m = ReportModel(title="t", report_type="work", date="d",
                    sections=[Section("개요", [Block(kind="summary", text="x")])])
    data = _r(m, page_numbers=False)
    xml = _docx.Document(_io.BytesIO(data)).sections[0].footer._element.xml
    assert "PAGE" not in xml
```
- [ ] **Step 2: 실패 확인** — FAIL(page_numbers 미지원)
- [ ] **Step 3: 구현** — `render_docx(model, theme="classic", page_numbers=False)`. 바닥글 헬퍼 추가(파일 내):
```python
def _add_page_number_footer(document) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    para = document.sections[0].footer.paragraphs[0]
    para.alignment = 1  # center
    def field(instr: str):
        for kind, val in (("begin", None), ("instrText", instr), ("end", None)):
            el = OxmlElement(f"w:{ 'instrText' if kind=='instrText' else 'fldChar' }")
            if kind == "instrText":
                el.set(qn("xml:space"), "preserve"); el.text = instr
            else:
                el.set(qn("w:fldCharType"), kind)
            r = OxmlElement("w:r"); r.append(el); para._p.append(r)
    field(" PAGE ")
    run = para.add_run(" / "); _ = run
    field(" NUMPAGES ")
```
  `render_docx` 끝(`doc.save` 전)에 `if page_numbers: _add_page_number_footer(doc)`.
- [ ] **Step 4: 통과** — `pytest tests/core/reporting_cli/test_docx_renderer.py -q` PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): Word 바닥글 페이지 번호(PAGE/NUMPAGES, 토글)"`

## Task 4: render_job + CLI 가 author/page_numbers 전달

**Files:** Modify `render_job.py`, `vib_report_cmd.py`, `cli_command_groups.py`, `templates.py`(이미 author); Test `tests/cli/test_vib_report_cmd.py`

- [ ] **Step 1: 실패 테스트**
```python
# test_vib_report_cmd.py 에 추가 (_args 는 getattr 친화 Namespace)
def test_author_threads_to_html(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"; plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, author="홍길동"))
    out = json.loads(capsys.readouterr().out)
    assert "작성자: 홍길동" in Path(out["path"]).read_text(encoding="utf-8")
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현**
  - `vib_report_cmd`: `build_report_model(data, raw.type, date=report_date, source_plan_path=str(plan_path), author=getattr(raw,"author","") or "")`. emit/render-decisions 도 동일하게 author 전달(emit_report_payload·merge 경로). render_job 호출에 `page_numbers=getattr(raw,"page_numbers",True)` 추가.
  - `render_job.render_and_write(..., theme="classic", page_numbers=True)` → `render_docx(model, theme=theme, page_numbers=page_numbers)`(html/pptx 는 무시).
  - `emit.emit_report_payload(..., author="")` → `build_report_model(..., author=author)`(payload base/polished 에 author 포함). 시그니처에 author 추가, vib_report_cmd emit 분기가 전달.
  - `ReportArgs`: `author: str`, `page_numbers: bool`.
  - `cli_command_groups`: `--author`(default ""), `--page-numbers`(BooleanOptionalAction, default True): `r.add_argument("--page-numbers", action=argparse.BooleanOptionalAction, default=True, help="페이지 번호(Word, 기본 ON)")`, `r.add_argument("--author", default="", help="작성자 이름")`.
- [ ] **Step 4: 통과** — `pytest tests/cli/test_vib_report_cmd.py tests/core/reporting_cli -q` PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(report): --author/--page-numbers CLI→렌더러 전달"`

## Task 5: GUI 래퍼 author/pageNumbers

**Files:** Modify `lib/vib/report.ts`; Test `__tests__/report.test.ts`

- [ ] **Step 1: 실패 테스트**
```ts
test("generatePlanningReport author/pageNumbers → 인자", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html", report_type: "work" }), stderr: "", exit_code: 0 });
  mockLoadDoc.mockResolvedValue({ path: "x", content: "<i></i>" } as never);
  await generatePlanningReport("/proj", "plans/p.md", "work", false, "classic", "홍길동", false);
  const a = mockRunVib.mock.calls[0][0];
  expect(a).toEqual(expect.arrayContaining(["--author", "홍길동", "--no-page-numbers"]));
});
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현** — `generatePlanningReport/Pdf/Office`, `emitReportModel`, `renderReportWithDecisions` 시그니처 끝에 `author = "", pageNumbers = true` 추가. args 에 `"--author", author`(항상) + `pageNumbers ? [] : ["--no-page-numbers"]` 삽입. emit 도 author 전달(payload 정합). (renderReportWithDecisions 는 author+pageNumbers 둘 다.)
- [ ] **Step 4: 통과** — `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/report.test.ts` PASS(기존 exact-match 테스트의 인자 배열도 `--author ""` 포함되게 갱신)
- [ ] **Step 5: 커밋** — `git commit -m "feat(gui-report): 래퍼에 author/pageNumbers 인자"`

## Task 6: 모달 작성자 입력 + 페이지번호 체크박스 + ReportView

**Files:** Modify `ExportReportModal.tsx`, `ReportView.tsx`; Test `__tests__/ExportReportModal.test.tsx`

- [ ] **Step 1: 실패 테스트**
```tsx
test("작성자 입력/페이지번호 → generatePlanningReport 인자", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.change(screen.getByLabelText("작성자"), { target: { value: "홍길동" } });
  fireEvent.click(screen.getByLabelText(/페이지 번호/));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "홍길동", false));
});
```
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현**
  - 모달: `const [author,setAuthor]=useState(()=>{try{return localStorage.getItem("vibelign_report_author")||""}catch{return ""}})`, `const [pageNumbers,setPageNumbers]=useState(true)`.
  - UI: 작성자 텍스트 input(`aria-label="작성자"`, onChange setAuthor + localStorage try/catch), 페이지번호 체크박스(label "페이지 번호 (Word·PDF)", checked pageNumbers).
  - handleGenerate 호출들에 `author, pageNumbers` 전달. `onReviewRequest?.(reportType, format, theme, author, pageNumbers)` 로 확장(시그니처).
  - 기존 모달 테스트의 generate 단언들에 `, "classic"` 다음 `, "", true`(기본 author/pageNumbers) 추가 갱신.
  - ReportView: `onReviewRequest` 타입에 author/pageNumbers, review 상태에 보관, `renderReportWithDecisions(..., theme, author, pageNumbers)` 전달.
- [ ] **Step 4: 통과 + tsc** — `npx vitest run src/components/plan-doc src/components/report-review && npx tsc --noEmit` PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(gui-report): 모달 작성자 입력 + 페이지번호 체크박스 + 리뷰 전달"`

## 완료 기준
- `pytest tests/core/reporting_cli tests/cli/test_vib_report_cmd.py` 통과.
- `cd vibelign-gui && npx vitest run && npx tsc --noEmit && npx eslint src` 무오류(기존 flaky 제외).
- author 있을 때 전 포맷 메타에 "작성자: …", Word page_numbers ON 시 바닥글 N/M. 기본(author "", page on) 동작 자연스러움.
