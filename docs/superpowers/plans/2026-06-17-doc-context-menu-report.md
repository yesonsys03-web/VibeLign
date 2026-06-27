# 우클릭 → 보고서 작성 (문서/코드탐색 탭) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DocsViewer/CodeExplorer에서 `.md` 문서를 우클릭하면 "보고서 작성" 메뉴가 나오고, 그 문서를 source로 기존 `ExportReportModal`이 열려 임의 마크다운도 보고서로 내보낼 수 있게 한다.

**Architecture:** 신규 백엔드 능력은 단 하나 — `vib report --type doc`(임의 .md의 자체 헤딩 구조를 `ReportModel`로 변환). 나머지는 모두 기존 자산(렌더러/PDF/polish/page-number/ExportReportModal/report.ts 브릿지) 재사용. 프론트는 컨텍스트 메뉴 1개 추가(Docs) + 1개 항목 추가(Code) + `reportSourcePath` 상태 배선.

**Tech Stack:** Python(pytest, ruff) · React/TypeScript(Tauri, vitest) · 기존 `reporting_cli` IR(`ReportModel`/`Section`/`Block`).

---

## File Structure

**백엔드 (Python)**
- Modify `vibelign/core/reporting_cli/reader.py` — `parse_generic_markdown` + `build_doc_report_model` 신규
- Modify `vibelign/core/reporting_cli/__init__.py` — `build_doc_report_model` export
- Modify `vibelign/core/reporting_cli/templates.py` — `REPORT_TYPE_LABELS["doc"]`
- Modify `vibelign/commands/vib_report_cmd.py` — `--type doc` 분기(메인 + reject 경로 공유)
- Modify `vibelign/core/reporting_cli/emit.py` — `--type doc` 분기(emit/polish 경로)
- Test `tests/core/reporting_cli/test_reader.py`, `tests/cli/test_vib_report_cmd.py`, `tests/core/reporting_cli/test_emit.py`

**프론트 (TS/React)**
- Modify `vibelign-gui/src/lib/vib/report.ts` — `ReportType` 에 `"doc"` 추가
- Modify `vibelign-gui/src/components/plan-doc/ExportReportModal.tsx` — `doc` 타입 옵션 + `defaultType` prop
- Modify `vibelign-gui/src/pages/ReportView.tsx` — `sourcePath` prop, 빈-상태 우회
- Modify `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx` — "보고서 작성" 메뉴 항목 + `onGenerateReport`
- Modify `vibelign-gui/src/components/docs/DocsSidebar.tsx` — 컨텍스트 메뉴 + `onGenerateReport`
- Modify `vibelign-gui/src/pages/DocsViewer.tsx` — `onGenerateReport` prop 전달
- Modify `vibelign-gui/src/App.tsx` — `reportSourcePath` 상태 + 3곳 배선
- Test `vibelign-gui/src/components/docs/__tests__/DocsSidebar.report.test.tsx`

**검증 명령(프로젝트 기준)**
- Python 테스트: `.venv/bin/python -m pytest tests/core/reporting_cli tests/cli/test_vib_report_cmd.py -q`
- ruff: `.venv/bin/ruff check vibelign/core/reporting_cli vibelign/commands/vib_report_cmd.py`
- GUI 빌드: `cd vibelign-gui && npm run build`
- GUI 테스트: `cd vibelign-gui && npx vitest run <파일>`

---

## Phase A — 백엔드: 임의 마크다운 → 보고서

### Task 1: `parse_generic_markdown` + `build_doc_report_model`

**Files:**
- Modify: `vibelign/core/reporting_cli/reader.py`
- Test: `tests/core/reporting_cli/test_reader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/reporting_cli/test_reader.py` 파일 끝에 추가:

```python
from vibelign.core.reporting_cli.reader import (
    build_doc_report_model,
    parse_generic_markdown,
)

GENERIC_MD = """# 설계 노트

도입 문단입니다.

## 배경
첫 줄.
두 번째 줄.

## 할 일
- 항목 A
- 항목 B
1. 번호 항목
"""


def test_generic_title_from_h1():
    title, _sections = parse_generic_markdown(GENERIC_MD)
    assert title == "설계 노트"


def test_generic_preamble_becomes_overview_section():
    _title, sections = parse_generic_markdown(GENERIC_MD)
    assert sections[0].heading == "개요"
    assert sections[0].blocks[0].kind == "paragraph"
    assert "도입 문단입니다." in sections[0].blocks[0].text


def test_generic_headings_and_bullets():
    _title, sections = parse_generic_markdown(GENERIC_MD)
    headings = [s.heading for s in sections]
    assert headings == ["개요", "배경", "할 일"]
    todo = sections[2]
    bullet_block = next(b for b in todo.blocks if b.kind == "bullets")
    assert bullet_block.items == ["항목 A", "항목 B", "번호 항목"]


def test_generic_no_headings_all_overview():
    title, sections = parse_generic_markdown("그냥 메모\n- a\n- b\n")
    assert title == ""
    assert len(sections) == 1
    assert sections[0].heading == "개요"


def test_build_doc_model_uses_default_title_when_empty():
    model = build_doc_report_model("- 한 줄", date="2026-06-17", default_title="myfile")
    assert model.report_type == "doc"
    assert model.title == "myfile"
    assert model.sections[0].heading == "개요"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_reader.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_doc_report_model'`

- [ ] **Step 3: 구현**

`vibelign/core/reporting_cli/reader.py` 상단 import 교체:

```python
from vibelign.core.reporting_cli.models import Block, PlanningData, ReportModel, Section
```

파일 끝(`parse_plan_markdown` 아래)에 추가:

```python
_BULLET_RE = re.compile(r"^(?:[-*]\s+|\d+[.)]\s+)")


def parse_generic_markdown(text: str) -> tuple[str, list[Section]]:
    """임의 마크다운을 (제목, 섹션[]) 으로 변환한다(기획 양식 무관).
    첫 '# ' → 제목, 이후 '#'~'######' → 섹션 경계, 단락 → paragraph,
    불릿/번호 → bullets. 첫 헤딩 이전 본문과 헤딩 없는 문서는 '개요' 섹션으로 보존한다.
    """
    title = ""
    sections: list[Section] = []
    heading: str | None = None
    para: list[str] = []
    bullets: list[str] = []
    blocks: list[Block] = []

    def flush_para() -> None:
        nonlocal para
        joined = " ".join(s for s in (p.strip() for p in para) if s)
        if joined:
            blocks.append(Block(kind="paragraph", text=joined))
        para = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            blocks.append(Block(kind="bullets", items=bullets))
        bullets = []

    def flush_section() -> None:
        nonlocal blocks
        flush_bullets()
        flush_para()
        if blocks:
            sections.append(Section(heading=heading or "개요", blocks=blocks))
        blocks = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        h1 = line.startswith("# ") and not line.startswith("## ")
        if h1 and not title:
            title = line[2:].strip()
            continue
        m = re.match(r"^(#{1,6})\s+(?P<h>.+)$", line)
        if m:
            flush_section()
            heading = m.group("h").strip()
            continue
        stripped = line.strip()
        if _BULLET_RE.match(stripped):
            flush_para()
            item = _strip_bullet(line)
            if item:
                bullets.append(item)
            continue
        if not stripped:
            flush_bullets()
            flush_para()
            continue
        flush_bullets()
        para.append(line)

    flush_section()
    return title, sections


def build_doc_report_model(
    text: str,
    *,
    date: str,
    source_plan_path: str = "",
    author: str = "",
    default_title: str = "문서 보고서",
) -> ReportModel:
    """임의 .md → '문서 그대로' ReportModel(report_type='doc')."""
    title, sections = parse_generic_markdown(text)
    return ReportModel(
        title=title or default_title,
        report_type="doc",
        date=date,
        source_plan_path=source_plan_path,
        author=author,
        sections=sections,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_reader.py -q`
Expected: PASS (신규 5개 포함 전부 통과)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/reader.py tests/core/reporting_cli/test_reader.py
git commit -m "feat(report): 임의 마크다운 → ReportModel 변환(parse_generic_markdown)"
```

---

### Task 2: CLI `--type doc` 분기 + export

**Files:**
- Modify: `vibelign/core/reporting_cli/__init__.py`
- Modify: `vibelign/core/reporting_cli/templates.py:48-52`
- Modify: `vibelign/commands/vib_report_cmd.py:10-15,54-73`
- Test: `tests/cli/test_vib_report_cmd.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/cli/test_vib_report_cmd.py` 의 `_args` 헬퍼는 `type` 을 override 가능하므로 그대로 사용. 파일 끝에 추가:

```python
DOC_MD = """# 자유 문서

도입 문단.

## 배경
어떤 배경 설명.

## 항목
- 첫째
- 둘째
"""


def test_report_type_doc_renders_arbitrary_markdown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "free.md"
    doc.write_text(DOC_MD, encoding="utf-8")

    run_vib_report(_args(doc, type="doc", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["report_type"] == "doc"
    html = Path(payload["path"]).read_text(encoding="utf-8")
    assert "배경" in html
    assert "<li>첫째</li>" in html


def test_report_type_doc_empty_file_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "empty.md"
    doc.write_text("   \n\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(doc, type="doc", json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "내보낼 내용" in payload["error"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/cli/test_vib_report_cmd.py::test_report_type_doc_renders_arbitrary_markdown -q`
Expected: FAIL — `payload["ok"]` False (현재 doc 타입은 `build_report_model` 의 `unknown report type: doc` 로 실패)

- [ ] **Step 3a: export 추가**

`vibelign/core/reporting_cli/__init__.py` — `reader` import 와 `__all__` 수정:

```python
from vibelign.core.reporting_cli.reader import build_doc_report_model, parse_plan_markdown
```

`__all__` 리스트에 `"build_doc_report_model",` 추가(예: `"parse_plan_markdown",` 아래).

- [ ] **Step 3b: 라벨 추가**

`vibelign/core/reporting_cli/templates.py:48-52` 의 `REPORT_TYPE_LABELS` 에 항목 추가:

```python
REPORT_TYPE_LABELS: dict[str, str] = {
    "work": "업무 보고",
    "proposal": "제안서",
    "result": "결과 보고",
    "doc": "문서 보고서",
}
```

- [ ] **Step 3c: CLI 분기**

`vibelign/commands/vib_report_cmd.py:10-15` import 블록에 `build_doc_report_model` 추가:

```python
from vibelign.core.reporting_cli import (
    ReportRendererUnavailable,
    build_doc_report_model,
    build_report_model,
    parse_plan_markdown,
    polish_report_model,
)
```

`vibelign/commands/vib_report_cmd.py:54-73`(아래 원본)을 교체:

```python
    root = resolve_project_root(Path.cwd())
    try:
        data = parse_plan_markdown(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _fail(want_json, f"기획안을 읽을 수 없어요: {exc}")
        return

    try:
        model = build_report_model(
            data,
            raw.type,
            date=report_date,
            source_plan_path=str(plan_path),
            author=getattr(raw, "author", "") or "",
        )
    except ValueError as exc:
        _fail(want_json, str(exc))
        return

    slug_source = data.title or data.idea or plan_path.stem
```

교체 후:

```python
    root = resolve_project_root(Path.cwd())
    author = getattr(raw, "author", "") or ""
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(want_json, f"기획안을 읽을 수 없어요: {exc}")
        return

    if raw.type == "doc":
        model = build_doc_report_model(
            text,
            date=report_date,
            source_plan_path=str(plan_path),
            author=author,
            default_title=plan_path.stem,
        )
        if not model.sections:
            _fail(want_json, "문서에 내보낼 내용이 없습니다.")
            return
        slug_source = model.title or plan_path.stem
    else:
        try:
            data = parse_plan_markdown(text)
            model = build_report_model(
                data,
                raw.type,
                date=report_date,
                source_plan_path=str(plan_path),
                author=author,
            )
        except ValueError as exc:
            _fail(want_json, str(exc))
            return
        slug_source = data.title or data.idea or plan_path.stem
```

> 이후 emit-model / reject-blocks / polish / render 블록은 `model` 과 `slug_source` 만 쓰므로 변경 없음. reject 경로도 doc 모델(ReportModel) 위에서 `merge_models` 가 그대로 동작한다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/cli/test_vib_report_cmd.py -q`
Expected: PASS (기존 + 신규 2개). 기존 `unknown type` 회귀 테스트도 통과(다른 미지원 타입은 여전히 에러).

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/__init__.py vibelign/core/reporting_cli/templates.py vibelign/commands/vib_report_cmd.py tests/cli/test_vib_report_cmd.py
git commit -m "feat(report): vib report --type doc 로 임의 .md 보고서화"
```

---

### Task 3: emit/polish 경로 `--type doc` 분기

**Files:**
- Modify: `vibelign/core/reporting_cli/emit.py:6,26-29`
- Test: `tests/core/reporting_cli/test_emit.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/reporting_cli/test_emit.py` 파일 끝에 추가(기존 import/fixture 재사용; `root` 는 `tmp_path` 사용):

```python
from vibelign.core.reporting_cli.emit import emit_report_payload


def test_emit_doc_type_preserves_arbitrary_sections(tmp_path):
    doc = tmp_path / "free.md"
    doc.write_text("# 자유\n\n## 배경\n설명 문단.\n", encoding="utf-8")

    payload = emit_report_payload(
        str(doc), "doc", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )

    assert payload["ok"] is True
    assert payload["report_type"] == "doc"
    headings = [s["heading"] for s in payload["base"]["sections"]]
    assert "배경" in headings
```

> `model_to_dict` 의 section 직렬화 키가 `heading` 이 아니면(`title` 등) 이 단언을 실제 키로 맞춘다 — `tests/core/reporting_cli/test_model_json.py` 에서 키명을 확인할 것.

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_emit.py::test_emit_doc_type_preserves_arbitrary_sections -q`
Expected: FAIL — `ValueError: unknown report type: doc`

- [ ] **Step 3: 구현**

`vibelign/core/reporting_cli/emit.py:6` import 에 `build_doc_report_model` 추가:

```python
from vibelign.core.reporting_cli import build_doc_report_model, build_report_model, parse_plan_markdown
```

`vibelign/core/reporting_cli/emit.py:26-29`(아래 원본)을 교체:

```python
    plan = Path(plan_path).expanduser()
    data = parse_plan_markdown(plan.read_text(encoding="utf-8"))
    base = build_report_model(data, report_type, date=date, source_plan_path=str(plan), author=author)
    slug = _report_slug(data.title or data.idea or plan.stem)
```

교체 후:

```python
    plan = Path(plan_path).expanduser()
    text = plan.read_text(encoding="utf-8")
    if report_type == "doc":
        base = build_doc_report_model(
            text, date=date, source_plan_path=str(plan), author=author, default_title=plan.stem
        )
        slug = _report_slug(base.title or plan.stem)
    else:
        data = parse_plan_markdown(text)
        base = build_report_model(data, report_type, date=date, source_plan_path=str(plan), author=author)
        slug = _report_slug(data.title or data.idea or plan.stem)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli -q`
Expected: PASS (emit 신규 포함 전체 그린)

- [ ] **Step 5: ruff + 커밋**

```bash
.venv/bin/ruff check vibelign/core/reporting_cli vibelign/commands/vib_report_cmd.py
git add vibelign/core/reporting_cli/emit.py tests/core/reporting_cli/test_emit.py
git commit -m "feat(report): emit/polish 경로 --type doc 분기"
```

---

## Phase B — 프론트: 타입/모달/뷰

### Task 4: `ReportType` 에 `"doc"` 추가

**Files:**
- Modify: `vibelign-gui/src/lib/vib/report.ts:6`

- [ ] **Step 1: 타입 확장**

`vibelign-gui/src/lib/vib/report.ts:6` 교체:

```typescript
export type ReportType = "work" | "proposal" | "result" | "doc";
```

> `report.ts` 의 함수들은 `reportType` 을 그대로 CLI 인자로 전달하므로 본문 변경 불필요.

- [ ] **Step 2: 타입체크**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: PASS (에러 없음)

- [ ] **Step 3: 커밋**

```bash
git add vibelign-gui/src/lib/vib/report.ts
git commit -m "feat(gui-report): ReportType 에 doc 추가"
```

---

### Task 5: ExportReportModal — `doc` 옵션 + `defaultType` prop

**Files:**
- Modify: `vibelign-gui/src/components/plan-doc/ExportReportModal.tsx:20-24,33-40,50-51`

- [ ] **Step 1: TYPES 에 doc 추가**

`vibelign-gui/src/components/plan-doc/ExportReportModal.tsx:20-24` 교체:

```typescript
const TYPES: { id: ReportType; label: string }[] = [
  { id: "work", label: "업무 보고" },
  { id: "proposal", label: "제안서" },
  { id: "result", label: "결과 보고" },
  { id: "doc", label: "문서 그대로" },
];
```

- [ ] **Step 2: props 에 defaultType 추가**

`vibelign-gui/src/components/plan-doc/ExportReportModal.tsx:33-40` 의 `ExportReportModalProps` 인터페이스에 한 줄 추가(`onReviewRequest` 위 또는 아래):

```typescript
  /** 모달이 열릴 때 초기 선택될 보고서 종류(문서 우클릭 진입 시 "doc"). 기본 "work". */
  defaultType?: ReportType;
```

- [ ] **Step 3: 초기 상태에 반영**

`vibelign-gui/src/components/plan-doc/ExportReportModal.tsx:50-51` 의 구조분해와 useState 교체:

```typescript
export function ExportReportModal({ open, planPath, cwd, onClose, onReviewRequest, defaultType }: ExportReportModalProps) {
  const [reportType, setReportType] = useState<ReportType>(defaultType ?? "work");
```

> 모달은 ReportView 에서 `key` 로 remount 되므로(Task 6) `defaultType` 이 매 진입마다 초기값으로 적용된다.

- [ ] **Step 4: 빌드 확인**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/components/plan-doc/ExportReportModal.tsx
git commit -m "feat(gui-report): ExportReportModal 에 문서 그대로 타입 + defaultType"
```

---

### Task 6: ReportView — `sourcePath` 진입 + 빈-상태 우회

**Files:**
- Modify: `vibelign-gui/src/pages/ReportView.tsx:14-18,30,81-93,95,179-183,201-207`

- [ ] **Step 1: props + 상태 추가**

`vibelign-gui/src/pages/ReportView.tsx:14-18` 인터페이스 교체:

```typescript
interface ReportViewProps {
  projectDir: string;
  /** 보고서로 만들 기획안이 하나도 없을 때 기획 시작으로 이동. */
  onStart?: () => void;
  /** 문서/코드탐색에서 우클릭→보고서로 넘어온 소스 .md 경로(루트 상대). */
  sourcePath?: string | null;
  /** sourcePath 를 모달로 소비한 뒤 부모 상태를 비우게 알린다(재진입 시 재오픈 방지). */
  onSourceHandled?: () => void;
}
```

`vibelign-gui/src/pages/ReportView.tsx:30` 시그니처 교체:

```typescript
export default function ReportView({ projectDir, onStart, sourcePath, onSourceHandled }: ReportViewProps) {
```

`vibelign-gui/src/pages/ReportView.tsx:32`(`reportFor` 상태) 바로 아래에 추가:

```typescript
  const [fromDoc, setFromDoc] = useState(false);
```

- [ ] **Step 2: sourcePath 소비 effect 추가**

`vibelign-gui/src/pages/ReportView.tsx:81`(`useEffect(() => { ... listPlanningChatSessions ...`) **위에** 새 effect 추가:

```typescript
  useEffect(() => {
    if (!sourcePath) return;
    setReportFor(sourcePath);
    setFromDoc(true);
    onSourceHandled?.();
  }, [sourcePath, onSourceHandled]);
```

- [ ] **Step 3: 빈-상태 가드가 모달을 막지 않도록 수정**

`vibelign-gui/src/pages/ReportView.tsx:95` 교체:

```typescript
  if (plans !== null && plans.length === 0 && !reportFor) {
```

- [ ] **Step 4: 기획안 카드 클릭은 fromDoc=false 로**

`vibelign-gui/src/pages/ReportView.tsx:179-183` 의 onClick 교체:

```typescript
            <button
              type="button"
              onClick={() => {
                if (plan.outputPath) {
                  setFromDoc(false);
                  setReportFor(plan.outputPath);
                }
              }}
```

- [ ] **Step 5: 모달에 key + defaultType 전달**

`vibelign-gui/src/pages/ReportView.tsx:201-207` 교체:

```typescript
      <ExportReportModal
        key={`${reportFor ?? "none"}:${fromDoc ? "doc" : "plan"}`}
        open={reportFor !== null}
        planPath={reportFor ?? ""}
        cwd={projectDir}
        defaultType={fromDoc ? "doc" : "work"}
        onClose={() => setReportFor(null)}
        onReviewRequest={(type, format, theme, author, pageNumbers) => void handleReviewRequest(type, format, theme, author, pageNumbers)}
      />
```

- [ ] **Step 6: 빌드 확인**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add vibelign-gui/src/pages/ReportView.tsx
git commit -m "feat(gui-report): ReportView sourcePath 진입 + 빈-상태 우회"
```

---

## Phase C — 컨텍스트 메뉴 + 배선

### Task 7: CodeFileTree — "보고서 작성" 메뉴 항목

**Files:**
- Modify: `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:7-23,25,83,96,172-187`

- [ ] **Step 1: props + 헬퍼 추가**

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:15-17` 의 prop 주석/선언 아래에 추가:

```typescript
  // md/markdown 문서를 우클릭하면 "보고서 작성" 메뉴를 띄운다.
  onGenerateReport?: (path: string) => void;
```

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:20-23`(`isReviewableDoc`) 아래에 추가:

```typescript
// 보고서로 만들 수 있는 문서 확장자(임의 .md).
function isReportableDoc(path: string): boolean {
  const ext = path.split(".").pop()?.toLowerCase();
  return ext === "md" || ext === "markdown";
}
```

- [ ] **Step 2: 시그니처에 prop 추가**

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:25` 교체:

```typescript
export default function CodeFileTree({ files, selectedPath, onSelect, autoExpandAll, changes, onReviewInPlanning, onGenerateReport }: CodeFileTreeProps) {
```

- [ ] **Step 3: 우클릭 트리거를 reportable 도 포함하도록**

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:83` 아래에 한 줄 추가:

```typescript
        const reportable = !isDirectory && Boolean(onGenerateReport) && isReportableDoc(node.path);
```

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:96` 의 `onContextMenu` 교체:

```typescript
            onContextMenu={(reviewable || reportable) ? (e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, path: node.path }); } : undefined}
```

- [ ] **Step 4: 메뉴에 항목 추가(조건부)**

`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx:172-187` 의 메뉴 블록 교체:

```typescript
    {menu && (
      <div
        role="menu"
        style={{ position: "fixed", left: menu.x, top: menu.y, zIndex: 1000, border: "2px solid #1A1A1A", background: "#fff", boxShadow: "var(--shadow-sm)" }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {onReviewInPlanning && isReviewableDoc(menu.path) && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ display: "block", width: "100%", textAlign: "left", textTransform: "none", letterSpacing: 0 }}
            onClick={() => { onReviewInPlanning?.(menu.path); setMenu(null); }}
          >
            기획방에서 검토
          </button>
        )}
        {onGenerateReport && isReportableDoc(menu.path) && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ display: "block", width: "100%", textAlign: "left", textTransform: "none", letterSpacing: 0 }}
            onClick={() => { onGenerateReport?.(menu.path); setMenu(null); }}
          >
            보고서 작성
          </button>
        )}
      </div>
    )}
```

- [ ] **Step 5: 빌드 확인**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add vibelign-gui/src/components/code-explorer/CodeFileTree.tsx
git commit -m "feat(gui-report): 코드탐색 우클릭에 보고서 작성 항목 추가"
```

---

### Task 8: DocsSidebar — 컨텍스트 메뉴 신규

**Files:**
- Modify: `vibelign-gui/src/components/docs/DocsSidebar.tsx:1,5-11,21-25,47-48,72,175-176`
- Test: `vibelign-gui/src/components/docs/__tests__/DocsSidebar.report.test.tsx`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `vibelign-gui/src/components/docs/__tests__/DocsSidebar.report.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DocsSidebar from "../DocsSidebar";
import type { DocsIndexEntry } from "../../../lib/vib";

const DOCS: DocsIndexEntry[] = [
  { category: "Docs", path: "notes/plan.md", title: "내 노트", modified_at_ms: 0 },
];

function renderSidebar(onGenerateReport = vi.fn()) {
  render(
    <DocsSidebar
      docs={DOCS}
      query="plan"
      selectedPath={null}
      onQueryChange={() => {}}
      onSelect={() => {}}
      onGenerateReport={onGenerateReport}
    />,
  );
  return onGenerateReport;
}

describe("DocsSidebar 보고서 작성 컨텍스트 메뉴", () => {
  it("md 문서 우클릭 시 '보고서 작성' 메뉴가 뜨고 콜백이 경로를 넘긴다", () => {
    const onGenerateReport = renderSidebar();
    const docBtn = screen.getByTitle("notes/plan.md");
    fireEvent.contextMenu(docBtn);
    const item = screen.getByText("보고서 작성");
    fireEvent.click(item);
    expect(onGenerateReport).toHaveBeenCalledWith("notes/plan.md");
  });
});
```

> `query="plan"` 으로 검색 모드를 켜 카테고리/폴더가 자동 펼쳐져 문서 버튼이 즉시 보이게 한다. `DocsIndexEntry` 의 정확한 필드는 `vibelign-gui/src/lib/vib` 에서 확인(불일치 시 맞춤).

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd vibelign-gui && npx vitest run src/components/docs/__tests__/DocsSidebar.report.test.tsx`
Expected: FAIL — "보고서 작성" 텍스트를 찾지 못함

- [ ] **Step 3a: import + props + 헬퍼**

`vibelign-gui/src/components/docs/DocsSidebar.tsx:1` 교체:

```typescript
import { useEffect, useState, type ReactNode } from "react";
```

`vibelign-gui/src/components/docs/DocsSidebar.tsx:5-11` 의 `DocsSidebarProps` 에 추가:

```typescript
  onGenerateReport?: (path: string) => void;
```

`vibelign-gui/src/components/docs/DocsSidebar.tsx:21-25` 사이(컴포넌트 밖)에 헬퍼 추가:

```typescript
function isReportableDoc(path: string): boolean {
  const ext = path.split(".").pop()?.toLowerCase();
  return ext === "md" || ext === "markdown";
}
```

- [ ] **Step 3b: 메뉴 상태 + 시그니처**

`vibelign-gui/src/components/docs/DocsSidebar.tsx:47` 교체:

```typescript
export default function DocsSidebar({ docs, query, selectedPath, onQueryChange, onSelect, onGenerateReport }: DocsSidebarProps) {
```

`vibelign-gui/src/components/docs/DocsSidebar.tsx:48-49`(useState 들) 아래에 추가:

```typescript
  const [menu, setMenu] = useState<{ x: number; y: number; path: string } | null>(null);
  useEffect(() => {
    if (!menu) return;
    const onDismiss = () => setMenu(null);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(null); };
    document.addEventListener("mousedown", onDismiss);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDismiss);
      document.removeEventListener("keydown", onKey);
    };
  }, [menu]);
```

- [ ] **Step 3c: 문서 버튼에 onContextMenu**

`vibelign-gui/src/components/docs/DocsSidebar.tsx:91`(`onClick={() => onSelect(entry.path)}`) 바로 아래에 추가:

```typescript
        onContextMenu={
          onGenerateReport && isReportableDoc(entry.path)
            ? (e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, path: entry.path }); }
            : undefined
        }
```

- [ ] **Step 3d: 메뉴 렌더**

`vibelign-gui/src/components/docs/DocsSidebar.tsx:175`(최상위 `return ( <div ...>`) 의 여는 태그를 Fragment 로 감싸고, 닫는 `</div>` 뒤에 메뉴를 추가한다. 즉 `return (` 직후 구조를:

```typescript
  return (
    <>
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
```

로 바꾸고(기존 첫 `<div ...>` 를 그대로 둠), 컴포넌트 최종 `</div>` 다음에:

```typescript
    {menu && (
      <div
        role="menu"
        style={{ position: "fixed", left: menu.x, top: menu.y, zIndex: 1000, border: "2px solid #1A1A1A", background: "#fff", boxShadow: "var(--shadow-sm)" }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          style={{ display: "block", width: "100%", textAlign: "left", textTransform: "none", letterSpacing: 0 }}
          onClick={() => { onGenerateReport?.(menu.path); setMenu(null); }}
        >
          보고서 작성
        </button>
      </div>
    )}
    </>
  );
```

를 추가해 `</>` 로 닫는다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd vibelign-gui && npx vitest run src/components/docs/__tests__/DocsSidebar.report.test.tsx`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/components/docs/DocsSidebar.tsx vibelign-gui/src/components/docs/__tests__/DocsSidebar.report.test.tsx
git commit -m "feat(gui-report): 문서 사이드바 우클릭 보고서 작성 메뉴"
```

---

### Task 9: DocsViewer — `onGenerateReport` 전달

**Files:**
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx:15-19,367-373`

- [ ] **Step 1: props 추가**

`vibelign-gui/src/pages/DocsViewer.tsx:15-19` 교체:

```typescript
interface DocsViewerProps {
  projectDir: string;
  onGenerateReport?: (path: string) => void;
}

export default function DocsViewer({ projectDir, onGenerateReport }: DocsViewerProps) {
```

- [ ] **Step 2: DocsSidebar 로 전달**

`vibelign-gui/src/pages/DocsViewer.tsx:367-373` 의 `<DocsSidebar ... />` 에 prop 추가:

```typescript
          <DocsSidebar
            docs={docsIndex}
            query={query}
            selectedPath={selectedPath}
            onQueryChange={setQuery}
            onSelect={setSelectedPath}
            onGenerateReport={onGenerateReport}
          />
```

- [ ] **Step 3: 빌드 확인**

Run: `cd vibelign-gui && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 4: 커밋**

```bash
git add vibelign-gui/src/pages/DocsViewer.tsx
git commit -m "feat(gui-report): DocsViewer onGenerateReport prop 패스스루"
```

---

### Task 10: App.tsx — `reportSourcePath` 상태 + 3곳 배선

**Files:**
- Modify: `vibelign-gui/src/App.tsx:95(근방),352-355,629,656,657`

- [ ] **Step 1: 상태 + 핸들러 추가**

`vibelign-gui/src/App.tsx:95`(`const [page, setPage] = useState<Page>("home");`) 아래에 추가:

```typescript
  const [reportSourcePath, setReportSourcePath] = useState<string | null>(null);
```

`vibelign-gui/src/App.tsx:352-355` 의 `navigate` 함수 **아래**에 헬퍼 추가:

```typescript
  function openReportFor(path: string) {
    setReportSourcePath(path);
    navigate("report");
  }
```

- [ ] **Step 2: ReportView 에 sourcePath 연결**

`vibelign-gui/src/App.tsx:629` 교체:

```typescript
                {page === "report" && <ReportView projectDir={projectDir} sourcePath={reportSourcePath} onSourceHandled={() => setReportSourcePath(null)} onStart={() => { if (planningResult) navigate("planning"); else setPage("home"); }} />}
```

- [ ] **Step 3: DocsViewer 배선**

`vibelign-gui/src/App.tsx:656` 교체:

```typescript
                {page === "docs" && <DocsViewer projectDir={projectDir} onGenerateReport={openReportFor} />}
```

- [ ] **Step 4: CodeExplorer 배선**

`vibelign-gui/src/App.tsx:657` 의 `<CodeExplorer ... />` 에 `onGenerateReport={openReportFor}` 추가(기존 `onReviewInPlanning` 옆):

```typescript
                {page === "code" && <CodeExplorer projectDir={projectDir} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} planningContract={planningResult?.contract ?? null} planningDocStale={planningResult?.docStale ?? false} onReviewInPlanning={(path) => { if (projectDir) void openPlanningRoom(projectDir, buildPlanReviewPrompt(path), path); }} onGenerateReport={openReportFor} />}
```

> CodeExplorer 가 `onGenerateReport` 를 받아 `CodeFileTree` 로 내려보내는지 확인. 안 내려보내면 `vibelign-gui/src/pages/CodeExplorer.tsx` 에서 prop 을 추가해 `CodeFileTree` 로 전달(아래 Step 5).

- [ ] **Step 5: CodeExplorer prop 패스스루 확인/추가**

`vibelign-gui/src/pages/CodeExplorer.tsx` 에서 `onReviewInPlanning` 이 어떻게 `CodeFileTree` 로 전달되는지 보고, 동일 패턴으로 `onGenerateReport?: (path: string) => void` 를 props 에 추가하고 `<CodeFileTree ... onGenerateReport={onGenerateReport} />` 로 전달한다. (정확한 줄은 구현 시 확인 — `onReviewInPlanning` 바로 옆.)

- [ ] **Step 6: 빌드 + 전체 GUI 테스트**

Run: `cd vibelign-gui && npm run build`
Expected: `build exit=0`

Run: `cd vibelign-gui && npx vitest run`
Expected: 전체 PASS

- [ ] **Step 7: 커밋**

```bash
git add vibelign-gui/src/App.tsx vibelign-gui/src/pages/CodeExplorer.tsx
git commit -m "feat(gui-report): 문서/코드탐색 우클릭→보고서 탭 배선(reportSourcePath)"
```

---

## 최종 검증 (Final verification)

- [ ] **Step 1: 백엔드 전체 그린**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli tests/cli/test_vib_report_cmd.py tests/cli/test_vib_report_stamp_cmd.py -q`
Expected: PASS

- [ ] **Step 2: ruff**

Run: `.venv/bin/ruff check vibelign/core/reporting_cli vibelign/commands/vib_report_cmd.py`
Expected: All checks passed

- [ ] **Step 3: GUI 빌드 + 테스트**

Run: `cd vibelign-gui && npm run build && npx vitest run`
Expected: build exit=0, 테스트 전체 PASS

- [ ] **Step 4: 수동 확인(앱 실행)**
  1. 문서 탭에서 임의 `.md` 우클릭 → "보고서 작성" → report 탭에서 모달이 "문서 그대로" 선택으로 자동 오픈
  2. PDF 생성 → 임의 md 본문(헤딩/불릿)이 보고서에 보존되는지 확인
  3. 코드탐색 탭에서 `.md` 우클릭 → "기획방에서 검토" + "보고서 작성" 둘 다 표시
  4. 기존 기획안 보고서 흐름(ReportView 기획안 카드 → 모달 "업무 보고" 기본)이 회귀 없이 동작

---

## Self-Review 결과

- **Spec coverage:** 스펙 §5.1(doc CLI)=Task1-3, §5.2(메뉴)=Task7-8, §5.3(배선)=Task6,9,10, §8(테스트)=각 Task + 최종검증. 누락 없음.
- **Type consistency:** `build_doc_report_model`/`parse_generic_markdown`/`isReportableDoc`/`onGenerateReport`/`reportSourcePath`/`defaultType`/`onSourceHandled` 가 정의·사용처에서 동일 명칭으로 일치.
- **알려진 확인 지점(구현 중 검증):** `model_to_dict` 의 section 키명(Task3 테스트), `CodeExplorer.tsx`/`DocsViewer.tsx` 의 정확한 줄번호, `DocsIndexEntry` 필드명. 모두 해당 Step에 명시.
