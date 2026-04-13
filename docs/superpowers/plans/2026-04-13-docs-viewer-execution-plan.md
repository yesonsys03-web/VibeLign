# Docs Viewer Execution Checklist

> **Working rule:** `.md` is the only source of truth. The viewer must never wait for conversion before showing content.

**Goal:** 긴 기획/설계 markdown 문서를 VibeLign GUI 안에서 즉시 읽을 수 있게 만들고, 클로드풍 시각화 패널은 md와 항상 동기화된 파생 데이터로 제공한다.

**Architecture in one line:** GUI는 markdown을 직접 즉시 렌더하고, docs visualizer는 md에서 파생 JSON을 만들며, watcher는 md 변경 시 이 캐시를 자동 갱신한다. GUI는 `source_hash`가 일치할 때만 enhancement를 사용한다.

**Tech Stack:** React, TypeScript, Tauri, Python, `react-markdown`, `remark-gfm`, Mermaid

---

## Non-Goals (Do Not Expand During Initial Implementation)

- [ ] AI 기반 고급 요약 생성 파이프라인 구축
- [ ] 문서를 직접 다시 써주는 편집 기능
- [ ] 협업 주석/댓글 시스템
- [ ] 원격 문서 저장소 연동
- [ ] visual artifact를 source of truth처럼 직접 편집하는 기능

---

## Execution Rules

- [ ] `.md` is the only source of truth.
- [ ] 문서 열기는 derived artifact 생성과 무관하게 즉시 동작해야 한다.
- [ ] every derived artifact includes `source_path`, `source_hash`, `generated_at`, `generator_version`, `schema_version`
- [ ] `source_hash`는 한 곳에서만 canonical하게 계산한다. GUI는 hash를 직접 재구현하지 않고 비교만 한다.
- [ ] hash mismatch means stale and must never be shown as current truth
- [ ] derived artifact failure must never block markdown reading
- [ ] cache writes must be atomic (`tmp + replace`)
- [ ] old schema / old generator version / corrupt JSON must hard-fallback
- [ ] docs discovery/indexing의 owner는 하나만 둔다. 다른 레이어는 thin bridge만 담당한다.
- [ ] `read_file`류 bridge는 active project root 바깥을 절대 읽지 않는다.
- [ ] trust state의 기준은 watch string log가 아니라 open-time freshness validation이다.
- [ ] `manual` 탭은 `DocsViewer` 단일 경로로 정리하고, 기존 `Home` manual flow는 active path에서 제거한다.

---

## Cross-Platform Rules (Windows / macOS / Linux)

> 기존 코드베이스가 이미 `#[cfg(target_os)]` 분기와 `pathlib.Path`로 크로스 플랫폼을 처리하고 있다. 새 코드도 동일 패턴을 따른다.

- [ ] **Tauri `read_file` command**: `std::path::PathBuf`로 받아서 OS별 separator 처리 불필요하게 만들기. Windows `\` 경로도 그대로 동작해야 함
- [ ] **GUI 경로 키**: GUI에서 문서를 식별할 때 항상 forward slash (`/`) 기준 relative path를 key로 사용. Windows backslash는 bridge layer에서 normalize
- [ ] **Canonical hash input**: BOM strip, newline normalize policy, path normalize 규칙을 고정하고 Python 쪽 helper가 authoritative hash를 계산
- [ ] **파일 인코딩**: `read_to_string`은 UTF-8만 지원. Windows BOM(`\xEF\xBB\xBF`) 파일은 strip 후 전달. 비UTF-8 파일은 에러 상태로 처리
- [ ] **Cache 경로**: `.vibelign/docs_visual/`는 프로젝트 루트 하위이므로 OS별 config dir 분기 불필요. 기존 `meta_paths.py` 패턴과 동일하게 `pathlib.Path` 사용
- [ ] **Atomic write (Windows)**: `os.replace()`는 Windows에서도 동작하지만, 대상 파일이 다른 프로세스에 열려 있으면 실패할 수 있음. 실패 시 retry 1회 + 짧은 대기 후 fallback
- [ ] **Watch engine**: 기존 `watch_engine.py`의 Windows 호환 패턴 유지. `.vibelign/docs_visual` 경로를 watch 제외 목록에 추가할 때 OS separator 무관하게 매칭
- [ ] **Python subprocess**: `run_vib`의 기존 패턴 참조 — Windows에서 `CREATE_NO_WINDOW` 플래그, `PYTHONIOENCODING=utf-8` 설정

---

## Edge Cases That Must Be Verified

- [ ] rename / move / delete 후 orphan cache 없음
- [ ] burst save / temp-file replace 저장에서도 stale race 없음
- [ ] `.vibelign/docs_visual` write가 watch self-loop를 만들지 않음
- [ ] empty doc / no-heading doc / weird encoding / very long single-line doc에서도 reading layer 유지
- [ ] Mermaid syntax error / too many diagrams / slow render에서도 doc render 유지
- [ ] duplicate title 문서에서도 selection key는 path 기준으로 안정적
- [ ] root docs와 `docs/**` docs 사이에서 cache key 충돌 없음
- [ ] watch off 또는 `.vibelign/docs_visual` 삭제 상태에서도 fallback 동작
- [ ] **Windows에서 `\` 경로로 문서 열기/캐시 키 매칭 정상 동작**
- [ ] **Windows BOM 포함 md 파일에서 렌더링 깨지지 않음**
- [ ] **Linux에서 case-sensitive 파일명 충돌 없음 (예: `README.md` vs `readme.md`)**

---

## Main Files To Touch

| 파일 | 역할 | 변경 |
|------|------|------|
| `vibelign-gui/src/App.tsx` | `manual` 탭을 docs viewer로 연결 | Modify |
| `vibelign-gui/src/pages/DocsViewer.tsx` | 문서 보기 메인 화면 | Create |
| `vibelign-gui/src/components/docs/DocsSidebar.tsx` | 문서 목록/검색/선택 | Create |
| `vibelign-gui/src/components/docs/MarkdownPane.tsx` | md 즉시 렌더 | Create |
| `vibelign-gui/src/components/docs/MermaidDiagram.tsx` | mermaid block 렌더 | Create |
| `vibelign-gui/src/components/docs/VisualSummaryPane.tsx` | 카드형 요약 패널 | Create |
| `vibelign-gui/src/lib/docs.ts` | 문서 인덱스/상태/bridge helper | Create |
| `vibelign-gui/src/lib/vib.ts` | docs cache bridge 추가 | Modify |
| `vibelign-gui/src-tauri/src/lib.rs` | `read_file` command (Phase 2) + docs visual read / refresh event bridge (Phase 9) | Modify |
| `vibelign/core/docs_visualizer.py` | md → visual JSON 생성기 | Create |
| `vibelign/core/docs_cache.py` | docs cache helper | Create |
| `vibelign/core/meta_paths.py` | `.vibelign/docs_visual` path | Modify |
| `vibelign/core/watch_engine.py` | md watch → docs visual sync | Modify |
| `vibelign/commands/vib_docs_build_cmd.py` | manual build command | Create |
| `vibelign/cli/cli_core_commands.py` | `vib docs-build` 등록 | Modify |
| `tests/test_docs_visualizer.py` | generator tests | Create |
| `tests/test_docs_build_cmd.py` | CLI tests | Create |
| `tests/test_watch_engine.py` | watch sync regression | Modify |

---

## Global Completion Tracker

- [ ] Phase 1 — Docs Viewer Skeleton
- [ ] Phase 2 — Immediate Markdown Rendering
- [ ] Phase 3 — Mermaid Support
- [ ] Phase 4 — Document Index and Navigation
- [ ] Phase 5 — Visual Artifact Schema
- [ ] Phase 6 — Docs Visualizer Core
- [ ] Phase 7 — Manual Build Command
- [ ] Phase 8 — Watch Sync Integration
- [ ] Phase 9 — GUI Sync State and Trust UX
- [ ] Phase 10 — Claude-Style Visual Summary Pane
- [ ] Phase 11 — Failure Recovery and Fallbacks
- [ ] Phase 12 — Verification

---

## Phase 1 — Docs Viewer Skeleton

**Target outcome:** `manual` 탭이 `Home` 서브뷰 대신 독립 docs viewer page를 연다.

**Files**
- Modify: `vibelign-gui/src/App.tsx`
- Create: `vibelign-gui/src/pages/DocsViewer.tsx`

**Implementation checklist**
- [ ] `DocsViewer` page 생성
- [ ] `App.tsx`에서 `manual` 라우팅을 `DocsViewer`로 교체
- [ ] 기존 top nav 유지
- [ ] empty state / loading state 추가
- [ ] `Home.tsx`의 `manual_list/manual_detail` 흐름이 active execution path에서 빠지게 정리한다

**Validation**
- [ ] GUI에서 `메뉴얼` 탭 클릭 시 `DocsViewer`가 열린다
- [ ] 기존 `Doctor`, `Checkpoints`, `Settings` 흐름은 깨지지 않는다

**Completion gate**
- [ ] `Home initialView="manual_list"` 경로가 실행 기준에서 제거되었다
- [ ] `DocsViewer`가 기본 빈 화면이라도 독립적으로 동작한다
- [ ] `manual` 탭에서 더 이상 `Home`의 manual flow로 진입하지 않는다

---

## Phase 2 — Immediate Markdown Rendering

**Target outcome:** 문서를 클릭하면 변환 대기 없이 본문이 바로 보인다.

**Prerequisites**
- `npm install react-markdown remark-gfm` (의존성 설치)

**Files**
- Create: `vibelign-gui/src/components/docs/MarkdownPane.tsx`
- Create: `vibelign-gui/src/lib/docs.ts`
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`
- Modify: `vibelign-gui/src/lib/vib.ts`
- Modify: `vibelign-gui/src-tauri/src/lib.rs` (Tauri `read_file` command 추가 — 현재 임의 파일 읽기 커맨드가 없으므로 이 단계에서 선행 필요)

**Implementation checklist**
- [ ] Tauri `read_file` command 추가 — md 파일 내용을 GUI로 전달하는 bridge. `PathBuf`로 받아 OS separator 자동 처리. Windows BOM strip 포함
- [ ] `vibelign-gui/src/lib/vib.ts`에 `readFile(path)` wrapper 추가
- [ ] `read_file`는 active project root 내부의 허용 문서 경로만 읽도록 canonical path 검증을 넣는다
- [ ] `react-markdown` + `remark-gfm` 연결
- [ ] heading/list/table/checklist/code block/blockquote 렌더
- [ ] 기본 TOC 또는 section jump 정보 생성
- [ ] 큰 문서에서 과도한 동기 계산 분리
- [ ] 문서 선택: Phase 4 이전이므로 hardcoded 경로(`PROJECT_CONTEXT.md`)로 초기 렌더 검증

**Validation**
- [ ] GUI build/typecheck에서 `readFile` bridge 호출 타입이 맞는다
- [ ] `PROJECT_CONTEXT.md`가 즉시 보인다
- [ ] `docs/wiki/*.md` 중 하나를 열어 표/리스트/코드블록 표시 확인
- [ ] 문서 로딩 실패 시 사용자에게 읽을 수 있는 오류 상태 제공

**Suggested verification commands**
- [ ] `npm run build` 또는 프로젝트의 프런트엔드 검증 명령 실행

**Completion gate**
- [ ] 읽기 UX가 derived cache 없이도 성립한다
- [ ] markdown은 항상 first paint에 보인다
- [ ] root 밖 파일 읽기나 `..` 경로 탈출이 차단된다

---

## Phase 3 — Mermaid Support

**Target outcome:** mermaid block이 시각화되고, 실패해도 읽기는 유지된다.

**Prerequisites**
- Mermaid 패키지 선택: `mermaid` (직접 사용, lazy-load) vs `react-mermaidjs` — 번들 사이즈 고려하여 결정 필요

**Decision checkpoint**
- [ ] Mermaid 패키지를 결정하고 이유를 기록한다

**Files**
- Create: `vibelign-gui/src/components/docs/MermaidDiagram.tsx`
- Modify: `vibelign-gui/src/components/docs/MarkdownPane.tsx`

**Implementation checklist**
- [ ] mermaid 패키지 설치
- [ ] fenced code block 중 `mermaid`만 별도 처리
- [ ] `startOnLoad: false`
- [ ] `securityLevel: "strict"`
- [ ] 실패 시 code block fallback 유지
- [ ] 다이어그램 과다 문서에서 visible-first 전략 적용

**Validation**
- [ ] 정상 mermaid 문서에서 SVG 렌더
- [ ] 문법 오류 mermaid에서 fallback 확인
- [ ] mermaid 없는 문서에서 부작용 없음

**Suggested verification commands**
- [ ] `npm run build` 또는 GUI 검증 명령 실행

**Completion gate**
- [ ] Mermaid는 enhancement일 뿐 reading path를 막지 않는다

---

## Phase 4 — Document Index and Navigation

**Target outcome:** 폴더를 직접 열지 않아도 문서를 찾고 전환할 수 있다.

**Files**
- Create: `vibelign-gui/src/components/docs/DocsSidebar.tsx`
- Modify: `vibelign-gui/src/lib/docs.ts` (Phase 2에서 생성됨)
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`
- Modify: `vibelign-gui/src/lib/vib.ts` 또는 `vibelign-gui/src-tauri/src/lib.rs` (docs index source bridge)

**Decision checkpoint**
- [ ] docs index source를 결정한다: Tauri `list_docs()` command vs 별도 CLI/JSON index
- [ ] 선택한 owner가 docs discovery의 single source가 되도록 고정한다

**Implementation checklist**
- [ ] 인덱스 대상 정의: `PROJECT_CONTEXT.md`, `docs/MANUAL.md`, `docs/wiki/**/*.md`, `docs/superpowers/specs/*.md`, `docs/superpowers/plans/*.md`
- [ ] docs index source bridge 구현
- [ ] 분류: Manual / Context / Wiki / Spec / Plan
- [ ] 제목/경로/최근 수정 시간 표시
- [ ] 검색 필터 추가
- [ ] duplicate title 대비 path-based selection key 적용

**Validation**
- [ ] 같은 제목 문서가 있어도 다른 문서가 정확히 열린다
- [ ] 루트 문서와 `docs/**` 문서가 함께 인덱싱된다

**Suggested verification commands**
- [ ] docs index bridge 테스트 또는 수동 결과 확인

**Completion gate**
- [ ] 문서 선택 상태가 안정적으로 유지된다
- [ ] 폴더 탐색 없이 기획 문서 진입이 가능하다
- [ ] docs 목록 기준이 GUI와 build/watch 사이에서 어긋나지 않는다

---

## Phase 5 — Visual Artifact Schema

**Target outcome:** generator와 GUI가 공유하는 안정된 JSON 계약이 생긴다.

**Files**
- Create: `vibelign/core/docs_cache.py`
- Create: `vibelign/core/docs_visualizer.py`

**Implementation checklist**
- [ ] top-level schema 정의
- [ ] canonical `source_hash` 계산 규칙을 schema/helper 수준에서 고정
- [ ] 메타 필드 고정: `source_path`, `source_hash`, `generated_at`, `generator_version`, `schema_version`
- [ ] 데이터 필드 고정: `title`, `summary`, `sections`, `glossary`, `action_items`, `diagram_blocks`, `warnings`
- [ ] invalid rules 정의: old schema / old generator version / corrupt JSON

**Validation**
- [ ] schema 예제를 문서 내에 남기거나 테스트에서 고정
- [ ] GUI가 이 schema만으로 trust state 판단 가능

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q` 또는 동등한 schema 검증 실행

**Completion gate**
- [ ] schema 변경 시 version bump 규칙이 분명하다
- [ ] hash 계산 기준이 Rust/TS/Python 사이에서 하나로 고정되었다

---

## Phase 6 — Docs Visualizer Core

**Target outcome:** md 하나에서 hash-bound visual artifact 하나를 생성한다.

**Files**
- Modify: `vibelign/core/docs_visualizer.py` (Phase 5에서 생성됨 — 이 단계에서 실제 로직 구현)
- Create: `tests/test_docs_visualizer.py`

**Implementation checklist**
- [ ] heading tree 추출
- [ ] checklist / warning-like section / action-like bullet 구조화
- [ ] mermaid block 메타 추출
- [ ] 규칙 기반 summary 생성
- [ ] empty doc / no-heading doc / weird encoding fallback 처리
- [ ] 실패 시 부분 파일 대신 명확한 failure 반환

**Validation**
- [ ] 정상 문서에서 visual JSON 생성
- [ ] 빈 문서에서도 최소 title/body fallback
- [ ] 긴 문서에서 deterministic 결과 유지

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py -q`

**Completion gate**
- [ ] same input → same output이 성립한다
- [ ] source hash가 artifact에 포함된다

---

## Phase 7 — Manual Build Command

**Target outcome:** watch 없이도 docs visual cache를 재생성할 수 있다.

**Files**
- Create: `vibelign/commands/vib_docs_build_cmd.py`
- Modify: `vibelign/cli/cli_core_commands.py`
- Create: `tests/test_docs_build_cmd.py`

**Implementation checklist**
- [ ] `vib docs-build` 추가
- [ ] single-file build 지원
- [ ] full rebuild 지원
- [ ] output path는 `.vibelign/docs_visual/`
- [ ] 실패 시 partial artifact 금지

**Validation**
- [ ] 단일 파일 build 성공
- [ ] full rebuild 성공
- [ ] bad input에서 실패하지만 기존 reading path와 무관

**Suggested verification commands**
- [ ] `pytest tests/test_docs_build_cmd.py -q`
- [ ] `python -m vibelign.cli.vib_cli docs-build --help` 또는 실제 CLI 진입 검증

**Completion gate**
- [ ] watch가 꺼져 있어도 manual rebuild가 가능하다

---

## Phase 8 — Watch Sync Integration

**Target outcome:** md 저장 시 visual cache가 자동 갱신되고 stale race가 없다.

**Files**
- Modify: `vibelign/core/meta_paths.py`
- Modify: `vibelign/core/watch_engine.py`
- Modify: `tests/test_watch_engine.py`

**Implementation checklist**
- [ ] `.vibelign/docs_visual/` path 추가
- [ ] `.vibelign/docs_visual/` 디렉터리 생성 책임을 `MetaPaths` 또는 전용 ensure helper에 명시
- [ ] `_refresh_docs_artifacts(changed)` 추가
- [ ] md 변경 debounce + batch 처리
- [ ] tmp + replace atomic write (`os.replace()` 사용. Windows에서 대상 파일 잠금 시 retry 1회 + 50ms 대기)
- [ ] revision/hash mismatch면 finished result discard
- [ ] rename / move / delete 시 old cache cleanup
- [ ] `.vibelign/docs_visual` write가 self-loop를 만들지 않게 처리

**Validation**
- [ ] md modify → cache refresh
- [ ] rename / move / delete → orphan cache cleanup
- [ ] burst save 후 latest hash만 남음

**Suggested verification commands**
- [ ] `pytest tests/test_watch_engine.py -q`

**Completion gate**
- [ ] watch sync는 최신 문서 상태만 반영한다
- [ ] cache write가 watch를 재귀적으로 다시 태우지 않는다
- [ ] watch는 freshness 보조 경로이고, trust state의 기준은 open-time validation으로 남아 있다

---

## Phase 9 — GUI Sync State and Trust UX

**Target outcome:** 사용자가 지금 보는 enhancement가 최신인지 명확히 안다.

**Files**
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`
- Modify: `vibelign-gui/src/lib/vib.ts`
- Modify: `vibelign-gui/src-tauri/src/lib.rs` (Phase 2에서 `read_file` 추가됨 — 이 단계에서 docs visual read / refresh event bridge 확장)

**Implementation checklist**
- [ ] 상태 정의: `markdown-only`, `enhanced-synced`, `enhanced-stale`, `enhanced-failed`
- [ ] current markdown hash vs artifact hash 비교
- [ ] trust state 계산은 open-time freshness validation을 기본으로 하고, watch event는 선택적 최적화로만 쓴다
- [ ] stale이면 current truth처럼 보이지 않게 처리
- [ ] failed여도 markdown pane 유지
- [ ] 가능하면 구조화된 refresh event 추가

**Validation**
- [ ] stale artifact를 현재 정보처럼 오해할 수 없다
- [ ] failed artifact 상황에서도 문서는 읽힌다

**Suggested verification commands**
- [ ] GUI build/typecheck 실행
- [ ] stale artifact를 만들어 상태 표시를 수동 확인

**Completion gate**
- [ ] trust state가 시각적으로 명확하다
- [ ] watch가 멈춰도 문서를 다시 열면 trust state가 정확하다

---

## Phase 10 — Claude-Style Visual Summary Pane

**Target outcome:** 초보자도 바로 이해할 수 있는 카드형 설명 패널이 붙는다.

**Files**
- Create: `vibelign-gui/src/components/docs/VisualSummaryPane.tsx`
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`

**Implementation checklist**
- [ ] 한 줄 요약 카드
- [ ] 왜 중요한지 카드
- [ ] 지금 해야 할 일 카드
- [ ] 어려운 용어 풀이 카드
- [ ] 구현 순서 카드
- [ ] artifact 없을 때 lightweight fallback 또는 숨김 처리

**Validation**
- [ ] summary pane이 없어도 문서 읽기는 유지
- [ ] summary pane이 있을 때 원문과 충돌하지 않음

**Suggested verification commands**
- [ ] GUI 수동 확인: summary pane on/off, artifact missing 상태 확인

**Completion gate**
- [ ] enhancement는 문서 이해를 돕지만 truth를 대체하지 않는다

---

## Phase 11 — Failure Recovery and Fallbacks

**Target outcome:** 어떤 실패에도 reading layer가 끊기지 않는다.

**Files**
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`
- Modify: `vibelign/core/docs_visualizer.py`
- Modify: `vibelign/commands/vib_docs_build_cmd.py`

**Implementation checklist**
- [ ] artifact missing → markdown-only
- [ ] corrupt artifact → ignore + rebuild path
- [ ] old generator version / schema mismatch → same fallback
- [ ] Mermaid failure → code fallback
- [ ] watch off → open-time freshness check
- [ ] huge doc / too many diagrams → enhancement partial disable allowed

**Validation**
- [ ] `.vibelign/docs_visual` 삭제 후도 읽기 가능
- [ ] corrupt JSON에서도 앱 크래시 없음
- [ ] huge doc에서도 pane 일부 비활성화만 되고 reading 유지

**Suggested verification commands**
- [ ] corrupt/stale artifact fixture로 수동 확인 또는 테스트 추가

**Completion gate**
- [ ] fancy layer failure가 reading layer failure로 번지지 않는다

---

## Phase 12 — Verification

**Target outcome:** 속도, sync, fallback이 실제로 증명된다.

**Files**
- Modify/Create relevant tests from earlier phases

**Verification checklist**
- [ ] 긴 md 파일 열기 성능 확인
- [ ] mermaid 많은 문서 안정성 확인
- [ ] md 수정 후 hash/state/cache 갱신 확인
- [ ] watch on/off 둘 다에서 fallback 확인
- [ ] `.vibelign/docs_visual` 삭제 후 복구 확인
- [ ] rename / move / delete 후 orphan cache 없음 확인
- [ ] burst save 후 latest hash만 반영 확인
- [ ] corrupt JSON / old schema / old generator version fallback 확인
- [ ] empty doc / no-heading doc / duplicate title 문서 UI 확인
- [ ] Windows `\` 경로에서 문서 열기 / 캐시 키 매칭 정상 확인
- [ ] Windows BOM 포함 md 파일 렌더링 확인
- [ ] Linux case-sensitive 파일명에서 캐시 충돌 없음 확인
- [ ] Windows에서 atomic write 실패 시 retry 동작 확인
- [ ] root 밖 경로 / `..` 탈출 / symlink 우회 읽기가 차단되는지 확인
- [ ] watch 없이 문서를 다시 열었을 때도 freshness/trust state가 정확한지 확인
- [ ] `manual` 탭이 `Home` legacy manual flow로 되돌아가지 않는지 확인

**Suggested verification commands**
- [ ] `pytest tests/test_docs_visualizer.py tests/test_docs_build_cmd.py tests/test_watch_engine.py -q`
- [ ] GUI build/typecheck 명령 실행
- [ ] 수동 시나리오 체크리스트 수행 후 결과 기록

**Completion gate**
- [ ] “바로 열리고, 항상 맞고, 실패해도 읽힌다”를 시연 가능하다
- [ ] 테스트/수동검증 항목이 문서화되어 있다

---

## Execution Order

1. Phase 1 — Docs Viewer Skeleton
2. Phase 2 — Immediate Markdown Rendering
3. Phase 3 — Mermaid Support
4. Phase 4 — Document Index and Navigation
5. Phase 5 — Visual Artifact Schema
6. Phase 6 — Docs Visualizer Core
7. Phase 7 — Manual Build Command
8. Phase 8 — Watch Sync Integration
9. Phase 9 — GUI Sync State and Trust UX
10. Phase 10 — Claude-Style Visual Summary Pane
11. Phase 11 — Failure Recovery and Fallbacks
12. Phase 12 — Verification

---

## Final Success Criteria

- [ ] 기획 md 파일이 GUI에서 즉시 열린다
- [ ] 긴 문서도 원문 기준으로 먼저 읽을 수 있다
- [ ] 시각화는 md와 hash 기반으로 동기화된다
- [ ] stale / failed 상태가 UI에서 명확히 보인다
- [ ] watcher가 켜져 있으면 파생 시각화가 자동 갱신된다
- [ ] fancy layer가 실패해도 원문 읽기는 절대 막히지 않는다
