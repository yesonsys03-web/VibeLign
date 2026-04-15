# Heuristic Mermaid Auto-Generation Execution Plan

> **Working rule:** markdown is still the only source of truth. Auto-generated diagrams are derived artifacts and must never be presented as authored truth.

**Goal:** authored Mermaid가 없는 markdown 문서에서도 구조를 이해할 수 있는 heuristic Mermaid diagram을 안정적으로 생성하고, GUI에서 provenance / confidence / freshness를 명확히 드러낸다.

**Architecture in one line:** `docs_visualizer`는 authored Mermaid를 우선 추출하고, 없을 때만 deterministic heuristic diagram 하나를 생성하며, GUI는 hash-bound artifact를 provenance label과 함께 렌더한다.

**Tech Stack:** Python, TypeScript, React, Mermaid, existing docs visual cache pipeline

---

## Non-Goals (Do Not Expand During Initial Implementation)

- [ ] always-on AI diagram generation
- [ ] authored Mermaid를 자동 생성 결과로 덮어쓰기
- [ ] diagram을 source of truth처럼 직접 편집하는 기능
- [ ] 여러 heuristic diagram을 한 문서에 과도하게 생성하는 기능
- [ ] semantic dependency graph를 완벽히 추론하는 기능

---

## Execution Rules

- [ ] **초기 릴리즈는 `step_flow`, `heading_mindmap`, `component_flow` 3종만 실제 생성한다. `decision_flow` 는 스펙에 존재하나 candidate 생성기가 `None` 을 반환하고 다음 후보로 fallback한다. 즉 v1에서 decision signal이 탐지되더라도 실제 emitted diagram은 fallback 후보 결과 또는 no-diagram이다.**
- [ ] authored diagram 인정 조건: source 가 non-empty 이고 Mermaid 선두 keyword(`flowchart|graph|mindmap|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|pie|gantt|gitGraph|timeline`) 로 시작. 조건 불충족 authored block 은 drop 후 heuristic fallback 실행. v1의 invalid authored 판정은 empty/keyword mismatch 기준이며 Mermaid 전체 parse validation을 요구하지 않는다
- [ ] ordered step 연속성은 동일 list block scope 내에서 1씩 증가하는 경우에만 인정한다
- [ ] doc kind hint 키워드는 `DOC_KIND_HINTS` 단일 dict 로 관리한다 (signal / scoring 이 같은 source 를 공유)
- [ ] authored Mermaid가 있으면 heuristic generation을 실행하지 않는다
- [ ] heuristic diagram은 최대 1개만 생성한다
- [ ] persisted diagram의 `confidence` 값은 `high | medium`만 사용한다. low-confidence는 diagram 미생성 + artifact root warning으로 처리한다
- [ ] provenance는 `authored | heuristic | ai_draft` 중 하나로 명시한다
- [ ] heuristic / ai_draft는 authored처럼 보이지 않게 UI 라벨을 강제한다
- [ ] freshness / stale 판단은 기존 `source_hash` 기반 계약을 유지한다
- [ ] 기존 docs viewer의 Cross-Platform Rules (path normalize, BOM strip, newline normalize, UTF-8, cache path 정책)를 그대로 상속한다
- [ ] heuristic parsing은 normalized markdown text만 사용하고 raw bytes / OS-native line ending을 직접 해석하지 않는다
- [ ] same input → same output이 유지되어야 한다
- [ ] very long doc에서는 현재 partial-disable 정책을 깨지 않는다
- [ ] failure는 항상 `markdown-only` 또는 기존 fallback으로 degrade 한다

---

## Edge Cases That Must Be Verified

- [ ] heading은 많지만 관계 신호가 약한 문서에서 억지 diagram 생성 없음
- [ ] ordered list와 heading이 함께 있을 때 candidate tie-break가 deterministic함
- [ ] file list가 dependency graph처럼 오해되지 않도록 label/warning이 표시됨
- [ ] authored Mermaid가 있는 문서에서 heuristic candidate가 숨겨짐
- [ ] stale artifact에서도 provenance는 유지되지만 synced처럼 보이지 않음
- [ ] huge doc에서 heuristic diagram이 무한정 커지지 않음
- [ ] README / guide / decision / component 문서가 각각 의도한 diagram type으로 분류되며, README/overview는 quick-start step이 있어도 기본적으로 `heading_mindmap`으로 유지됨
- [ ] Windows path (`C:\foo\bar.py`, `docs\guide\README.md`)가 component signal로 정상 인식됨
- [ ] BOM/CRLF markdown이 macOS/LF 문서와 동일한 heuristic 결과를 만든다
- [ ] path-like text는 display-only이며 cache key / node identity로 쓰이지 않는다
- [ ] fenced code block / link destination / shell command example 안의 path는 component signal에서 제외된다
- [ ] 빈 authored mermaid block / 선두 keyword 미매칭 block 은 drop되고 heuristic fallback이 동작한다
- [ ] `1. a / (heading) / 2. b / 3. c` 처럼 heading/code block 으로 끊긴 ordered list 는 step sequence 로 인정되지 않는다
- [ ] nested ordered list (indent 다른 `1.`) 는 최상위 sequence 에 포함되지 않는다
- [ ] H1 이 없는 문서에서 `heading_mindmap` root label 이 Mermaid parse error 를 만들지 않는다 (fallback: 파일 basename 또는 `"Untitled"`)
- [ ] step 수가 cap(8) 초과할 때 diagram 에 `… N more` 노드 또는 warning 으로 truncation 이 표시된다
- [ ] `heading_mindmap` 은 H2 까지만 사용 (H3 이하 제외) — determinism 유지
- [ ] node id 는 항상 순번 기반, 중복 label 이 있어도 id 충돌이 발생하지 않는다
- [ ] authored block 이 empty/keyword mismatch 로 invalid 한 경우 heuristic fallback 으로 전환되고 해당 사실이 warning 에 기록된다
- [ ] stale + heuristic + component summary warning 이 동시에 떠도 viewer 가 시각적으로 구분 가능하다
- [ ] narrow-layout (DocsViewer 좁은 폭) 에서 provenance/confidence/summary 뱃지가 overflow 없이 렌더된다
- [ ] legacy artifact 에 `provenance` 필드가 없으면 `authored` 로 해석된다
- [ ] `docs-build` 의 stale 판정에 generator version mismatch 조건이 포함된다
- [ ] markdown table 의 escaped pipe (`\|`) 가 셀 구분자로 오인되지 않는다

---

## Main Files To Touch

| 파일 | 역할 | 변경 |
|------|------|------|
| `vibelign/core/docs_visualizer.py` | signal extraction / candidate scoring / heuristic Mermaid source 생성 | Modify |
| `vibelign/core/docs_cache.py` | diagram schema example / contract field 확장 | Modify |
| `vibelign-gui/src/lib/vib.ts` | diagram block TypeScript 타입 확장 | Modify |
| `vibelign-gui/src/components/docs/VisualSummaryPane.tsx` | provenance / confidence label 렌더 | Modify |
| `tests/test_docs_visualizer.py` | heuristic generator deterministic tests | Modify |
| `tests/test_docs_build_cmd.py` | schema write-through regression if needed | Modify (optional) |

---

## Global Completion Tracker

- [ ] Phase 1 — Diagram Schema Extension
- [ ] Phase 2 — Signal Extraction Helpers
- [ ] Phase 3 — Candidate Builders
- [ ] Phase 4 — Candidate Selection and Confidence Rules
- [ ] Phase 5 — Visualizer Integration
- [ ] Phase 6 — GUI Provenance Rendering
- [ ] Phase 7 — Test Coverage
- [ ] Phase 8 — Verification

---

## Phase 1 — Diagram Schema Extension

**Target outcome:** heuristic diagram을 표현할 수 있는 artifact contract가 생긴다.

**Files**
- Modify: `vibelign/core/docs_cache.py`
- Modify: `vibelign-gui/src/lib/vib.ts`

**Implementation checklist**
- [ ] `diagram_blocks` example/schema에 `provenance`, `generator`, `confidence`, `warnings` 추가
- [ ] artifact root `warnings` 와 `diagram_blocks[].warnings` 의 책임을 분리 문서화
- [ ] artifact root `warnings` 필드는 optional (기존 authored-only artifact에 없으면 `[]`로 해석) 로 정의
- [ ] `generator` 필드는 `name-vN` 형태로 정의하고, 버전 bump 시 기존 artifact가 schema-mismatch(stale) 처리되도록 문서화
- [ ] 기존 authored artifact를 깨지 않도록 optional compatibility 검토
- [ ] TypeScript `DocsVisualArtifact` type에 신규 필드 반영

**Validation**
- [ ] schema example이 heuristic artifact를 표현 가능
- [ ] 기존 authored-only artifact도 GUI에서 읽힌다

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`
- [ ] `npm run build`

**Completion gate**
- [ ] Python/Rust/TS 브리지 중 diagram field mismatch가 없다
- [ ] old artifact를 hard-break하지 않는다

---

## Phase 2 — Signal Extraction Helpers

**Target outcome:** markdown에서 heuristic 판단용 신호를 안정적으로 추출한다.

**Files**
- Modify: `vibelign/core/docs_visualizer.py`

**Implementation checklist**
- [ ] ordered step regex helper 추가
- [ ] ordered step 은 **동일 list block scope 내에서 1씩 증가 + 3개 이상** 조건으로만 step sequence 로 인정 (일반 ordered list / cross-heading / nested indent 오탐 방지)
- [ ] checklist(`- [ ]`, `- [x]`) helper 추가 → `action_items` 신호를 signal dataclass 에 채움
- [ ] decision line detection helper 추가
- [ ] file-like item detection helper 추가 (Windows backslash path / drive-letter path 포함)
- [ ] fenced code block / link destination / shell command example 안의 path는 signal 대상에서 제외
- [ ] markdown table row parsing helper 추가 (escaped pipe `\|` 처리 포함)
- [ ] doc kind hint scoring helper 는 `DOC_KIND_HINTS` 단일 dict 를 참조하고 소문자 substring 매칭 사용
- [ ] signal dataclass 또는 동등 구조 정의 (`action_items` 포함)
- [ ] signal helper는 normalized text만 입력으로 사용

**Validation**
- [ ] README / step / decision / component fixture에서 신호 추출이 기대대로 동작
- [ ] noise text가 과도하게 step/decision으로 오인되지 않음
- [ ] CRLF / BOM 원본이 signal dataclass 레벨에 도달하기 **전에** normalize됨을 단위 테스트로 확인 (regex 의 `$` 앵커가 CRLF 잔여에 오동작하지 않아야 함)

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`

**Completion gate**
- [ ] signal extraction이 deterministic하다
- [ ] helper들이 기존 authored Mermaid extraction 경로를 건드리지 않는다

---

## Phase 3 — Candidate Builders

**Target outcome:** 4종 heuristic diagram source를 Mermaid 문자열로 생성할 수 있다.

**Files**
- Modify: `vibelign/core/docs_visualizer.py`

**Implementation checklist**
- [ ] `step_flow` renderer 추가 (cap 초과 시 마지막 노드 뒤 `Sn["… N more steps"]` 노드 추가 + `auto_diagram_truncated` warning)
- [ ] `decision_flow` renderer 는 **초기 릴리즈에서 `None` 반환** (후속 릴리즈로 유예)
- [ ] `heading_mindmap` renderer 추가 (**H2 까지만 사용**, H3 이하 제외)
- [ ] `heading_mindmap` root label fallback: title 이 없거나 공백이면 파일 basename, 그것도 없으면 `"Untitled"`
- [ ] `component_flow` renderer 추가 (**edge 없이 `subgraph` 그룹핑만**, dependency 오해 방지)
- [ ] 모든 renderer 의 node id 는 순번 기반 (`S1`/`C1`/…) 이며 label 에서 파생하지 않는다 (중복 label 에서도 충돌 없음)
- [ ] Mermaid label safe-normalize helper 추가 (`| # ; :` 는 공백 치환, `\\` 는 `/` 로 치환, `\r` 은 제거 — backslash는 정보 보존)
- [ ] node/edge cap을 두어 diagram size를 제한

**Validation**
- [ ] 생성된 Mermaid 문자열이 기본 syntax를 만족한다
- [ ] 긴 label이 normalize/truncate 된다
- [ ] Windows path/backslash가 label에 들어가도 Mermaid source가 깨지지 않으며, backslash 는 `/` 로 보존되어 표시된다 (`C:\foo\bar.py` → `C:/foo/bar.py`)
- [ ] component flow는 summary warning을 함께 남길 수 있다

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`

**Completion gate**
- [ ] 각 candidate는 같은 입력에서 같은 Mermaid source를 생성한다
- [ ] diagram size cap이 존재한다

---

## Phase 4 — Candidate Selection and Confidence Rules

**Target outcome:** 여러 후보 중 하나만 deterministic하게 선택된다.

**Files**
- Modify: `vibelign/core/docs_visualizer.py`

**Implementation checklist**
- [ ] score guide 구현
- [ ] tie-break 순서 구현: `step_flow` > `decision_flow` > `component_flow` > `heading_mindmap`
- [ ] 단, **파일 수준 README/Overview hint** (파일명 == `README.md` 대소문자 무관, 또는 H1이 `README`/`Overview`/`소개`/`개요` 중 하나와 **정확 일치**) 가 있으면 `heading_mindmap` 을 기본 선택으로 고정. 본문 단어 매칭으로는 override하지 않는다
- [ ] `score < 4` → 생성 skip (confidence 값이 아니라 skip 사건으로 처리)
- [ ] artifact 에 기록되는 `confidence` 는 `high(≥6) | medium(4~5)` 두 값만 사용
- [ ] `auto_diagram_skipped: low confidence (score<4)` artifact root warning 추가
- [ ] `auto_diagram_truncated` warning 추가

**Validation**
- [ ] ambiguous input에서 tie-break가 재현 가능
- [ ] low-confidence 문서가 diagram 없이 artifact를 생성한다

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`

**Completion gate**
- [ ] 후보 선택이 랜덤하지 않다
- [ ] low-confidence에서도 reading path는 유지된다

---

## Phase 5 — Visualizer Integration

**Target outcome:** authored-first + heuristic fallback가 `visualize_markdown_bytes()`에 통합된다.

**Files**
- Modify: `vibelign/core/docs_visualizer.py`

**Implementation checklist**
- [ ] `_extract_mermaid_blocks()` 이후 `_has_usable_authored_diagram()` 게이트 추가 (비어있거나 선두 keyword 불일치 block 은 usable 로 간주하지 않음)
- [ ] usable authored diagram 이 없을 때만 heuristic fallback 실행, drop된 authored block 은 `auto_diagram_note` warning 에 기록
- [ ] `decision_flow` candidate 가 선택되었지만 renderer 가 `None` 을 반환하면 다음 tie-break 후보로 자동 fallback
- [ ] huge doc partial-disable 체크는 heuristic fallback **이전**에 수행: 걸리면 heuristic 도 skip하고 `auto_diagram_skipped_huge_doc` warning 을 남긴다
- [ ] `DiagramBlock` 생성 시 provenance/generator/confidence/warnings 반영
- [ ] `docs-build` stale 판정 경로에 generator version mismatch 조건이 걸리는지 확인 (필요 시 조건 추가)

**Validation**
- [ ] authored Mermaid 문서는 기존과 동일 동작
- [ ] Mermaid 없는 README에서 heuristic diagram 1개 생성
- [ ] huge doc에서는 기존 제한 규칙 유지
- [ ] BOM/CRLF fixture가 LF fixture와 동일한 heuristic output을 만든다

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`
- [ ] `python -m vibelign.cli.vib_cli docs-build PROJECT_CONTEXT.md --json`

**Completion gate**
- [ ] authored-first 원칙이 깨지지 않는다
- [ ] heuristic diagram도 hash-bound derived artifact로 저장된다

---

## Phase 6 — GUI Provenance Rendering

**Target outcome:** 사용자가 diagram 출처를 authored와 혼동하지 않는다.

**Files**
- Modify: `vibelign-gui/src/components/docs/VisualSummaryPane.tsx`
- Modify: `vibelign-gui/src/lib/vib.ts`

**Implementation checklist**
- [ ] diagram마다 provenance label 표시
- [ ] legacy artifact (`provenance` 필드 부재) 는 `authored` 로 해석
- [ ] heuristic diagram이면 설명 배너 표시
- [ ] `component_flow` 에는 provenance badge 외에 **"structural summary, not a dependency graph"** 배너를 별도로 강제 표시
- [ ] confidence badge 또는 equivalent text 표시
- [ ] stale artifact 상태와 provenance를 동시에 보여도 의미가 섞이지 않게 정리
- [ ] DocsViewer narrow-layout 에서 provenance/confidence/summary 3중 뱃지가 overflow 없이 렌더되는지 확인
- [ ] stale + heuristic + component summary warning 동시 상태 fixture 로 시각 QA

**Validation**
- [ ] heuristic diagram이 authored처럼 보이지 않는다
- [ ] stale + heuristic 조합이 오해를 만들지 않는다

**Suggested verification commands**
- [ ] `npm run build`
- [ ] GUI 수동 확인: authored / heuristic / no-diagram 상태 비교

**Completion gate**
- [ ] provenance와 trust-state가 별도 개념으로 표현된다
- [ ] diagram이 없어도 summary pane fallback은 유지된다

---

## Phase 7 — Test Coverage

**Target outcome:** heuristic generation이 회귀 없이 검증된다.

**Files**
- Modify: `tests/test_docs_visualizer.py`
- Modify: `tests/test_docs_build_cmd.py` (if schema contract assertion needed)

**Implementation checklist**
- [ ] authored Mermaid 우선 테스트
- [ ] 빈 authored block / 선두 keyword 미매칭 authored block → drop 후 heuristic fallback 테스트
- [ ] README → heading mindmap 테스트
- [ ] H1 이 없는 문서 → mindmap root fallback 테스트 (basename / "Untitled")
- [ ] guide/steps → step flow 테스트
- [ ] heading 사이에 끼인 ordered list → step sequence 로 인식되지 않는다는 회귀 테스트
- [ ] nested ordered list → 최상위 sequence 에서 제외되는 테스트
- [ ] step 9개 이상 → `… N more` truncation 표기 테스트
- [ ] decision doc → `decision_flow` candidate 선택되지만 renderer None → 다음 후보로 fallback 테스트 (초기 릴리즈 한정)
- [ ] component/file table → component flow 테스트 (subgraph, edge 없음 assertion)
- [ ] component_flow 에 중복 label 존재 시 node id 충돌 없음 테스트
- [ ] escaped pipe 포함 table fixture
- [ ] Windows path text 포함 component fixture 테스트
- [ ] BOM / CRLF fixture 테스트
- [ ] low-confidence/noisy doc → diagram 없음 테스트
- [ ] legacy artifact (provenance 필드 부재) → `authored` 로 해석되는 테스트
- [ ] generator version bump 시 기존 artifact 가 stale 판정되는 테스트
- [ ] same input => same output 테스트 유지 또는 확장

**Validation**
- [ ] 대표 문서 유형별 fixture coverage 확보
- [ ] warning field regression 없음

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`
- [ ] `pytest tests/test_docs_build_cmd.py -q`

**Completion gate**
- [ ] heuristic path의 주요 분기점이 모두 테스트된다
- [ ] authored path 회귀가 없다

---

## Phase 8 — Verification

**Target outcome:** heuristic diagram 생성이 빠르고 예측 가능하며 UX를 해치지 않는다는 근거가 생긴다.

**Files**
- Modify/Create relevant tests and fixtures from earlier phases

**Verification checklist**
- [ ] medium-size README에서 artifact 생성 시간이 체감상 기존과 크게 다르지 않다
- [ ] long doc에서 node/heading cap이 적용된다
- [ ] generated Mermaid가 GUI build/runtime을 깨지 않는다
- [ ] stale artifact / missing artifact / authored artifact / heuristic artifact 상태를 모두 확인한다
- [ ] macOS/LF 와 Windows/CRLF fixture에서 동일 markdown 내용이 동일한 heuristic Mermaid source를 만든다

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`
- [ ] `pytest tests/test_docs_build_cmd.py -q`
- [ ] `npm run build`
- [ ] 필요시 `python -m vibelign.cli.vib_cli docs-build <path> --json`

**Completion gate**
- [ ] heuristic generation이 기본 reading UX를 느리게 만들지 않는다
- [ ] docs viewer가 authored와 heuristic을 명확히 구분한다
- [ ] fallback path가 유지된다

---

## Final Ship Criteria

- [ ] authored-first 규칙이 문서화와 코드에서 일치한다
- [ ] heuristic diagram은 최대 1개만 생성된다
- [ ] low-confidence는 diagram이 아니라 artifact root warning으로 남는다
- [ ] schema / GUI / tests가 provenance 확장을 함께 반영한다
- [ ] same input → same output이 유지된다
- [ ] markdown-first / hash-bound / trust-state 원칙이 유지된다
