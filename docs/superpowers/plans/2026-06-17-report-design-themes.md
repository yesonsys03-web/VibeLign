# Plan — 보고서 디자인 테마 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보고서 종류(업무/제안/결과)와 직교한 '디자인 테마' 축을 추가한다 — HTML/PDF 는 테마별 손 작성 CSS, Word/PPT 는 테마 팔레트(색·폰트). 초기 5종(classic/minimal/executive/compact/pastel).

**Architecture:** 신규 `themes.py` 레지스트리(`Theme` dataclass + `THEMES` + `get_theme`). 렌더러는 `theme` 인자(기본 `"classic"`)를 받아 HTML 은 `theme.html_css` 주입, docx/pptx 는 팔레트 적용. `--theme` 가 CLI→`render_and_write`→렌더러, 그리고 GUI 래퍼·모달 드롭다운까지 흐른다. emit 은 무관(렌더 안 함), render-decisions 는 `--theme` 받음.

**Tech Stack:** Python 3 / pytest / ruff, React + TS + Vitest.

**구조화 규율:** 최소 패치·앵커 준수·단일책임. 신규 production 소스(`themes.py`)는 앵커 스텁→Edit 로 precheck(30줄/앵커) 통과. 렌더러는 시그니처만 확장(내부 불변).

---

## File Structure
- Create: `vibelign/core/reporting_cli/themes.py` — `Theme`/`THEMES`/`THEME_IDS`/`get_theme` + 5 CSS
- Modify: `html_renderer.py`(CSS 주입), `docx_renderer.py`/`pptx_renderer.py`(팔레트), `render_job.py`(theme 전달), `commands/vib_report_cmd.py`(--theme), `cli/cli_command_groups.py`(인자)
- Modify(GUI): `lib/vib/report.ts`(theme 파라미터), `components/plan-doc/ExportReportModal.tsx`(드롭다운), `pages/ReportView.tsx`(theme 전달)

---

## Task 1: `themes.py` 레지스트리 + 5 테마

**Files:**
- Create: `vibelign/core/reporting_cli/themes.py`
- Test: `tests/core/reporting_cli/test_themes.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_themes.py
from __future__ import annotations

from vibelign.core.reporting_cli.themes import THEME_IDS, get_theme


def test_five_themes_registered():
    assert THEME_IDS == ("classic", "minimal", "executive", "compact", "pastel")


def test_each_theme_has_nonempty_fields():
    for tid in THEME_IDS:
        t = get_theme(tid)
        assert t.id == tid
        assert t.label and t.html_css and t.accent and t.heading_font and t.body_font


def test_unknown_theme_falls_back_to_classic():
    assert get_theme("nope").id == "classic"
    assert get_theme("").id == "classic"


def test_classic_css_matches_current_design():
    # 회귀: classic 은 현재 디자인(레드 액센트) 유지.
    assert get_theme("classic").accent == "#9B1B1B"
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_themes.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 앵커 스텁 작성(≤30줄)**

```python
# vibelign/core/reporting_cli/themes.py
# === ANCHOR: THEMES_START ===
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    html_css: str
    accent: str
    ink: str
    paper: str
    heading_font: str
    body_font: str


THEME_IDS: tuple[str, ...] = ("classic", "minimal", "executive", "compact", "pastel")
# === ANCHOR: THEMES_END ===
```

- [ ] **Step 4: Edit 로 THEMES + get_theme 추가 (앵커 END 위에 삽입)**

각 테마의 `html_css` 는 `<style>` 안에 들어갈 본문(중괄호는 일반 문자열이라 이스케이프 불필요 — html_renderer 가 `.format` 대신 직접 치환). 5개를 다음 팔레트·레이아웃으로 작성:

```python
_CLASSIC_CSS = """
  :root { --ink:#1A1A1A; --paper:#F7F7F2; --accent:#9B1B1B; }
  * { box-sizing:border-box; }
  body { font-family:"Noto Serif KR","Apple SD Gothic Neo",serif; color:var(--ink); background:var(--paper);
         max-width:760px; margin:0 auto; padding:48px 40px; line-height:1.7; }
  h1 { font-size:26px; border-bottom:3px solid var(--accent); padding-bottom:10px; }
  h2 { font-size:17px; color:var(--accent); margin-top:28px; }
  p.meta { color:#666; font-size:13px; margin-top:4px; }
  p.summary { font-weight:700; font-size:16px; }
  ul { padding-left:20px; } li { margin:4px 0; }
  @media print { body { background:#fff; max-width:none; padding:0; } h2 { break-after:avoid; } section { break-inside:avoid; } }
"""

_MINIMAL_CSS = """
  :root { --ink:#222; --paper:#fff; --accent:#444; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif; color:var(--ink); background:var(--paper);
         max-width:720px; margin:0 auto; padding:64px 48px; line-height:1.8; letter-spacing:-0.01em; }
  h1 { font-size:28px; font-weight:800; }
  h2 { font-size:14px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:.08em; margin-top:36px; }
  p.meta { color:#999; font-size:12px; margin-top:6px; }
  p.summary { font-weight:600; font-size:16px; color:#000; }
  ul { padding-left:18px; } li { margin:6px 0; }
  section { border-top:1px solid #eee; padding-top:8px; }
  @media print { body { padding:0; max-width:none; } }
"""

_EXECUTIVE_CSS = """
  :root { --ink:#1c2430; --paper:#fff; --accent:#1B3A6B; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",sans-serif; color:var(--ink); background:var(--paper);
         max-width:800px; margin:0 auto; padding:0 0 48px; line-height:1.7; }
  h1 { font-size:30px; font-weight:900; color:#fff; background:var(--accent); margin:0; padding:36px 40px; }
  p.meta { color:#fff; background:var(--accent); margin:0; padding:0 40px 24px; font-size:13px; opacity:.85; }
  section, h2 ~ * { padding-left:40px; padding-right:40px; }
  h2 { font-size:18px; color:var(--accent); border-left:5px solid var(--accent); padding:2px 0 2px 12px; margin:30px 40px 8px; }
  p.summary { font-weight:700; font-size:17px; background:#f0f4fa; padding:14px 16px; border-radius:6px; }
  ul { padding-left:20px; } li { margin:5px 0; }
  @media print { body { padding:0; } }
"""

_COMPACT_CSS = """
  :root { --ink:#222; --paper:#fff; --accent:#2f6f46; }
  * { box-sizing:border-box; }
  body { font-family:"Apple SD Gothic Neo","Pretendard",sans-serif; color:var(--ink); background:var(--paper);
         max-width:680px; margin:0 auto; padding:28px 28px; line-height:1.45; font-size:13px; }
  h1 { font-size:20px; border-bottom:2px solid var(--accent); padding-bottom:6px; margin:0 0 4px; }
  h2 { font-size:13px; color:var(--accent); margin:16px 0 4px; font-weight:800; }
  p.meta { color:#777; font-size:11px; margin:0 0 8px; }
  p.summary { font-weight:700; }
  p { margin:4px 0; } ul { padding-left:16px; margin:4px 0; } li { margin:1px 0; }
  @media print { body { padding:0; } }
"""

_PASTEL_CSS = """
  :root { --ink:#4a3f35; --paper:#FBF6EE; --accent:#C97B5A; }
  * { box-sizing:border-box; }
  body { font-family:"Pretendard","Apple SD Gothic Neo",sans-serif; color:var(--ink); background:var(--paper);
         max-width:740px; margin:0 auto; padding:48px 40px; line-height:1.8; }
  h1 { font-size:26px; color:var(--accent); }
  h2 { font-size:16px; color:var(--accent); margin-top:28px; }
  p.meta { color:#a08e7d; font-size:13px; margin-top:4px; }
  p.summary { font-weight:700; background:#fff3e9; padding:12px 14px; border-radius:12px; }
  section { background:#fff; border-radius:14px; padding:6px 18px 12px; margin:14px 0; box-shadow:0 1px 4px rgba(0,0,0,.04); }
  ul { padding-left:20px; } li { margin:4px 0; }
  @media print { body { background:#fff; } section { box-shadow:none; } }
"""

THEMES: dict[str, Theme] = {
    "classic": Theme("classic", "클래식", _CLASSIC_CSS, "#9B1B1B", "#1A1A1A", "#F7F7F2",
                     '"Noto Serif KR", serif', '"Noto Serif KR", serif'),
    "minimal": Theme("minimal", "모던 미니멀", _MINIMAL_CSS, "#444444", "#222222", "#FFFFFF",
                     '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    "executive": Theme("executive", "임원 보고형", _EXECUTIVE_CSS, "#1B3A6B", "#1C2430", "#FFFFFF",
                       '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
    "compact": Theme("compact", "컴팩트", _COMPACT_CSS, "#2F6F46", "#222222", "#FFFFFF",
                     '"Apple SD Gothic Neo", sans-serif', '"Apple SD Gothic Neo", sans-serif'),
    "pastel": Theme("pastel", "부드러운 파스텔", _PASTEL_CSS, "#C97B5A", "#4A3F35", "#FBF6EE",
                    '"Pretendard", sans-serif', '"Pretendard", sans-serif'),
}


def get_theme(theme_id: str) -> Theme:
    """테마 조회. 모르는/빈 id 는 classic 으로 폴백한다(렌더가 안 깨지게)."""
    return THEMES.get(theme_id) or THEMES["classic"]
```

- [ ] **Step 5: 통과 확인 + ruff**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_themes.py -q && .venv/bin/ruff check vibelign/core/reporting_cli/themes.py`
Expected: PASS (4) + ruff clean

- [ ] **Step 6: 커밋**

```bash
git add vibelign/core/reporting_cli/themes.py tests/core/reporting_cli/test_themes.py
git commit -m "feat(report): 디자인 테마 레지스트리 + 5종(classic/minimal/executive/compact/pastel)"
```

---

## Task 2: html_renderer 가 테마 CSS 주입

**Files:**
- Modify: `vibelign/core/reporting_cli/html_renderer.py`
- Test: `tests/core/reporting_cli/test_html_renderer.py` (추가)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_html_renderer.py 에 추가
from vibelign.core.reporting_cli.html_renderer import render_html
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _m():
    return ReportModel(title="t", report_type="work", date="d",
                       sections=[Section("개요", [Block(kind="summary", text="요약")])])


def test_theme_minimal_injects_its_css():
    html = render_html(_m(), theme="minimal")
    assert "Pretendard" in html and "text-transform:uppercase" in html


def test_unknown_theme_falls_back_to_classic():
    assert render_html(_m(), theme="nope") == render_html(_m(), theme="classic")


def test_default_theme_is_classic_unchanged():
    html = render_html(_m())
    assert "#9B1B1B" in html  # classic accent
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_html_renderer.py -k theme -q`
Expected: FAIL — `render_html() got an unexpected keyword argument 'theme'`

- [ ] **Step 3: `_HEAD` 를 CSS 주입형으로, `render_html` 에 theme 추가**

`html_renderer.py` 상단의 `_HEAD` 상수를 다음 함수로 교체(중괄호 충돌 회피 위해 `.format` 대신 직접 결합):

```python
from vibelign.core.reporting_cli.themes import get_theme

_HEAD_OPEN = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<title>'
_HEAD_MID = "</title>\n<style>"
_HEAD_CLOSE = "\n</style>\n</head>\n<body>"


def _head(title: str, css: str) -> str:
    return f"{_HEAD_OPEN}{title}{_HEAD_MID}{css}{_HEAD_CLOSE}"
```

`render_html` 시그니처·본문 교체:

```python
def render_html(model: ReportModel, theme: str = "classic") -> str:
    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    css = get_theme(theme).html_css
    parts = [
        _head(escape(model.title), css),
        f"<h1>{escape(model.title)}</h1>",
        f'<p class="meta">{escape(label)} · {escape(model.date)}</p>',
    ]
    parts.extend(_render_section(s) for s in model.sections)
    parts.append(_TAIL)
    return "\n".join(parts)
```

`_TAIL`, `_render_block`, `_render_section` 은 그대로.

- [ ] **Step 4: 통과 확인 + 기존 html 테스트 회귀**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_html_renderer.py -q`
Expected: PASS (신규 3 + 기존 — 기존이 특정 CSS 문자열을 검사하면 classic 에 그대로 있어 통과; 깨지면 그 검사값이 classic css 에 있는지 확인)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/html_renderer.py tests/core/reporting_cli/test_html_renderer.py
git commit -m "feat(report): html 렌더러가 테마별 CSS 주입(기본 classic 불변)"
```

---

## Task 3: docx/pptx 렌더러가 팔레트 적용

**Files:**
- Modify: `vibelign/core/reporting_cli/docx_renderer.py`, `pptx_renderer.py`
- Test: `tests/core/reporting_cli/test_docx_renderer.py`, `test_pptx_renderer.py` (추가)

- [ ] **Step 1: 실패 테스트 작성 (docx)**

```python
# tests/core/reporting_cli/test_docx_renderer.py 에 추가
import io
import docx
from vibelign.core.reporting_cli.docx_renderer import render_docx
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def test_docx_theme_applies_accent_to_heading():
    m = ReportModel(title="t", report_type="work", date="d",
                    sections=[Section("개요", [Block(kind="summary", text="요약")])])
    data = render_docx(m, theme="executive")  # accent #1B3A6B
    d = docx.Document(io.BytesIO(data))
    # 제목 또는 머리글 run 중 하나에 executive accent 색이 적용됐는지
    colors = []
    for p in d.paragraphs:
        for r in p.runs:
            if r.font.color and r.font.color.rgb is not None:
                colors.append(str(r.font.color.rgb))
    assert "1B3A6B" in colors
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_docx_renderer.py -k theme -q`
Expected: FAIL — unexpected keyword 'theme' (또는 색 미적용)

- [ ] **Step 3: docx_renderer 에 theme 적용**

`render_docx(model)` → `render_docx(model, theme="classic")`. 상단에 `from vibelign.core.reporting_cli.themes import get_theme` 와 `from docx.shared import RGBColor` 추가. 제목/머리글 추가부에서 색·폰트 지정:

```python
def render_docx(model: ReportModel, theme: str = "classic") -> bytes:
    if not DOCX_AVAILABLE:
        raise ReportRendererUnavailable("python-docx 가 설치되어 있지 않습니다")
    th = get_theme(theme)
    accent = RGBColor.from_string(th.accent.lstrip("#"))
    document = docx.Document()
    title = document.add_heading(model.title, level=0)
    for r in title.runs:
        r.font.color.rgb = accent
    label = REPORT_TYPE_LABELS.get(model.report_type, model.report_type)
    document.add_paragraph(f"{label} · {model.date}")
    for section in model.sections:
        h = document.add_heading(section.heading, level=1)
        for r in h.runs:
            r.font.color.rgb = accent
        for block in section.blocks:
            # (기존 블록 렌더 로직 유지: bullets/summary/paragraph)
            ...
    buf = io.BytesIO(); document.save(buf); return buf.getvalue()
```

> 기존 블록 렌더 본문은 그대로 두고, 위처럼 제목/머리글 run 색만 accent 로 설정한다(폰트명은 선택적으로 `r.font.name = th.heading_font` 가능하나 한글 폰트 미설치 환경 고려해 색 우선).

- [ ] **Step 4: pptx 동일 패턴 + 테스트**

`render_pptx(model)` → `render_pptx(model, theme="classic")`. 제목 텍스트 프레임 run 색을 accent 로:

```python
# pptx_renderer.py
from pptx.dml.color import RGBColor  # 이미 있으면 재사용
from vibelign.core.reporting_cli.themes import get_theme
# render_pptx 안: th = get_theme(theme); accent = RGBColor.from_string(th.accent.lstrip("#"))
# 제목 슬라이드 title.text_frame.paragraphs[0].runs[0].font.color.rgb = accent (run 없으면 생성)
```

테스트(`test_pptx_renderer.py`):
```python
def test_pptx_theme_renders_without_error():
    from vibelign.core.reporting_cli.pptx_renderer import render_pptx
    from vibelign.core.reporting_cli.models import Block, ReportModel, Section
    m = ReportModel(title="t", report_type="work", date="d",
                    sections=[Section("개요", [Block(kind="bullets", items=["a"])])])
    data = render_pptx(m, theme="pastel")
    assert data[:2] == b"PK"  # 유효한 pptx(zip)
```

- [ ] **Step 5: 통과 + 기존 회귀**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_docx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py -q`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add vibelign/core/reporting_cli/docx_renderer.py vibelign/core/reporting_cli/pptx_renderer.py tests/core/reporting_cli/test_docx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py
git commit -m "feat(report): docx/pptx 렌더러가 테마 팔레트(accent) 적용"
```

---

## Task 4: render_job + CLI 가 theme 전달

**Files:**
- Modify: `render_job.py`, `commands/vib_report_cmd.py`, `cli/cli_command_groups.py`
- Test: `tests/cli/test_vib_report_cmd.py` (추가)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/cli/test_vib_report_cmd.py 에 추가 (_args 는 getattr 친화적 Namespace)
def test_theme_threads_to_html(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"; plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, theme="minimal"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert "text-transform:uppercase" in Path(out["path"]).read_text(encoding="utf-8")
```

> `_args` 기본 dict 에 `theme="classic"` 추가.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/cli/test_vib_report_cmd.py -k theme_threads -q`
Expected: FAIL — minimal CSS 없음(theme 미전달)

- [ ] **Step 3: `render_and_write` 에 theme 추가**

`render_job.py` 의 `render_and_write` 시그니처에 `theme: str = "classic"` 추가, 각 렌더 호출에 전달:

```python
def render_and_write(root, model, fmt, *, slug_source, output, force, theme="classic"):
    if fmt == "docx":
        data_bytes = render_docx(model, theme=theme)
        return write_report_bytes(root, model, data_bytes, slug_source=slug_source, ext=".docx", output=output, force=force)
    if fmt == "pptx":
        data_bytes = render_pptx(model, theme=theme)
        return write_report_bytes(root, model, data_bytes, slug_source=slug_source, ext=".pptx", output=output, force=force)
    html = render_html(model, theme=theme)
    return write_report(root, model, html, slug_source=slug_source, output=output, force=force)
```

- [ ] **Step 4: `vib_report_cmd.py` — ReportArgs + 두 렌더 경로에 theme 전달**

`ReportArgs` Protocol 에 `theme: str` 추가. 일반 렌더 경로와 render-decisions 경로의 `render_and_write(...)` 호출에 `theme=getattr(raw, "theme", "classic") or "classic"` 추가:

```python
        dest = render_and_write(
            root, model, fmt, slug_source=slug_source, output=raw.output, force=raw.force,
            theme=getattr(raw, "theme", "classic") or "classic",
        )
```
(두 군데 모두 — 일반 경로 약 라인 139, render-decisions 경로의 render_and_write 호출.)

- [ ] **Step 5: `cli_command_groups.py` — `--theme` 인자**

`--polish-key` 인자 옆에 추가:
```python
    _ = r.add_argument("--theme", default="classic",
                       choices=["classic", "minimal", "executive", "compact", "pastel"],
                       help="디자인 테마 (기본 classic)")
```

- [ ] **Step 6: 통과 + 전체 cmd 회귀**

Run: `.venv/bin/python -m pytest tests/cli/test_vib_report_cmd.py tests/core/reporting_cli -q`
Expected: PASS (신규 + 기존 전부)

- [ ] **Step 7: 커밋**

```bash
git add vibelign/core/reporting_cli/render_job.py vibelign/commands/vib_report_cmd.py vibelign/cli/cli_command_groups.py tests/cli/test_vib_report_cmd.py
git commit -m "feat(report): --theme 가 CLI→render_and_write→렌더러로 전달"
```

---

## Task 5: GUI 래퍼에 theme 파라미터

**Files:**
- Modify: `vibelign-gui/src/lib/vib/report.ts`
- Test: `vibelign-gui/src/lib/vib/__tests__/report.test.ts` (추가)

- [ ] **Step 1: 실패 테스트 작성**

```ts
test("generatePlanningReport theme → --theme 인자", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html", report_type: "work" }), stderr: "", exit_code: 0 });
  mockLoadDoc.mockResolvedValue({ path: "x", content: "<i></i>" } as never);
  await generatePlanningReport("/proj", "plans/p.md", "work", false, "minimal");
  expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--theme", "minimal"]));
});

test("renderReportWithDecisions theme → --theme 인자", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html" }), stderr: "", exit_code: 0 });
  await renderReportWithDecisions("/proj", "plans/p.md", "work", "html", [[0, 1]], "k1", "executive");
  expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--theme", "executive"]));
});
```

- [ ] **Step 2: 실패 확인**

Run(`cd vibelign-gui`): `npx vitest run src/lib/vib/__tests__/report.test.ts`
Expected: FAIL — theme 인자 없음

- [ ] **Step 3: report.ts 래퍼에 theme 추가 (기본 "classic")**

`generatePlanningReport/generateReportPdf/generateReportOffice/emitReportModel/renderReportWithDecisions` 시그니처 끝에 `theme: string = "classic"` 추가하고 args 에 `"--theme", theme` 를 넣는다. 예:

```ts
export async function generatePlanningReport(cwd, planPath, reportType, polish = false, theme = "classic") {
  const res = await runVib(["report", planPath, "--type", reportType, "--format", "html", "--theme", theme, "--json",
    ...(polish ? ["--polish"] : [])], cwd);
  // …이하 동일
}

export async function renderReportWithDecisions(cwd, planPath, reportType, format, reject, polishKey, theme = "classic") {
  const fmt = format === "pdf" ? "html" : format;
  const args = ["report", planPath, "--type", reportType, "--format", fmt,
    "--reject-blocks", JSON.stringify(reject), "--polish-key", polishKey, "--theme", theme, "--json"];
  // …이하 동일
}
```
(emit 은 렌더 안 하므로 theme 불필요 — 단, generateReportPdf/Office 도 동일하게 `--theme` 추가.)

- [ ] **Step 4: 통과 + report 테스트 회귀**

Run(`cd vibelign-gui`): `npx vitest run src/lib/vib/__tests__/report.test.ts`
Expected: PASS (신규 2 + 기존)

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/report.ts vibelign-gui/src/lib/vib/__tests__/report.test.ts
git commit -m "feat(gui-report): vib 래퍼에 theme 파라미터(--theme)"
```

---

## Task 6: 모달 테마 드롭다운 + ReportView 전달

**Files:**
- Modify: `vibelign-gui/src/components/plan-doc/ExportReportModal.tsx`, `vibelign-gui/src/pages/ReportView.tsx`
- Test: `vibelign-gui/src/components/plan-doc/__tests__/ExportReportModal.test.tsx` (추가)

- [ ] **Step 1: 실패 테스트 작성 (테마 선택이 generate 호출 인자에 반영)**

```tsx
test("테마 선택 → generatePlanningReport 에 theme 전달", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.change(screen.getByLabelText("디자인 테마"), { target: { value: "minimal" } });
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "minimal"));
});
```

> `mockGen` 은 기존 ExportReportModal 테스트의 `generatePlanningReport` 목. 기존 호출 단언들(예: `toHaveBeenCalledWith("/proj","plans/p.md","work",false)`)은 새 5번째 인자 `"classic"` 가 붙으므로 **함께 갱신**해야 한다.

- [ ] **Step 2: 실패 확인**

Run(`cd vibelign-gui`): `npx vitest run src/components/plan-doc/__tests__/ExportReportModal.test.tsx`
Expected: FAIL — 드롭다운 없음 / theme 인자 누락

- [ ] **Step 3: 모달에 테마 state + 드롭다운**

```tsx
const THEMES = [
  { id: "classic", label: "클래식" }, { id: "minimal", label: "모던 미니멀" },
  { id: "executive", label: "임원 보고형" }, { id: "compact", label: "컴팩트" },
  { id: "pastel", label: "부드러운 파스텔" },
];
const [theme, setTheme] = useState<string>(() => localStorage.getItem("vibelign_report_theme") || "classic");
```
드롭다운(포맷 라디오 아래):
```tsx
<div style={{ marginBottom: 12 }}>
  <label>디자인 테마{" "}
    <select aria-label="디자인 테마" value={theme}
      onChange={(e) => { setTheme(e.target.value); localStorage.setItem("vibelign_report_theme", e.target.value); }}>
      {THEMES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
    </select>
  </label>
</div>
```
`handleGenerate` 의 호출에 theme 전달: `generatePlanningReport(cwd, planPath, reportType, polish, theme)`, `generateReportPdf(cwd, planPath, reportType, polish, theme)`, `generateReportOffice(cwd, planPath, reportType, format, polish, theme)`. 그리고 `onReviewRequest?.(reportType, format, theme)` 로 확장(시그니처에 theme 추가).

- [ ] **Step 4: ReportView — onReviewRequest/render 에 theme 전달**

`onReviewRequest` 타입을 `(type, format, theme) => void` 로, `handleReviewRequest(type, format, theme)` 가 review 상태에 theme 보관, `handleReviewConfirm` 의 `renderReportWithDecisions(projectDir, plan, type, format, rejectBlocks, payload.key, theme)` 에 전달:

```tsx
// review 상태에 theme 추가
const [review, setReview] = useState<{ payload: EmitPayload; plan: string; type: ReportType; format: Fmt; theme: string } | null>(null);
// handleReviewRequest(type, format, theme): setReview({..., theme})  (emit 은 theme 무관)
// handleReviewConfirm: renderReportWithDecisions(projectDir, plan, type, format, rejectBlocks, payload.key, review.theme)
// 모달: onReviewRequest={(type, format, theme) => void handleReviewRequest(type, format, theme)}
```

- [ ] **Step 5: 통과 + tsc + 전체 GUI 보고서 테스트**

Run(`cd vibelign-gui`):
```bash
npx vitest run src/components/plan-doc src/components/report-review src/lib/vib/__tests__/report.test.ts && npx tsc --noEmit
```
Expected: PASS, tsc 0

- [ ] **Step 6: 커밋**

```bash
git add vibelign-gui/src/components/plan-doc/ExportReportModal.tsx vibelign-gui/src/pages/ReportView.tsx vibelign-gui/src/components/plan-doc/__tests__/ExportReportModal.test.tsx
git commit -m "feat(gui-report): 모달 디자인 테마 드롭다운 + 리뷰 흐름 theme 전달"
```

---

## Task 7: 실제 바이너리 E2E

- [ ] **Step 1: 5개 테마가 서로 다른 HTML 을 만든다**

임시 기획안으로:
```bash
for t in classic minimal executive compact pastel; do
  vib report plans/<plan>.md --type proposal --format html --theme "$t" --json
done
```
각 결과 HTML 의 `<style>` 블록이 테마별로 다름(예: minimal=uppercase, executive=네이비 배경 h1, pastel=라운드 section)을 확인. 모르는 `--theme zzz` 는 argparse 가 거부.

- [ ] **Step 2: docx accent 확인** — `--theme executive --format docx` 산출물을 python-docx 로 열어 머리글 색 #1B3A6B 확인(또는 Task 3 테스트로 대체).

---

## 완료 기준
- `pytest tests/core/reporting_cli tests/cli/test_vib_report_cmd.py` 전부 통과.
- `cd vibelign-gui && npx vitest run && npx tsc --noEmit && npx eslint src` 무오류(기존 flaky perf 제외).
- `--theme` 5종이 HTML 에서 시각적으로 구분되고, docx/pptx 는 accent 색 적용. 기본/미지정은 classic 불변.

## 의존성
- 독립 기능(이전 다듬기/가드 기능과 무관). 종류(3) × 테마(5) 직교 유지.
