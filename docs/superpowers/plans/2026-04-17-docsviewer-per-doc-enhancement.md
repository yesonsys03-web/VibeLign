# DocsViewer 우측 패널 문서별 컨텐츠 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DocsViewer 우측 패널의 하드코딩된 메타 설명(아키텍처 한 줄·핵심 실행 규칙·Edge Cases·Final Success Criteria)을 문서별 휴리스틱 추출 결과로 교체하고, AI 요약 버튼으로 고품질 LLM 요약을 on-demand 로 얻을 수 있게 한다.

**Architecture:** Python `docs_visualizer.py` 에 휴리스틱 추출기(tldr/rules/criteria/edge_cases/components)를 추가해 artifact JSON 에 `heuristic_fields` 로 저장한다. GUI 는 이 필드가 있으면 렌더, 없으면 카드 숨김. "AI 요약" 버튼 클릭 시 Tauri → Python `vib docs-enhance` subcommand 가 LLM 을 호출해 `ai_fields` 로 덮어쓰고 artifact 를 재기록한다. 다이어그램이 이미 쓰는 `provenance: authored|heuristic|ai_draft` 패턴을 텍스트 필드에 그대로 확장한다.

**Tech Stack:** Python 3 (dataclass, re), TypeScript/React (Tauri 웹뷰), Rust (Tauri command), Anthropic API (urllib, ask_cmd.py 패턴 재사용), keys_store.py.

---

## 파일 구조

### 생성

- **`vibelign/core/docs_ai_enhance.py`** — LLM 호출 래퍼. 단일 문서 텍스트를 받아 구조화된 JSON 응답(tldr/rules/criteria/edge_cases/components)을 반환. Anthropic/OpenAI/Gemini 어댑터. `ask_cmd.py` 스타일 재사용.
- **`tests/test_docs_enhance_heuristics.py`** — 휴리스틱 추출기 단위 테스트.
- **`tests/test_docs_ai_enhance.py`** — LLM 래퍼 모킹 테스트(네트워크 호출 없이 프롬프트 구성·JSON 파싱 검증).
- **`vibelign-gui/src/components/docs/AiEnhanceButton.tsx`** — AI 요약 버튼 + consent 모달 + 사용량 표시.

### 수정

- **`vibelign/core/docs_cache.py`** — `DOCS_VISUAL_SCHEMA_VERSION` 1 → 2, `DOCS_VISUAL_GENERATOR_VERSION` "heuristic-mermaid-v1" → "heuristic-v2", `minimum_required_fields` 에 `heuristic_fields` 추가, `docs_visual_schema_example()` 예시 갱신.
- **`vibelign/core/docs_visualizer.py`** — 새 dataclass `HeuristicEnhancedFields`, `AIEnhancedFields` 추가. 새 extractor 함수 5개. `visualize_markdown_bytes` 끝부분에 `heuristic_fields` 채우기. `DocsVisualArtifact` 에 필드 추가.
- **`vibelign/commands/vib_docs_build_cmd.py`** — `run_vib_docs_enhance` 핸들러 추가 (단일 문서 LLM 호출 + `ai_fields` 갱신).
- **`vibelign/cli/cli_core_commands.py`** — `docs-enhance` subcommand 등록.
- **`vibelign/cli/vib_cli.py:81`** — help metavar 목록에 `docs-enhance` 추가.
- **`vibelign/cli/cli_base.py`** — help 설명에 `docs-enhance` 한 줄 추가.
- **`vibelign-gui/src/lib/vib.ts`** — TS 타입 `DocsVisualHeuristicFields`, `DocsVisualAIFields` 추가. `DocsVisualArtifact` 에 필드 추가. `enhanceDocWithAi(root, path, providerKeys)` bridge 함수 추가.
- **`vibelign-gui/src-tauri/src/lib.rs`** — `enhance_doc_with_ai` Tauri command 추가, `invoke_handler!` 등록.
- **`vibelign-gui/src/components/docs/VisualSummaryPane.tsx`** — 하드코딩된 `keyRules/successCriteria/edgeCases/fileRows` 제거. artifact 필드 기반 조건부 카드. AiEnhanceButton 배치.
- **`vibelign-gui/src/pages/DocsViewer.tsx`** — artifact 갱신 시점 관리 (AI 호출 후 재조회).
- **`vibelign-gui/src/pages/Settings.tsx`** — AI 요약 동의 상태 토글/초기화.

### 테스트

- `tests/test_docs_enhance_heuristics.py` (신규)
- `tests/test_docs_ai_enhance.py` (신규)
- `tests/test_docs_build_cmd.py` (기존, enhance 커맨드 테스트 케이스 추가)
- `tests/test_vib_cli_surface.py` (기존, `docs-enhance` 명령 등록 확인)

---

## 작업 순서 (TDD, bite-sized)

### Task 1: 스키마 확장 — 새 dataclass 추가 및 버전 bump

**Files:**
- Modify: `vibelign/core/docs_visualizer.py:59-79` (DocsVisualArtifact dataclass)
- Modify: `vibelign/core/docs_cache.py:14-15` (schema/generator 버전)
- Test: `tests/test_docs_visualizer.py` 기존 테스트로 회귀 확인

- [ ] **Step 1: 버전 bump**

`vibelign/core/docs_cache.py:14-15`:

```python
DOCS_VISUAL_SCHEMA_VERSION = 2
DOCS_VISUAL_GENERATOR_VERSION = "heuristic-v2"
```

- [ ] **Step 2: 새 dataclass 2개를 docs_visualizer.py 에 추가**

`vibelign/core/docs_visualizer.py` 의 `DiagramBlock` dataclass 뒤(56번 라인 이후) 에 삽입:

```python
@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_START ===
class HeuristicEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "heuristic"
    generator: str = "heuristic-v2"
    generated_at: str = ""
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_START ===
class AIEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "ai_draft"
    model: str = ""
    provider: str = ""
    generated_at: str = ""
    source_hash: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_END ===
```

- [ ] **Step 3: DocsVisualArtifact 에 두 필드 추가**

`vibelign/core/docs_visualizer.py:61-73` 의 `DocsVisualArtifact` 를 다음으로 교체:

```python
@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_START ===
class DocsVisualArtifact:
    source_path: str
    source_hash: str
    generated_at: str
    generator_version: str
    schema_version: int
    title: str
    summary: str
    sections: list[VisualSection] = field(default_factory=list)
    glossary: list[GlossaryEntry] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    diagram_blocks: list[DiagramBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    heuristic_fields: Optional[HeuristicEnhancedFields] = None
    ai_fields: Optional[AIEnhancedFields] = None

    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_START ===
    def to_dict(self) -> dict[str, Any]:
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_END ===
        return asdict(self)
    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_END ===
```

- [ ] **Step 4: 기존 회귀 테스트 실행**

```bash
cd /Users/topsphinx/Documents/coding/VibeLign
python -m pytest tests/test_docs_visualizer.py -v
```

Expected: 모든 기존 테스트 PASS (새 필드는 None default 라 기존 로직 영향 없음).

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/docs_visualizer.py vibelign/core/docs_cache.py
git commit -m "feat(docs-visualizer): 휴리스틱·AI enhanced fields 스키마 v2 추가"
```

---

### Task 2: 휴리스틱 TLDR 추출기

**Files:**
- Modify: `vibelign/core/docs_visualizer.py` (새 함수 `_extract_tldr_one_liner`)
- Create: `tests/test_docs_enhance_heuristics.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_docs_enhance_heuristics.py`:

```python
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ensure_stub_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules[name] = package


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_ensure_stub_package("vibelign", ROOT / "vibelign")
_ensure_stub_package("vibelign.core", ROOT / "vibelign" / "core")
_load_module("vibelign.core.docs_cache", ROOT / "vibelign" / "core" / "docs_cache.py")
docs_visualizer = _load_module(
    "vibelign.core.docs_visualizer", ROOT / "vibelign" / "core" / "docs_visualizer.py"
)


class ExtractTldrTest(unittest.TestCase):
    def test_first_sentence_of_first_paragraph(self):
        lines = [
            "# Title",
            "",
            "첫 문장입니다. 두번째 문장도 있어요.",
            "",
            "## Section",
        ]
        result = docs_visualizer._extract_tldr_one_liner(lines)
        self.assertEqual(result, "첫 문장입니다.")

    def test_empty_document_returns_empty(self):
        self.assertEqual(docs_visualizer._extract_tldr_one_liner([]), "")

    def test_no_paragraph_only_headings(self):
        lines = ["# A", "## B", "## C"]
        self.assertEqual(docs_visualizer._extract_tldr_one_liner(lines), "")

    def test_ignores_code_block_and_list(self):
        lines = [
            "# Title",
            "",
            "```",
            "inside code",
            "```",
            "",
            "- list item",
            "",
            "진짜 요약 문장.",
        ]
        self.assertEqual(docs_visualizer._extract_tldr_one_liner(lines), "진짜 요약 문장.")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractTldrTest -v
```

Expected: FAIL — `_extract_tldr_one_liner` 함수 없음.

- [ ] **Step 3: 최소 구현 추가**

`vibelign/core/docs_visualizer.py` 의 `_derive_summary` 함수(1001번 라인) 뒤에 삽입:

```python
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TLDR_ONE_LINER_START ===
def _extract_tldr_one_liner(lines: list[str]) -> str:
    paragraph = _first_meaningful_paragraph(lines)
    if not paragraph:
        return ""
    parts = re.split(r"(?<=[.!?。？！])\s+|(?<=[.!?。？！])$", paragraph)
    first = next((part.strip() for part in parts if part.strip()), "")
    return first[:180]
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_TLDR_ONE_LINER_END ===
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractTldrTest -v
```

Expected: PASS (4/4).

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/docs_visualizer.py tests/test_docs_enhance_heuristics.py
git commit -m "feat(docs-visualizer): _extract_tldr_one_liner 휴리스틱 추가"
```

---

### Task 3: 규칙/기준/Edge Case 섹션 추출기

**Files:**
- Modify: `vibelign/core/docs_visualizer.py`
- Test: `tests/test_docs_enhance_heuristics.py` (추가)

- [ ] **Step 1: 실패 테스트 추가 (test_docs_enhance_heuristics.py 내)**

```python
class ExtractBulletSectionTest(unittest.TestCase):
    def test_key_rules_from_rule_heading(self):
        lines = [
            "# Doc",
            "",
            "## 핵심 규칙",
            "",
            "- 절대 금지 항목 A",
            "- 항상 지킬 것 B",
            "",
            "## 다른 섹션",
            "- 무관한 내용",
        ]
        rules = docs_visualizer._extract_bullet_section(lines, docs_visualizer.RULES_HEADING_RE)
        self.assertEqual(rules, ["절대 금지 항목 A", "항상 지킬 것 B"])

    def test_success_criteria_from_success_heading(self):
        lines = [
            "# Doc",
            "",
            "## Success Criteria",
            "- 테스트 100% 통과",
            "- 지연 < 1초",
        ]
        criteria = docs_visualizer._extract_bullet_section(
            lines, docs_visualizer.CRITERIA_HEADING_RE
        )
        self.assertEqual(criteria, ["테스트 100% 통과", "지연 < 1초"])

    def test_edge_cases_from_edge_heading(self):
        lines = [
            "# Doc",
            "",
            "## 예외 상황",
            "- 네트워크 끊김",
            "- 빈 입력",
        ]
        edges = docs_visualizer._extract_bullet_section(lines, docs_visualizer.EDGE_HEADING_RE)
        self.assertEqual(edges, ["네트워크 끊김", "빈 입력"])

    def test_returns_empty_when_no_matching_heading(self):
        lines = ["# Doc", "", "## 무관한 섹션", "- 내용"]
        self.assertEqual(
            docs_visualizer._extract_bullet_section(lines, docs_visualizer.RULES_HEADING_RE),
            [],
        )
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractBulletSectionTest -v
```

Expected: FAIL — `_extract_bullet_section`, 정규식 상수 없음.

- [ ] **Step 3: 정규식 상수와 함수 추가**

`vibelign/core/docs_visualizer.py` 의 `ACTION_HEADING_RE` (159번 라인) 뒤에 추가:

```python
RULES_HEADING_RE = re.compile(
    r"\b(rule|rules|principle|principles|guideline|guidelines|"
    r"규칙|원칙|지침|가이드라인)\b",
    re.IGNORECASE,
)
CRITERIA_HEADING_RE = re.compile(
    r"\b(success\s*criteria|acceptance|success|goal|goals|"
    r"성공\s*기준|기준|목표|완료\s*조건|수용)\b",
    re.IGNORECASE,
)
EDGE_HEADING_RE = re.compile(
    r"\b(edge\s*cases?|pitfall|pitfalls|caveat|caveats|gotcha|"
    r"예외|주의|주의사항|함정|엣지)\b",
    re.IGNORECASE,
)
COMPONENTS_HEADING_RE = re.compile(
    r"\b(component|components|module|modules|architecture|structure|"
    r"구성\s*요소|구성|모듈|아키텍처|구조)\b",
    re.IGNORECASE,
)
```

그리고 `_extract_action_items` 함수(437번 라인) 뒤에 새 함수 추가:

```python
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_BULLET_SECTION_START ===
def _extract_bullet_section(lines: list[str], heading_re: re.Pattern[str]) -> list[str]:
    items: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, _level, title in heading_ranges:
        if not heading_re.search(title):
            continue
        for line in lines[start + 1 : end]:
            bullet = BULLET_RE.match(line)
            checklist = CHECKLIST_RE.match(line)
            if checklist:
                items.append(_strip_inline_markdown(checklist.group("text")))
            elif bullet:
                items.append(_strip_inline_markdown(bullet.group("text")))
    return _dedupe_keep_order(items)
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_BULLET_SECTION_END ===
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractBulletSectionTest -v
```

Expected: PASS (4/4).

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/docs_visualizer.py tests/test_docs_enhance_heuristics.py
git commit -m "feat(docs-visualizer): 규칙·기준·edge-case 섹션 bullet 추출기"
```

---

### Task 4: Components 추출기 (H2 + 첫 문장)

**Files:**
- Modify: `vibelign/core/docs_visualizer.py`
- Test: `tests/test_docs_enhance_heuristics.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
class ExtractComponentsTest(unittest.TestCase):
    def test_h2_with_first_sentence(self):
        lines = [
            "# Doc",
            "",
            "## 파서",
            "markdown 을 AST 로 변환합니다. 그리고 캐시합니다.",
            "",
            "## 렌더러",
            "AST 를 HTML 로 렌더합니다.",
        ]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(
            items,
            ["파서 — markdown 을 AST 로 변환합니다.", "렌더러 — AST 를 HTML 로 렌더합니다."],
        )

    def test_limits_to_six_items(self):
        lines = ["# Doc"]
        for i in range(10):
            lines += ["", f"## Section {i}", f"Summary {i}."]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(len(items), 6)

    def test_skips_h2_with_no_content(self):
        lines = [
            "# Doc",
            "",
            "## Empty",
            "",
            "## Has content",
            "진짜 내용.",
        ]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(items, ["Has content — 진짜 내용."])
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractComponentsTest -v
```

Expected: FAIL.

- [ ] **Step 3: 구현 추가**

`vibelign/core/docs_visualizer.py` 의 `_extract_bullet_section` 뒤에 삽입:

```python
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_COMPONENTS_START ===
def _extract_components(lines: list[str]) -> list[str]:
    items: list[str] = []
    heading_ranges = _extract_heading_ranges(lines)
    for start, end, level, title in heading_ranges:
        if level != 2:
            continue
        summary = _first_meaningful_paragraph(lines[start + 1 : end])
        if not summary:
            continue
        parts = re.split(r"(?<=[.!?。？！])\s+|(?<=[.!?。？！])$", summary)
        first = next((part.strip() for part in parts if part.strip()), "")
        if not first:
            continue
        items.append(f"{title} — {first}")
        if len(items) >= COMPONENT_CAP:
            break
    return items
# === ANCHOR: DOCS_VISUALIZER__EXTRACT_COMPONENTS_END ===
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::ExtractComponentsTest -v
```

Expected: PASS (3/3).

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/docs_visualizer.py tests/test_docs_enhance_heuristics.py
git commit -m "feat(docs-visualizer): components 추출기 (H2 + 첫 문장)"
```

---

### Task 5: visualize_markdown_bytes 에 heuristic_fields 주입

**Files:**
- Modify: `vibelign/core/docs_visualizer.py:1030-1099` (visualize_markdown_bytes)
- Test: `tests/test_docs_enhance_heuristics.py`

- [ ] **Step 1: 통합 테스트 추가**

```python
import tempfile
class VisualizeMarkdownIntegrationTest(unittest.TestCase):
    def test_heuristic_fields_populated(self):
        content = """# 제목

이 문서는 샘플 계획입니다. 예시 용도입니다.

## 규칙

- 절대 외부 API 를 호출하지 않는다
- 모든 경로는 posix

## 성공 기준

- 모든 테스트 통과
- 문서 파싱 < 100ms

## 예외 상황

- 빈 파일 처리

## 주요 구성

### 파서

AST 로 변환합니다.

### 렌더러

HTML 로 출력합니다.
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "plan.md"
            target.write_text(content, encoding="utf-8")
            artifact = docs_visualizer.visualize_markdown_file(target)
            self.assertIsNotNone(artifact.heuristic_fields)
            hf = artifact.heuristic_fields
            self.assertEqual(hf.tldr_one_liner, "이 문서는 샘플 계획입니다.")
            self.assertIn("절대 외부 API 를 호출하지 않는다", hf.key_rules)
            self.assertIn("모든 테스트 통과", hf.success_criteria)
            self.assertIn("빈 파일 처리", hf.edge_cases)
            self.assertEqual(hf.provenance, "heuristic")

    def test_ai_fields_default_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "x.md"
            target.write_text("# x\n\nintro.\n", encoding="utf-8")
            artifact = docs_visualizer.visualize_markdown_file(target)
            self.assertIsNone(artifact.ai_fields)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py::VisualizeMarkdownIntegrationTest -v
```

Expected: FAIL — `heuristic_fields` 가 None.

- [ ] **Step 3: visualize_markdown_bytes 수정**

`vibelign/core/docs_visualizer.py:1085` 의 `artifact = build_artifact_shell(...)` 앞에 heuristic_fields 빌드 로직 삽입. `visualize_markdown_bytes` 함수 끝부분(`1085-1099`) 을 다음으로 교체:

```python
    heuristic_fields = HeuristicEnhancedFields(
        tldr_one_liner=_extract_tldr_one_liner(lines),
        key_rules=_extract_bullet_section(lines, RULES_HEADING_RE),
        success_criteria=_extract_bullet_section(lines, CRITERIA_HEADING_RE),
        edge_cases=_extract_bullet_section(lines, EDGE_HEADING_RE),
        components=_extract_components(lines),
        generator=DOCS_VISUAL_GENERATOR_VERSION,
        generated_at=current_generated_at(),
    )

    artifact = build_artifact_shell(source_path, title=title, summary=summary)
    return DocsVisualArtifact(
        source_path=artifact.source_path,
        source_hash=compute_source_hash(source_path.resolve()),
        generated_at=artifact.generated_at,
        generator_version=artifact.generator_version,
        schema_version=artifact.schema_version,
        title=artifact.title,
        summary=artifact.summary,
        sections=sections,
        glossary=glossary,
        action_items=action_items,
        diagram_blocks=diagram_blocks,
        warnings=warnings,
        heuristic_fields=heuristic_fields,
        ai_fields=None,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_docs_enhance_heuristics.py tests/test_docs_visualizer.py -v
```

Expected: 모두 PASS.

- [ ] **Step 5: docs_cache.py 의 minimum_required_fields 와 schema example 갱신**

`vibelign/core/docs_cache.py:197-225` 의 `docs_visual_schema_example` 을 다음으로 교체(heuristic_fields 예시 추가):

```python
def docs_visual_schema_example() -> dict[str, object]:
    return {
        "schema_version": DOCS_VISUAL_SCHEMA_VERSION,
        "generator_version": DOCS_VISUAL_GENERATOR_VERSION,
        "generated_at": "2026-04-17T00:00:00Z",
        "source_path": "docs/wiki/index.md",
        "source_hash": "<sha256-of-normalized-source>",
        "title": "VibeLign Wiki",
        "summary": "Stable visual artifact contract example.",
        "sections": [
            {"id": "intro", "title": "Intro", "level": 1, "summary": "Top section."}
        ],
        "glossary": [],
        "action_items": [],
        "diagram_blocks": [],
        "warnings": [],
        "heuristic_fields": {
            "tldr_one_liner": "샘플 문서의 한 줄 요약.",
            "key_rules": ["핵심 규칙 1", "핵심 규칙 2"],
            "success_criteria": ["성공 기준 1"],
            "edge_cases": ["예외 상황 1"],
            "components": ["파서 — AST 변환"],
            "provenance": "heuristic",
            "generator": DOCS_VISUAL_GENERATOR_VERSION,
            "generated_at": "2026-04-17T00:00:00Z",
        },
        "ai_fields": None,
    }
```

- [ ] **Step 6: Commit**

```bash
git add vibelign/core/docs_visualizer.py vibelign/core/docs_cache.py tests/test_docs_enhance_heuristics.py
git commit -m "feat(docs-visualizer): heuristic_fields를 모든 artifact에 주입"
```

---

### Task 6: TypeScript 타입 확장

**Files:**
- Modify: `vibelign-gui/src/lib/vib.ts:36-65` (DocsVisualArtifact type)

- [ ] **Step 1: 새 interface 추가**

`vibelign-gui/src/lib/vib.ts:36` (`DocsVisualSection` interface 앞) 에 삽입:

```typescript
export interface DocsVisualHeuristicFields {
  tldr_one_liner: string;
  key_rules: string[];
  success_criteria: string[];
  edge_cases: string[];
  components: string[];
  provenance: "heuristic";
  generator: string;
  generated_at: string;
}

export interface DocsVisualAIFields {
  tldr_one_liner: string;
  key_rules: string[];
  success_criteria: string[];
  edge_cases: string[];
  components: string[];
  provenance: "ai_draft";
  model: string;
  provider: string;
  generated_at: string;
  source_hash: string;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
}
```

- [ ] **Step 2: DocsVisualArtifact 에 필드 추가**

`vibelign-gui/src/lib/vib.ts:43-65` 의 `DocsVisualArtifact` 마지막 필드(`warnings?`) 뒤에 추가:

```typescript
  heuristic_fields?: DocsVisualHeuristicFields | null;
  ai_fields?: DocsVisualAIFields | null;
```

- [ ] **Step 3: 타입체크 통과 확인**

```bash
cd vibelign-gui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add vibelign-gui/src/lib/vib.ts
git commit -m "feat(docs-viewer/types): heuristic/ai fields TS 타입 추가"
```

---

### Task 7: VisualSummaryPane 하드코딩 제거 + 조건부 렌더

**Files:**
- Modify: `vibelign-gui/src/components/docs/VisualSummaryPane.tsx`

- [ ] **Step 1: 하드코딩 헬퍼 함수 제거**

`vibelign-gui/src/components/docs/VisualSummaryPane.tsx:87-120` 의 `keyRules`, `successCriteria`, `edgeCases` 함수를 완전히 삭제. `fileRows` 함수(146-153)도 삭제.

- [ ] **Step 2: 새 헬퍼 함수 추가**

삭제된 자리에 다음 삽입:

```typescript
function heuristicRules(artifact: DocsVisualArtifact): string[] {
  const ai = artifact.ai_fields;
  if (ai && ai.key_rules.length > 0) return ai.key_rules;
  return artifact.heuristic_fields?.key_rules ?? [];
}

function heuristicCriteria(artifact: DocsVisualArtifact): string[] {
  const ai = artifact.ai_fields;
  if (ai && ai.success_criteria.length > 0) return ai.success_criteria;
  return artifact.heuristic_fields?.success_criteria ?? [];
}

function heuristicEdges(artifact: DocsVisualArtifact): string[] {
  const ai = artifact.ai_fields;
  if (ai && ai.edge_cases.length > 0) return ai.edge_cases;
  return artifact.heuristic_fields?.edge_cases ?? [];
}

function heuristicComponents(artifact: DocsVisualArtifact): string[] {
  const ai = artifact.ai_fields;
  if (ai && ai.components.length > 0) return ai.components;
  return artifact.heuristic_fields?.components ?? [];
}

function heuristicTldr(artifact: DocsVisualArtifact): string {
  const ai = artifact.ai_fields;
  if (ai && ai.tldr_one_liner) return ai.tldr_one_liner;
  return artifact.heuristic_fields?.tldr_one_liner ?? "";
}

function isAiActive(artifact: DocsVisualArtifact): boolean {
  return !!(artifact.ai_fields && artifact.ai_fields.source_hash === artifact.source_hash);
}
```

- [ ] **Step 3: 기존 Rule 카드(221행) 를 조건부 렌더로 교체**

기존:
```tsx
<Rule>
  <strong>아키텍처 한 줄:</strong> GUI는 markdown 원문을 바로 보여주고...
</Rule>
```

을 다음으로 교체:

```tsx
{heuristicTldr(artifact) ? (
  <Rule>
    <strong>한 줄 요약:</strong> {heuristicTldr(artifact)}
    {isAiActive(artifact) ? <SmallPill bg="#FFF0F0" color="#A33A3A">AI</SmallPill> : null}
  </Rule>
) : null}
```

- [ ] **Step 4: "핵심 실행 규칙" 카드 조건부 + heuristicRules 사용**

`vibelign-gui/src/components/docs/VisualSummaryPane.tsx:251-260` 의 Card 전체를 다음으로 교체:

```tsx
{heuristicRules(artifact).length > 0 ? (
  <Card title={isAiActive(artifact) ? "핵심 규칙 (AI)" : "핵심 규칙"}>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {heuristicRules(artifact).map((rule, idx) => (
        <Rule key={`rule-${idx}`} tone={idx % 2 === 0 ? "#4D9FFF" : "#4DFF91"}>
          {rule}
        </Rule>
      ))}
      {topItems(warnings, 2).map((warning, idx) => (
        <Rule key={`warn-${idx}`} tone="#FFD166"><strong>주의:</strong> {warning}</Rule>
      ))}
    </div>
  </Card>
) : null}
```

- [ ] **Step 5: "검증해야 할 Edge Cases"/"Final Success Criteria" 카드 조건부**

`vibelign-gui/src/components/docs/VisualSummaryPane.tsx:314-321` 을 다음으로 교체:

```tsx
{(heuristicEdges(artifact).length > 0 || heuristicCriteria(artifact).length > 0) ? (
  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
    {heuristicEdges(artifact).length > 0 ? (
      <Card title={isAiActive(artifact) ? "예외 상황 (AI)" : "예외 상황"}>
        <BulletList items={heuristicEdges(artifact)} />
      </Card>
    ) : null}
    {heuristicCriteria(artifact).length > 0 ? (
      <Card title={isAiActive(artifact) ? "성공 기준 (AI)" : "성공 기준"}>
        <BulletList items={heuristicCriteria(artifact)} icon="✅" />
      </Card>
    ) : null}
  </div>
) : null}
```

- [ ] **Step 6: "주요 구성 요소" 카드를 components 기반으로 교체**

`vibelign-gui/src/components/docs/VisualSummaryPane.tsx:291-312` 을 다음으로 교체:

```tsx
{heuristicComponents(artifact).length > 0 ? (
  <Card title={isAiActive(artifact) ? "주요 구성 요소 (AI)" : "주요 구성 요소"}>
    <BulletList items={heuristicComponents(artifact)} />
  </Card>
) : null}
```

- [ ] **Step 7: 타입 체크**

```bash
cd vibelign-gui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add vibelign-gui/src/components/docs/VisualSummaryPane.tsx
git commit -m "refactor(docs-viewer): 하드코딩 메타 제거 → heuristic_fields 기반 렌더"
```

---

### Task 8: E2E 수동 검증 (phase 1 heuristic 완료)

**Files:** 없음 (수동 검증)

- [ ] **Step 1: artifact 재생성**

```bash
cd /Users/topsphinx/Documents/coding/VibeLign
vib docs-build
```

Expected: stdout `docs visual cache 전체 재생성 완료: N개`.

- [ ] **Step 2: tauri dev 재시작**

```bash
cd vibelign-gui && npm run tauri dev
```

(Task 이전 vib_path.rs 수정으로 dev 가 시스템 vib 를 씀 → `docs-build` 명령 인식)

- [ ] **Step 3: DocsViewer 로 진입**
- `docs/superpowers/plans/*.md` 파일 클릭 — 이 문서에는 heuristic_fields 풍부 → 우측 패널 카드가 문서 내용을 반영해야 함
- `docs/wiki/index.md` — 짧은 문서 → 일부 카드 자동 숨김

- [ ] **Step 4: 문서 간 이동 시 내용이 바뀌는지 확인**

각 문서마다 "한 줄 요약"·"핵심 규칙" 등이 **다른 내용**을 보여야 한다. 동일하면 regression.

- [ ] **Step 5: Commit 없음 (수동 검증)**

---

### Task 9: AI enhance 모듈 — LLM 호출 래퍼

**Files:**
- Create: `vibelign/core/docs_ai_enhance.py`
- Create: `tests/test_docs_ai_enhance.py`

- [ ] **Step 1: 실패 테스트 작성 (Anthropic 응답 파싱)**

`tests/test_docs_ai_enhance.py`:

```python
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(path)]
    sys.modules[name] = pkg


_stub("vibelign", ROOT / "vibelign")
_stub("vibelign.core", ROOT / "vibelign" / "core")
_load("vibelign.core.keys_store", ROOT / "vibelign" / "core" / "keys_store.py")
_load("vibelign.core.http_retry", ROOT / "vibelign" / "core" / "http_retry.py")
enhance = _load(
    "vibelign.core.docs_ai_enhance",
    ROOT / "vibelign" / "core" / "docs_ai_enhance.py",
)


class AIEnhanceParsingTest(unittest.TestCase):
    def test_builds_prompt_with_source_text(self):
        prompt = enhance.build_prompt("# Title\n\nbody.")
        self.assertIn("Title", prompt)
        self.assertIn("body.", prompt)
        self.assertIn("tldr_one_liner", prompt)

    def test_parses_valid_anthropic_response(self):
        fake_body = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "tldr_one_liner": "짧은 요약",
                        "key_rules": ["규칙1"],
                        "success_criteria": ["기준1"],
                        "edge_cases": ["예외1"],
                        "components": ["파서 — AST"],
                    }),
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        parsed = enhance.parse_anthropic_response(fake_body)
        self.assertEqual(parsed["fields"]["tldr_one_liner"], "짧은 요약")
        self.assertEqual(parsed["tokens_input"], 100)
        self.assertEqual(parsed["tokens_output"], 50)

    def test_rejects_non_json_content(self):
        fake_body = {"content": [{"type": "text", "text": "not json"}]}
        with self.assertRaises(ValueError):
            enhance.parse_anthropic_response(fake_body)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_docs_ai_enhance.py -v
```

Expected: FAIL — 모듈 없음.

- [ ] **Step 3: docs_ai_enhance.py 구현**

`vibelign/core/docs_ai_enhance.py`:

```python
# === ANCHOR: DOCS_AI_ENHANCE_START ===
"""단일 markdown 문서에 대해 LLM 을 호출해 구조화된 요약 필드를 돌려준다.

Anthropic Messages API 기반. OpenAI/Gemini 어댑터는 후속 과제.
네트워크 호출은 vibelign.core.http_retry 를 통해 재시도한다.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from . import http_retry as _HTTP_RETRY
from . import keys_store as _KEYS


PROMPT_TEMPLATE = """You are a precise documentation summarizer for a developer tool.

Read the markdown document below and return a JSON object with these fields:
- tldr_one_liner (string, ≤ 180 chars): one-sentence summary in the document's language
- key_rules (string[], max 6): explicit rules or principles stated in the doc
- success_criteria (string[], max 5): how the reader knows the goal is met
- edge_cases (string[], max 5): failure modes, exceptions, pitfalls
- components (string[], max 6): "name — one-line role" for each major component discussed

Rules:
- Return JSON only — no prose, no markdown fences
- Use the language of the source document (Korean/English as-is)
- If a field has no evidence in the doc, return empty string or empty array — don't fabricate
- Quote or paraphrase from the doc; don't inject generic statements

=== DOCUMENT START ===
{source_text}
=== DOCUMENT END ===
"""


# === ANCHOR: DOCS_AI_ENHANCE_BUILD_PROMPT_START ===
def build_prompt(source_text: str) -> str:
    return PROMPT_TEMPLATE.format(source_text=source_text)
# === ANCHOR: DOCS_AI_ENHANCE_BUILD_PROMPT_END ===


# === ANCHOR: DOCS_AI_ENHANCE_PARSE_ANTHROPIC_RESPONSE_START ===
def parse_anthropic_response(body: dict[str, Any]) -> dict[str, Any]:
    blocks = body.get("content") or []
    text = next(
        (b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"),
        "",
    ).strip()
    if not text:
        raise ValueError("AI 응답이 비어있습니다")
    try:
        fields = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI 응답 JSON 파싱 실패: {exc}") from exc
    usage = body.get("usage") or {}
    return {
        "fields": {
            "tldr_one_liner": str(fields.get("tldr_one_liner", ""))[:180],
            "key_rules": [str(x) for x in (fields.get("key_rules") or [])][:6],
            "success_criteria": [str(x) for x in (fields.get("success_criteria") or [])][:5],
            "edge_cases": [str(x) for x in (fields.get("edge_cases") or [])][:5],
            "components": [str(x) for x in (fields.get("components") or [])][:6],
        },
        "tokens_input": int(usage.get("input_tokens", 0)),
        "tokens_output": int(usage.get("output_tokens", 0)),
    }
# === ANCHOR: DOCS_AI_ENHANCE_PARSE_ANTHROPIC_RESPONSE_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CALL_ANTHROPIC_START ===
def call_anthropic(source_text: str, *, model: str = "claude-sonnet-4-5") -> dict[str, Any]:
    api_key = _KEYS.get_key("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 가 환경변수/키스토어에 없습니다")

    prompt = build_prompt(source_text)
    payload = json.dumps({
        "model": model,
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    raw = _HTTP_RETRY.urlopen_read_with_retry(req, timeout=60.0)
    body = json.loads(raw.decode("utf-8"))
    parsed = parse_anthropic_response(body)
    parsed["model"] = model
    parsed["provider"] = "anthropic"
    # pricing rough estimate (claude sonnet 4.5: $3/MTok in, $15/MTok out)
    parsed["cost_usd"] = round(
        (parsed["tokens_input"] * 3 + parsed["tokens_output"] * 15) / 1_000_000, 6
    )
    return parsed
# === ANCHOR: DOCS_AI_ENHANCE_CALL_ANTHROPIC_END ===
# === ANCHOR: DOCS_AI_ENHANCE_END ===
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_docs_ai_enhance.py -v
```

Expected: PASS (3/3). 네트워크 없는 테스트이므로 CI에서도 통과.

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/docs_ai_enhance.py tests/test_docs_ai_enhance.py
git commit -m "feat(docs-ai-enhance): Anthropic API 기반 문서 요약 래퍼"
```

---

### Task 10: `vib docs-enhance <path>` 커맨드

**Files:**
- Modify: `vibelign/commands/vib_docs_build_cmd.py` (run_vib_docs_enhance 추가)
- Modify: `vibelign/cli/cli_core_commands.py` (subcommand 등록)
- Modify: `vibelign/cli/vib_cli.py:81` (metavar 갱신)
- Modify: `vibelign/cli/cli_base.py` (help 한 줄 추가)

- [ ] **Step 1: 기존 cli_core_commands.py 의 docs-build 블록 찾기**

```bash
grep -n "docs-build" vibelign/cli/cli_core_commands.py
```

`cli_core_commands.py:160-200` 근처 docs-build 등록부 확인.

- [ ] **Step 2: run_vib_docs_enhance 함수 추가**

`vibelign/commands/vib_docs_build_cmd.py:175` (`run_vib_docs_build` 뒤) 에 삽입:

```python
# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_ENHANCE_START ===
def run_vib_docs_enhance(args: argparse.Namespace) -> None:
    from ..core import docs_ai_enhance as _AI_ENHANCE

    root = _resolve_root()
    target = getattr(args, "path", None)
    if not isinstance(target, str) or not target.strip():
        print("docs-enhance 는 문서 경로가 필요해요 (예: vib docs-enhance docs/wiki/index.md)", file=sys.stderr)
        raise SystemExit(2)

    relative_path = target.replace("\\", "/")
    meta = MetaPaths(root)
    artifact_path = meta.docs_visual_path(relative_path)
    if not artifact_path.exists():
        print(f"artifact 가 없어요. 먼저 vib docs-build '{relative_path}' 를 실행하세요.", file=sys.stderr)
        raise SystemExit(3)

    source_path = (root / relative_path).resolve()
    if not source_path.is_file():
        print(f"source markdown 이 없어요: {relative_path}", file=sys.stderr)
        raise SystemExit(3)

    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"source markdown 을 읽을 수 없어요: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    try:
        result = _AI_ENHANCE.call_anthropic(source_text)
    except Exception as exc:
        print(f"AI 호출 실패: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc

    existing = json.loads(artifact_path.read_text(encoding="utf-8"))
    source_hash = existing.get("source_hash", "")
    existing["ai_fields"] = {
        **result["fields"],
        "provenance": "ai_draft",
        "model": result["model"],
        "provider": result["provider"],
        "generated_at": _DOCS_VISUALIZER.current_generated_at(),
        "source_hash": source_hash,
        "tokens_input": result["tokens_input"],
        "tokens_output": result["tokens_output"],
        "cost_usd": result["cost_usd"],
    }
    _atomic_write_text(
        artifact_path, json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
    )
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "path": relative_path, "ai_fields": existing["ai_fields"]}, ensure_ascii=False))
    else:
        print(
            f"AI 요약 완료: {relative_path} "
            f"(in={result['tokens_input']} out={result['tokens_output']} ${result['cost_usd']:.4f})"
        )
# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_ENHANCE_END ===
```

- [ ] **Step 3: CLI subcommand 등록**

`vibelign/cli/cli_core_commands.py` 에서 docs-build 등록부 찾아, 비슷한 블록을 docs-enhance 로 추가:

```python
register_lazy(
    "docs-enhance",
    help="AI 로 현재 문서의 요약 필드를 생성해요 (ANTHROPIC_API_KEY 필요)",
    description=(
        "사용 예:\n"
        "  vib docs-enhance docs/wiki/index.md\n"
        "  vib docs-enhance PROJECT_CONTEXT.md --json"
    ),
    args=[
        {"name": "path", "nargs": "?", "help": "enhance 대상 markdown 경로"},
        {"name": "--json", "action": "store_true", "help": "JSON 출력"},
    ],
    func=lazy_command("vibelign.commands.vib_docs_build_cmd", "run_vib_docs_enhance"),
)
```

(정확한 `register_lazy`/`lazy_command` 시그니처는 파일 내 docs-build 등록 블록을 복사해 맞춘다.)

- [ ] **Step 4: metavar/help 문자열 갱신**

`vibelign/cli/vib_cli.py:81` — `docs-index` 뒤에 `docs-enhance` 삽입.
`vibelign/cli/cli_base.py:118` 근처 — `docs-build` 설명 뒤에 `docs-enhance  AI 로 문서 요약을 보강해요` 한 줄 추가.

- [ ] **Step 5: 수동 검증**

```bash
vib --help | grep docs-enhance
```

Expected: 명령어 리스트에 `docs-enhance` 등장.

```bash
vib docs-enhance --help
```

Expected: 사용법 출력, path 인자 설명.

- [ ] **Step 6: 통합 테스트 (API 키 없이 실패 경로)**

```bash
ANTHROPIC_API_KEY= vib docs-enhance docs/wiki/index.md 2>&1
```

Expected: exit code ≠ 0, stderr 에 "ANTHROPIC_API_KEY" 문자열.

- [ ] **Step 7: Commit**

```bash
git add vibelign/commands/vib_docs_build_cmd.py vibelign/cli/cli_core_commands.py vibelign/cli/vib_cli.py vibelign/cli/cli_base.py
git commit -m "feat(cli): vib docs-enhance 커맨드 — AI 로 문서 요약 생성"
```

---

### Task 11: Tauri command `enhance_doc_with_ai`

**Files:**
- Modify: `vibelign-gui/src-tauri/src/lib.rs`

- [ ] **Step 1: 기존 run_vib_docs_index 함수 위치 확인**

```bash
grep -n "run_vib_docs_index\|read_docs_visual\|enhance_doc" vibelign-gui/src-tauri/src/lib.rs
```

- [ ] **Step 2: 새 command 추가**

`vibelign-gui/src-tauri/src/lib.rs` 의 `read_docs_visual` 함수 아래에 삽입:

```rust
#[tauri::command]
async fn enhance_doc_with_ai(
    root: String,
    path: PathBuf,
    api_key: String,
) -> Result<String, String> {
    let (_resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let vib = vib_path::find_runtime_vib()
        .ok_or_else(|| "vib 실행 파일을 찾을 수 없습니다".to_string())?;
    let mut command = std::process::Command::new(&vib);
    command
        .arg("docs-enhance")
        .arg(&relative_path)
        .arg("--json")
        .env("VIBELIGN_PROJECT_ROOT", &root)
        .env("ANTHROPIC_API_KEY", &api_key)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");
    vib_path::hide_console(&mut command);
    let output = command
        .output()
        .map_err(|e| format!("vib docs-enhance 실행 실패: {e}"))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("docs-enhance 실패: {}", err.trim()));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}
```

주의: `vib_path::hide_console` 는 `pub` 으로 노출돼 있어야 함. 현재 `pub(crate)` 인지 확인 후 필요 시 `pub fn hide_console` 로 바꾸거나 helper wrapper 추가.

- [ ] **Step 3: invoke_handler 에 등록**

`vibelign-gui/src-tauri/src/lib.rs` 의 `tauri::generate_handler![...]` 매크로 안에 `enhance_doc_with_ai,` 추가.

- [ ] **Step 4: Windows 주의사항 확인 (수동)**

`command.env("PYTHONUTF8", "1")` 와 `hide_console(&mut command)` 가 모두 Windows 에서 한글 깨짐·콘솔 팝업 방지. 기존 `run_vib` 와 동일 패턴.

- [ ] **Step 5: Rust 빌드**

```bash
cd vibelign-gui/src-tauri && cargo check
```

Expected: compiles cleanly.

- [ ] **Step 6: Commit**

```bash
git add vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(tauri): enhance_doc_with_ai 커맨드 — vib docs-enhance subprocess 호출"
```

---

### Task 12: TS bridge `enhanceDocWithAi`

**Files:**
- Modify: `vibelign-gui/src/lib/vib.ts`

- [ ] **Step 1: bridge 함수 추가**

`vibelign-gui/src/lib/vib.ts:87` (`readDocsVisual` 다음) 에 삽입:

```typescript
export interface EnhanceDocResult {
  ok: boolean;
  path: string;
  ai_fields: DocsVisualAIFields;
}

export async function enhanceDocWithAi(
  root: string,
  path: string,
  apiKey: string,
): Promise<EnhanceDocResult> {
  const raw = await invoke<string>("enhance_doc_with_ai", { root, path, apiKey });
  return JSON.parse(raw) as EnhanceDocResult;
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd vibelign-gui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add vibelign-gui/src/lib/vib.ts
git commit -m "feat(bridge): enhanceDocWithAi TS 래퍼"
```

---

### Task 13: AiEnhanceButton 컴포넌트 + consent 모달

**Files:**
- Create: `vibelign-gui/src/components/docs/AiEnhanceButton.tsx`

- [ ] **Step 1: 새 컴포넌트 파일**

`vibelign-gui/src/components/docs/AiEnhanceButton.tsx`:

```tsx
import { useState } from "react";
import { enhanceDocWithAi, loadProviderApiKeys } from "../../lib/vib";

const CONSENT_KEY = "vibelign.docs.ai.consent";

export interface AiEnhanceButtonProps {
  root: string;
  relativePath: string;
  onDone: () => void;
  sourceHash: string;
  isAiActive: boolean;
  lastTokensInput?: number;
  lastTokensOutput?: number;
  lastCostUsd?: number;
}

export default function AiEnhanceButton({
  root,
  relativePath,
  onDone,
  isAiActive,
  lastTokensInput,
  lastTokensOutput,
  lastCostUsd,
}: AiEnhanceButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(false);

  const proceed = async () => {
    setBusy(true);
    setError(null);
    try {
      const keys = await loadProviderApiKeys();
      const key = keys["ANTHROPIC"] || "";
      if (!key) {
        setError("설정 > API 키에서 Anthropic 키를 먼저 등록해주세요");
        return;
      }
      await enhanceDocWithAi(root, relativePath, key);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleClick = () => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (consent === "accepted") {
      proceed();
      return;
    }
    setShowConsent(true);
  };

  const handleAccept = (remember: boolean) => {
    if (remember) localStorage.setItem(CONSENT_KEY, "accepted");
    setShowConsent(false);
    proceed();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <button
        className="card"
        onClick={handleClick}
        disabled={busy}
        style={{
          padding: "8px 14px",
          background: isAiActive ? "#FFF0F0" : "#E8F5FF",
          fontWeight: 800,
          fontSize: 12,
          cursor: busy ? "wait" : "pointer",
        }}
      >
        {busy ? "AI 요약 생성 중..." : isAiActive ? "AI 요약 새로 생성" : "AI 로 요약하기"}
      </button>
      {error ? (
        <div style={{ fontSize: 11, color: "#A33A3A" }}>{error}</div>
      ) : null}
      {isAiActive && typeof lastCostUsd === "number" ? (
        <div style={{ fontSize: 10, color: "#777" }}>
          last AI: in={lastTokensInput ?? 0} out={lastTokensOutput ?? 0} · ${lastCostUsd.toFixed(4)}
        </div>
      ) : null}
      {showConsent ? (
        <div
          role="dialog"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <div
            className="card"
            style={{ padding: 24, maxWidth: 420, background: "#FBF8EE" }}
          >
            <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 12 }}>
              AI 요약을 사용하시겠어요?
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 16 }}>
              이 문서 내용이 Anthropic API (외부) 로 전송됩니다. 민감한 문서는
              진행 전에 한 번 더 확인해주세요.
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowConsent(false)} style={{ padding: "6px 12px" }}>
                취소
              </button>
              <button onClick={() => handleAccept(false)} style={{ padding: "6px 12px" }}>
                이번만 진행
              </button>
              <button
                onClick={() => handleAccept(true)}
                style={{ padding: "6px 12px", background: "#4D9FFF", color: "#fff" }}
              >
                항상 허용
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd vibelign-gui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add vibelign-gui/src/components/docs/AiEnhanceButton.tsx
git commit -m "feat(docs-viewer): AiEnhanceButton 컴포넌트 + consent 모달"
```

---

### Task 14: VisualSummaryPane 에 버튼 배치 + DocsViewer 연동

**Files:**
- Modify: `vibelign-gui/src/components/docs/VisualSummaryPane.tsx`
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`

- [ ] **Step 1: VisualSummaryPane props 확장**

`vibelign-gui/src/components/docs/VisualSummaryPane.tsx:6-10` 의 interface 를 다음으로 교체:

```typescript
interface VisualSummaryPaneProps {
  artifact: DocsVisualArtifact;
  trustState: DocsTrustState;
  onPhaseSelect?: (sectionId: string) => void;
  projectRoot: string;
  relativePath: string;
  onArtifactRefresh: () => void;
}
```

- [ ] **Step 2: 첫 카드("Docs Viewer Execution Summary") 에 버튼 삽입**

첫 Card 의 pills 영역(`210-215번 라인`) 바로 뒤, title 선언(`216번 라인`) 앞에 AiEnhanceButton 삽입:

```tsx
import AiEnhanceButton from "./AiEnhanceButton";

// ...

<AiEnhanceButton
  root={projectRoot}
  relativePath={relativePath}
  onDone={onArtifactRefresh}
  sourceHash={artifact.source_hash}
  isAiActive={isAiActive(artifact)}
  lastTokensInput={artifact.ai_fields?.tokens_input}
  lastTokensOutput={artifact.ai_fields?.tokens_output}
  lastCostUsd={artifact.ai_fields?.cost_usd}
/>
```

(Card 내부 최상단, pills 아래 title 위 자연스러운 위치)

- [ ] **Step 3: DocsViewer 에서 props 전달**

`vibelign-gui/src/pages/DocsViewer.tsx:404` 의 `<VisualSummaryPane ... />` 호출을 다음으로 교체:

```tsx
<VisualSummaryPane
  artifact={visual?.artifact}
  trustState={trustState}
  onPhaseSelect={handlePhaseSelect}
  projectRoot={projectDir}
  relativePath={selectedPath}
  onArtifactRefresh={() => setSelectedPath((p) => p)}
/>
```

주의: `setSelectedPath((p) => p)` 는 동일 경로로 set 하지만 DocsViewer 의 useEffect 의존성에서 다시 `readDocsVisual` 트리거되도록 별도 refresh counter 추가 필요. 다음과 같이 보완:

```tsx
const [refreshTick, setRefreshTick] = useState(0);
// useEffect(() => {...}, [projectDir, selectedPath, refreshTick]);
// onArtifactRefresh={() => setRefreshTick((t) => t + 1)}
```

정확한 useEffect 의존성 배열은 `vibelign-gui/src/pages/DocsViewer.tsx` 의 `readDocsVisual` useEffect 를 찾아 `refreshTick` 을 deps 에 추가.

- [ ] **Step 4: 타입 체크**

```bash
cd vibelign-gui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add vibelign-gui/src/components/docs/VisualSummaryPane.tsx vibelign-gui/src/pages/DocsViewer.tsx
git commit -m "feat(docs-viewer): AI 요약 버튼 배치 + artifact refresh 연동"
```

---

### Task 15: Settings 에 consent 초기화 토글

**Files:**
- Modify: `vibelign-gui/src/pages/Settings.tsx`

- [ ] **Step 1: Settings.tsx 의 기존 카드 구조 파악**

```bash
grep -n "Card\|section\|import" vibelign-gui/src/pages/Settings.tsx | head -20
```

- [ ] **Step 2: consent 상태 토글 카드 추가**

Settings.tsx 의 마지막 설정 카드 뒤에 삽입:

```tsx
const CONSENT_KEY = "vibelign.docs.ai.consent";

// 컴포넌트 내부 state:
const [consentAccepted, setConsentAccepted] = useState<boolean>(
  () => localStorage.getItem(CONSENT_KEY) === "accepted"
);

// 카드 JSX:
<Card title="AI 요약 동의 상태">
  <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 10 }}>
    DocsViewer 에서 AI 요약 버튼을 누를 때 문서 내용이 외부 API 로 전송됩니다.
    {consentAccepted ? " 항상 허용 상태입니다." : " 매번 확인 모달이 뜹니다."}
  </div>
  {consentAccepted ? (
    <button
      onClick={() => {
        localStorage.removeItem(CONSENT_KEY);
        setConsentAccepted(false);
      }}
    >
      동의 취소 (다시 물어보기)
    </button>
  ) : null}
</Card>
```

(Card 컴포넌트는 Settings.tsx 내 기존 UI 패턴을 따름)

- [ ] **Step 3: 타입 체크**

```bash
cd vibelign-gui && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add vibelign-gui/src/pages/Settings.tsx
git commit -m "feat(settings): AI 요약 동의 상태 토글/초기화"
```

---

### Task 16: E2E 수동 검증 + Windows 체크 (phase 2 AI 완료)

**Files:** 없음 (수동 검증)

- [ ] **Step 1: Anthropic 키 등록**

Settings → API 키 탭에서 ANTHROPIC 키 입력 저장.

- [ ] **Step 2: DocsViewer 에서 임의 문서 선택 → "AI 로 요약하기" 클릭**

Expected:
- consent 모달 뜸
- "항상 허용" 클릭 → API 호출 → 몇 초 후 카드 제목이 "핵심 규칙 (AI)" 로 변경, 내용 AI 생성본
- "last AI: in=X out=Y · $0.00XX" fine-print 노출

- [ ] **Step 3: 같은 문서에서 "AI 요약 새로 생성" 재클릭**

Expected: consent 생략, 새로운 ai_fields 로 갱신.

- [ ] **Step 4: 다른 문서 이동 후 복귀**

Expected: ai_fields 는 artifact JSON 에 영속화돼 그대로 보임 (source_hash 일치하는 동안).

- [ ] **Step 5: 원본 문서 수정 → source_hash 불일치**

Expected: DocsViewer 상단에 STALE pill (기존 로직), AI 카드 제목은 계속 (AI) 인 상태 — 사용자가 재생성 유도.

- [ ] **Step 6: 네트워크 차단 후 AI 버튼 클릭**

Expected: 버튼 옆 error 메시지 노출, heuristic 카드는 그대로 유지 (regression 없음).

- [ ] **Step 7: Windows 체크 (VM 또는 회사 컴)**

Expected:
- Windows 에서 `vib docs-enhance` 콘솔 팝업 없이 실행
- 한글 깨짐 없음 (PYTHONUTF8 덕분)
- artifact JSON 의 atomic write 성공 (`_atomic_write_text` 의 Windows retry)
- 우측 패널 AI 카드 한글 정상

- [ ] **Step 8: Commit 없음 (수동 검증)**

---

### Task 17: 최종 통합 테스트 + 회귀

**Files:** 없음

- [ ] **Step 1: 전체 Python 테스트**

```bash
python -m pytest tests/ -v -x
```

Expected: 모든 테스트 PASS. 특히:
- test_docs_visualizer.py (기존)
- test_docs_enhance_heuristics.py (신규)
- test_docs_ai_enhance.py (신규)
- test_docs_build_cmd.py (기존 + enhance 케이스)

- [ ] **Step 2: Rust + Frontend 검증**

```bash
cd vibelign-gui/src-tauri && cargo check --release
cd .. && npx tsc --noEmit
```

Expected: 둘 다 통과.

- [ ] **Step 3: `vib --help` 확인**

Expected: `docs-enhance` subcommand 노출.

- [ ] **Step 4: Commit (필요 시 fix-up 커밋)**

없으면 skip.

---

## Self-Review 체크리스트

**1. Spec coverage**: 결정된 7개 사항(접근 A+B, 스코프, provenance 재사용, source_hash 캐시, consent, 비용 표시, 실패 폴백) 모두 Task 에 매핑됨 ✅. Windows 호환은 Task 11, 16 에서 확인.

**2. Placeholder scan**: 모든 Step 에 실제 코드/명령 포함. "적절한 예외 처리 추가" 같은 추상 문구 없음.

**3. Type consistency**:
- Python: `HeuristicEnhancedFields`, `AIEnhancedFields` — 두 dataclass 시그니처가 Task 1 에서 정의되고 Task 9 (파싱), Task 10 (저장) 에서 동일 필드명 사용 ✅
- TS: `DocsVisualHeuristicFields`, `DocsVisualAIFields` — Task 6 에서 정의, Task 7/12/13/14 에서 동일 속성 참조 ✅
- AI 호출 반환 형태: `{fields, tokens_input, tokens_output, model, provider, cost_usd}` — Task 9/10 일관 ✅

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-docsviewer-per-doc-enhancement.md`.
