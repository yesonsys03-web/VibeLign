# Changelog

본 파일은 VibeLign 의 주요 변경사항을 기록합니다.
포맷은 [Keep a Changelog](https://keepachangelog.com/) 를 따르며,
버전 체계는 [Semantic Versioning](https://semver.org/) 을 준수합니다.

---

## [Unreleased]

---

## [2.2.14] — 2026-05-19

v2.2.13 의 CI codesign manifest 보강이 GitHub Actions 빌드만 커버해서, **로컬 빌드 (사용자 직접 `npm run tauri build`)** 에서는 같은 `RUST_ENGINE_INTEGRITY_FAILED` 가 그대로 재발하던 회귀를 차단. integrity 검사를 런타임 self-heal 로 격상.

### Fixed

- **macOS 번들 `vibelign-engine` integrity self-heal** (`vibelign/core/checkpoint_engine/rust_engine/discovery.py`): 매니페스트와 binary hash 가 어긋날 때, `codesign --verify --strict` 가 통과하는 binary 는 정상 codesigned artifact 로 간주하고 매니페스트를 갱신해 회복한다. macOS 한정 — Windows/Linux 는 codesign 신뢰 신호가 없어 기존대로 실패. 로컬 빌드, CI 빌드, 사용자가 직접 재서명한 빌드 모두 동일하게 동작.

### Why

v2.2.13 의 `gui.yml` 수정은 CI 의 `codesign --deep` 직후 매니페스트를 재생성했지만, 사용자가 로컬에서 직접 `npm run tauri build` (혹은 Tauri 의 cargo bundle 단계) 를 실행하면 같은 binary mutation 이 일어나도 manifest refresh step 이 없어 같은 증상 재발. 빌드 경로별 후처리를 강제하기보다 vibelign 자체가 codesign 검증을 통과한 binary 를 신뢰하도록 격상하는 게 robust.

### Verified

- `tests/test_rust_engine_discovery_integrity.py` 8 통과 (darwin self-heal 회귀 테스트 3건 신규 — codesigned 회복, 미서명 실패 유지, non-darwin self-heal 금지).
- `tests/test_git_hooks*.py` 24 통과 (v2.2.13 변경 회귀 없음).

### Notes

- macOS Big Sur+ 의 linker 자동 ad-hoc 서명, Tauri 의 cargo bundle 단계 서명, 사용자 수동 `codesign --deep -s -` 모두 같은 경로로 처리.
- 기존 v2.2.13 GUI 설치본 즉시 우회 (v2.2.14 빌드 받기 전까지):
  ```
  ENGINE="/Applications/vibelign-gui.app/Contents/Resources/vib-runtime/_internal/vibelign/_bundled/vibelign-engine"
  shasum -a 256 "$ENGINE" | awk '{print $1"  vibelign-engine"}' > "$ENGINE.sha256"
  ```

---

## [2.2.13] — 2026-05-19

자동 백업 정합성 hotfix — GUI `RUST_ENGINE_INTEGRITY_FAILED` 폭발과 GUI commit tool 환경의 post-commit 자동 백업 누락 동시에 해소.

### Fixed

- **GUI `vibelign-engine` integrity check 실패** (`.github/workflows/gui.yml`): macOS `codesign --deep` 가 bundled binary 끝에 서명 blob 을 추가해 사전 생성된 `.sha256` 매니페스트와 hash 가 어긋나던 회귀. codesign 직후 매니페스트를 재생성하도록 step 보강. GUI 의 `vib history`, BACKUPS 페이지 등 Rust 엔진 호출이 `RUST_ENGINE_INTEGRITY_FAILED: integrity check failed` 로 폭발하던 issue 해결.
- **post-commit 자동 백업 PATH 의존성** (`vibelign/core/git_hooks.py`): hook 의 모든 fallback 이 `command -v vib` 같은 PATH lookup 에만 의존해서, Sourcetree / VS Code / Tower 처럼 launchd PATH 만 상속해 `~/.local/bin` 이 빠진 commit tool 에서 자동 백업이 통째로 누락되던 회귀. install 시점에 `shutil.which('vib')` / `shutil.which('vibelign')` / `sys.executable` 절대 경로를 캡처해 PATH 분기보다 먼저 시도하도록 hook 구조 변경. marker 를 v4 로 bump 하고 v1-v3 hook 자동 교체.

### Changed

- **CI 매트릭스에서 Linux 제외** (`.github/workflows/publish.yml`, `python.yml`): wheel publish 가 `[macos-13, windows-latest]` 만 build, sdist 는 macos-13 로 이동. `python.yml` 의 smoke build 도 `macos-latest` 로 이동. Linux user 대상 PyPI wheel 제공 중단.

### Verified

- `tests/test_git_hooks.py` + `tests/test_git_hooks_post_commit.py` 24 통과 (절대 경로 분기 회귀 테스트 신규 1건, marker v4 자동 교체 회귀 포함).
- `_build_post_commit_block()` 출력 수동 검증 — 절대 경로 3개 fallback (vib, vibelign, python -m vibelign) 가 PATH 분기 위에 위치.

### Notes

- 사용자는 `vib start` 한 번 다시 돌리거나 GUI 를 새 릴리즈로 업데이트하면 양 issue 자동 해소.
- 기존 v2.2.12 GUI 설치본에서 즉시 우회하려면: `cp ~/.local/share/uv/tools/vibelign/lib/python*/site-packages/vibelign/_bundled/vibelign-engine /Applications/vibelign-gui.app/Contents/Resources/vib-runtime/_internal/vibelign/_bundled/vibelign-engine`.

---

## [2.2.12] — 2026-05-19

vib 의 pre-commit hook 이 사소한 구조 drift 만으로 commit 을 막던 문제를 해소. secrets 차단은 유지하면서 guard 실패는 advisory(경고만) 로 강등.

### Changed

- **pre-commit hook 유연화** (`vibelign/core/git_hooks.py`): hook 템플릿을 `pre-commit-enforcement v3` 로 bump. `vib guard --strict` 가 실패해도 commit 은 통과시키고 stderr 에 한 줄 알림만 출력. `vib secrets --staged` 는 그대로 차단 (시크릿 누출 위험은 비대칭이라 보수적으로 유지).
- **escape hatch 환경변수 추가**:
  - `VIBELIGN_SKIP_HOOK=1 git commit ...` — 1회용 우회 (`--no-verify` 의도-명확 버전, vib 자체가 실행되지 않음).
  - `VIBELIGN_STRICT_GUARD=1` — strict 팀용 opt-in. 옛 차단 동작 복귀.
- **기존 hook 자동 재설치** (`_HOOK_MARKER_RE`): `secrets-pre-commit v1` / `pre-commit-enforcement v1` / `pre-commit-enforcement v2` 어느 marker 든 다음 `vib start` 에서 v3 로 자동 교체. 사용자 수동 정리 불필요.

### Why

사용자 보고: `vib guard --strict` 가 commit 시점에 자잘한 anchor drift 를 잡아 commit 이 여러 차례 실패. secrets 누출 같은 비가역 실수는 차단을 유지해야 하지만, 구조 drift 는 `vib doctor` / 다음 작업에서 다시 잡히므로 commit 차단까지는 과함. (이번 release 자체가 `pre-commit-enforcement v3` 동작 변경이라, 새 marker 가 사용자 환경에 도달하면 즉시 효과 발생.)

### Verified

- `tests/test_git_hooks.py` 13 개 통과 (advisory 동작, STRICT_GUARD opt-in, SKIP env 우회, v1/v2 marker 자동 교체 모두 회귀 테스트).
- `tests/test_git_hooks_post_commit.py` 10 개 통과 (post-commit hook 회귀 없음).
- 전체 스위트 1383 passed, 14 failed — 모든 실패는 main 에서도 동일하게 재현되는 pre-existing 항목 (stash 검증).

### Notes

- 기존 `.git/hooks/pre-commit` 이 `secrets-pre-commit v1` 형태인 사용자도 다음 `vib start` 한 번이면 자동 교체.
- guard 차단이 정말 필요한 팀은 `~/.zshrc` / shell rc 에 `export VIBELIGN_STRICT_GUARD=1` 박아두면 옛 동작 유지.

---

## [2.2.11] — 2026-05-13

v2.2.10 측정 데이터(`vib patch` baseline 0/7 on 사용자 실 자연어 요청) 후속으로, GUI 의 Patch 카드를 노출에서 제거. CLI `vib patch` 는 변경 없음.

### Removed

- **GUI Patch 카드 노출** (`vibelign-gui/src/hooks/useCardOrder.ts`): `DEFAULT_CARD_ORDER` 에서 `"patch"` 토큰 제거. 신규/기존 사용자 모두 Home 카드 목록에서 더 이상 보이지 않음. 기존 사용자의 saved card-order 는 `useCardOrder.ts:26` 의 filter 가 자동 정리.

### Why

v2.2.10 데이터셋 7 entries 전부에서 `vib patch` 가 무관한 파일을 지목 (keyword trap):
- user-004: `--json` 키워드 → `vib_docs_build_cmd.py` (오답)
- user-007: `--preview` 키워드 → `vibelign-core/src/backup/restore/preview.rs` (오답, 무비판 실행 시 vib 의 `recover --preview` 기능 회귀 가능)

GUI 사용자가 이 카드의 부정확한 출력을 무비판적으로 따를 위험이 가장 큼. CLI 는 사용자가 직접 검토 후 적용하는 흐름이라 risk 가 다름.

### Notes

- CLI `vib patch` 명령: 변경 없음. 다음 마일스톤에서 별도 deprecation 검토.
- `PatchCard.tsx` import + `Home.tsx:115` 의 `case "patch":` 는 dead code 로 보존 — trivial re-enable 옵션 유지.
- `commandData.ts` 의 patch 명령 정의 + `Manual` / `Help` 페이지의 patch 문서는 보존됨.

### Verified

- `npm run build` (vibelign-gui) — 통과.
- `npm test` — pre-existing DocsViewer 2 fail 동일, patch-hide 무관.
- macOS/Windows GitHub Actions CI — 모두 SUCCESS (PR #8).

---

## [2.2.10] — 2026-05-13

VibeLign 정체성 pivot 시작점 — **host LLM(Claude Code/Cursor)이 MCP 도구로 직접 file:anchor 매핑**할 수 있는 PoC 인프라 mainlined. 부수로 BACKUPS 페이지네이션 + Explain 카드 옵션 정리.

### Added

- **MCP `anchor_read_content` 도구** (`vibelign/mcp/mcp_anchor_handlers.py`): host LLM 이 패치 전 앵커 내부 텍스트를 정확한 경계로 read. path traversal 방지(`fp.relative_to(root)`), `minLength: 1` 스키마 가드, `_START`/`_END` 접미사 자동 정규화 포함.
- **MCP `project_map_get` 도구** (`vibelign/mcp/mcp_misc_handlers.py`): 프로젝트 카테고리/파일/앵커 인덱스를 raw JSON 으로 반환. host LLM 이 자연어 요청을 정확한 파일에 매핑하기 위한 전역 컨텍스트 도구. non-dict shape 거부 + OSError 메시지 경로 누출 방지.
- **BACKUPS 탭 + DB Viewer rows pagination** (`FileHistoryTable.tsx`, `BackupDbRowList.tsx`): 페이지당 10개, "이전 / X / Y 페이지 · M–N / TOTAL / 다음" 푸터. 리스트가 누적되면 예전 항목 접근이 어려웠던 문제 해결. FileHistoryTable 은 검색어 변경 시 1페이지 리셋, 선택 항목이 다른 페이지에 있으면 자동 점프.
- **Baseline 회귀 락** (`tests/benchmark/test_patch_suggester_baseline.py`): rule-based `patch_suggester` 의 file/anchor 매칭 수치(14/20 file, 0/19 anchor) 락. sentinel-driven 검증으로 silent regression 방지.
- **수동 평가 runbook** (`docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`): host LLM 정확도 측정 절차 + 의사결정 트리 (성공/부분/실패별 다음 단계 명시).
- **User requests dataset** (`tests/benchmark/user_requests.json`): 사용자 실 자연어 수정 요청 6 entries (ambiguous case 의 plausible set 확장 포함).
- **PoC plan + decision artifacts** (`docs/superpowers/plans/2026-05-13-mcp-host-llm-pivot-plan.md`).

### Removed

- **Explain 카드의 `--write-report` / `--json` 옵션** (`vibelign-gui/src/lib/commandData.ts`): GUI 카드 flags 배열에서 두 bool 옵션 제거. CLI 의 동일 플래그는 그대로 지원 (다른 명령 - doctor, guard, patch - 도 영향 없음).

### Measured

- `vib patch` baseline vs host-LLM-driven flow 자연 분포 측정: **6 사용자 실 요청 중 baseline 0/6 (0%), fresh blind subagent 6/6 (100%)**. sample_project 인공 시나리오(baseline 14/20) 보다 자연 분포에서 gap 이 훨씬 큼이 입증됨.
- `vib patch "gui 익스플레인 카드에서 --write-report --json 옵션은 제거해줘"` → `vibelign/commands/vib_docs_build_cmd.py` (오답, JSON 키워드 함정 명시) vs host LLM 은 정답 `commandData.ts` 즉시 짚음. dogfooding 증거 (PR #5 description 부록 참조).

### Verified

- `cargo test --lib` (vibelign-core) — 회귀 없음.
- `cargo check` (vibelign-gui/src-tauri) — 0 errors.
- `npx tsc --noEmit` (vibelign-gui) — No errors found.
- `npm run build` (vibelign-gui) — Vite bundle 정상 생성.
- `pytest tests/test_mcp_*` — 41 passed (anchor handlers + read content + misc + project_map_get + dispatch + tool snapshot + baseline lock).
- macOS/Windows GitHub Actions CI — 모두 SUCCESS (PR #4 / #5 / #7).

### Notes

- Gemini 경로 (`vib patch --ai`, `vibelign/core/ai_codespeak.py`) 는 본 릴리즈에서 변경 없음. 평가 결과(0% vs 100% gap)가 일관됨에 따라 다음 마일스톤에서 deprecation 검토.
- 신규 MCP 도구는 Claude Code/Cursor 가 vibelign-mcp 등록 시 자동 노출. CLI/GUI 동작은 변경 없음.

---

## [2.2.9] — 2026-05-13

v2.2.8 의 scroll-to-top floating 버튼이 mac/Windows 양쪽에서 안 보이던 issue 의 패치 릴리즈.

### Fixed

- **scroll-to-top 버튼 — 실제 scroll container 인식** (`ScrollToTopButton.tsx`): `brutalism.css` 의 `.app-layout { height: 100vh; overflow: hidden }` + `.page-content { flex: 1; overflow-y: auto }` 구조라 실제 scroll container 는 `window` 가 아닌 `.page-content`. v2.2.8 의 listener 가 `window.addEventListener("scroll")` + `window.scrollY` 만 사용 → inner container 의 scroll 못 잡아 버튼 visibility toggle 미발동. 수정: `document.addEventListener("scroll", ..., { capture: true })` 추가 (scroll event 는 bubble 안 하지만 capture phase 에서 받음). `getActiveScrollContainer()` helper 로 `.page-content` element 찾고, `container?.scrollTop ?? window.scrollY` 로 visibility 판정, click 시 container scrollTo 우선.

### Verified

- `npx tsc --noEmit` (vibelign-gui) → No errors found.

---

## [2.2.8] — 2026-05-13

GUI 의 두 UX issue 수정 — "복구 후보 추천 보기" 의 후보별 차이 정보 누락 + "CANVAS / RAW HTML" 화면의 iframe 잘림. 추가로 모든 페이지에 scroll-to-top floating 버튼.

### Added

- **scroll-to-top floating 버튼** (`ScrollToTopButton.tsx`): `window.scrollY > 300` 시 우하단에 표시되는 buttons (브루탈리즘 스타일, ↑ glyph). 클릭 시 `window.scrollTo({ top: 0, behavior: "smooth" })`. App root level 에 한 번 render 되어 모든 page (Home / Doctor / DocsViewer / BackupDashboard / ErrorLogs / Settings / Onboarding) 공통 사용.

### Fixed

- **GUI 복구 후보 추천 — AI candidate-specific reason 추가 표시 + 문구 친화화** (`RecoveryOptionsCard.tsx`): 3 후보가 모두 동일한 "근거" 문구를 보이던 issue. 진짜 차이를 표현하는 LLM `candidate.reason` 필드가 GUI 에 표시 안 됨이 원인. `<div>AI 설명: {candidate.reason}</div>` 추가로 candidate-specific 설명 표시 (한국어 phrase 시 LLM 이 한국어 reason 반환). rule-based 5 항목 문구도 기술용어 제거 ("커밋 직후 저장" → "코드 저장 직후 만든 백업" / "최근 검증 기록 없음" → "확인 안 한 시점" 등).
- **GUI CANVAS / RAW HTML 화면 — content-aware iframe 높이 + viewport-fit** (`CanvasViewPane.tsx`, `RawHtmlCanvasPane.tsx`): 두 view mode 의 iframe 이 markup 휴리스틱 추정에 의존하던 fixed-height 사용 → 추정 부족 시 content 잘리고 iframe 내부 스크롤바 생성. `sandbox="allow-same-origin"` 추가 (scripts/forms 여전히 disabled) + `onLoad` 핸들러로 `contentDocument.documentElement.scrollHeight + body.scrollHeight max + 24px margin` 측정 → height state 갱신. `minHeight: calc(100vh - 200px)` 추가로 short content 도 app window viewport 만큼 차지. 결과: content 가 짧으면 viewport-fit, 길면 page natural scroll (왼쪽 사이드처럼). iframe 안 별도 스크롤바 없음.

### Verified

- `cargo test --lib` (vibelign-core) → 145 passed.
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `npx tsc --noEmit` (vibelign-gui) → No errors found.
- `pytest test_recovery_*` → 32 passed, 0 회귀 (recovery 변경 없음, agent.py 의 prompt 축소는 v2.2.7 의 변경).

### Notes

- 본 릴리즈는 모두 user-facing UX fix — 측정/lessons 적용보다 직접 보고된 issue 의 정직한 수정.
- CanvasViewPane 와 RawHtmlCanvasPane 가 같은 iframe + fixed-height anti-pattern 이었음 — 두 component 모두 동일 fix 적용.

---

## [2.2.7] — 2026-05-13

GUI 의 "복구 후보 추천 보기" (Recovery 패널) 첫 호출 wall 25s → 13.6s (~46% 가속). `_compact_candidate_payload` 의 `commit_message` 가 LLM prompt 의 49% (28KB 중 13.8KB) 를 차지하던 것을 subject + 200자 cap 으로 축소. 추가로 score_path Rust port 트랙의 Session 1 probe artifacts (`score_path.rs::meaningful_overlap` + 5 parity tests + ipc variant) 가 dormant library 로 보존됨 — 트랙 자체는 §9 retraction 으로 종료.

### Performance

- **Recovery 후보 추천 wall ~46% 단축**: `vib recover --recommend --phrase ...` 의 첫 호출 (cache miss) wall **25s → 13.6s** 측정 확인. 원인은 LLM prompt 크기 (28KB) 의 49% 가 commit_message 본문이었던 것 — `_compact_candidate_payload` 가 commit 의 subject 첫 줄 + 200자 cap 으로 보내도록 변경. prompt 28,203 → 15,381 chars (-46%), Gemini Flash 응답 시간이 input 크기에 ~linear 라 wall 도 동일 비율로 감소. quality 영향 없음 (LLM 추천 결정은 source/created_at/evidence_score/commit_boundary 등 metadata 필드에 의존, commit body 의 verbose handoff/plan 세부는 unused).

### Added

- **`vibelign-core/src/score_path.rs::meaningful_overlap`** (dormant library): Python `_meaningful_overlap` 의 1:1 port + 5 parity unit tests. score_path 트랙 §9 retraction 후 dormant 로 보존 — 미래 score_path 통째 port 시도 시 재사용 가능 + Python 측 코드 변경 시 cargo test 가 drift 감지.
- **`EngineRequest::MeaningfulOverlap` ipc variant** + handler dispatch: GUI/외부 consumer 가 호출 가능. 현재 default-off 의 routing 은 없음 (Python wire 는 retraction 시 revert 됨).

### Verified

- `cargo test --lib` (vibelign-core) → **145 passed** (이전 140 + 신규 score_path parity 5 tests).
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `pytest test_recovery_agent + test_recovery_planner + test_memory_recovery_schemas` → 32 passed, 0 회귀.
- Wall warm 측정 (cache invalidate 후 fresh phrase): `vib recover --recommend` 25.18s → **13.60s**.
- prompt 크기 capture: 28,203 chars → **15,381 chars (-46%)**, commit_message 합 13,800 → 1,204 (-91%).

### Notes

- 두 retraction lessons (tokenizer 트랙 §9 + score_path 트랙 §9) 의 측정-주도 룰이 본 가속의 prerequisite — cProfile/pyinstrument cumtime 신뢰 X, stub-patch wall diff + apples-to-apples harness + skip-rate measurement 가 진짜 leverage 식별. 자세한 기록은 `docs/superpowers/plans/2026-05-13-patch-suggester-tokenizer-rust-port-plan.md` §9 + `docs/superpowers/plans/2026-05-13-score-path-rust-port-plan.md` §9 참조.

---

## [2.2.6] — 2026-05-13

GUI 의 메모리 요약 카드를 Python sidecar 호출에서 in-process Rust 직결로 전환하여 마운트 지연을 제거하고, 향후 score_path 최적화 트랙의 토대로 한국어 토큰 분해 Rust 모듈 (`vibelign-core/src/tokenizer.rs`) 과 102 case × 6 함수 = 612 record 의 parity fixtures 를 dormant library 로 추가했습니다. `_normalize_korean_token` 의 hot loop 에서 매 호출마다 재실행되던 sort 도 module-level pre-sort 로 정리했습니다.

### Added

- **GUI memorySummary direct bridge** (Phase 3 PoC consumer #13): `SessionMemoryCard` mount 시 `runVib(["memory","show","--json"])` 호출이 in-process `callEngineDirect({command:"memory_summary_read"})` 로 전환. Python sidecar ~80ms 호출 제거. audit logging parity 완전 유지 (`project_root_hash` SHA256[:16] / 마이크로초 timestamp / sequence number / `.create_new(true)` 파일 락).
- **`vibelign-core/src/tokenizer.rs`**: `vibelign.core.patch_suggester` 의 6 leaf 토큰 함수 (`_decompose_korean_compound` / `_split_identifier_parts` / `_normalize_korean_token` / `_expand_token` / `tokenize` / `_intent_tokens`) 와 const table 113 entries 를 Rust 로 1:1 포팅. 현재 dormant library — score_path multi-session 트랙 진입 시 ipc 노출 예정.
- **`tests/fixtures/tokenizer_goldens/`**: 102 case × 6 함수 = 612 expected record JSON fixtures + `_regenerate.py` (Python source-of-truth 재캡처 스크립트, `uv run python ...` 으로 호출). cargo test 의 byte-equal parity assertion 으로 Rust 포팅 정확성 검증 + Python alias drift 자동 감지.
- **`vibelign-core/examples/bench_tokenizer.rs`**: isolated 1M iter bench. 향후 score_path Rust port 시 floor 측정 reference.

### Changed

- **`_normalize_korean_token` pre-sort**: `sorted(_KOREAN_PARTICLE_SUFFIXES, key=len, reverse=True)` 가 매 호출 (recover preview 시 609k 회) 마다 재실행되던 것을 module-level `_KOREAN_PARTICLE_SUFFIXES_SORTED` tuple 한 번에 고정. direct 1M iter 27% 가속 (1.97μs → 1.44μs / call), wall noise (caller-side set 처리가 wall dominate). 결정성/순서는 byte-equal 유지.

### Verified

- `cargo test --lib` (vibelign-core) → **140 passed** (이전 134 + 신규 tokenizer parity 6 tests / 612 assertion).
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `npx tsc --noEmit` (vibelign-gui) → No errors found.
- `pytest tests/test_patch_*.py tests/test_recovery_planner.py` → 30 passed, 20 subtests passed.
- `cargo run --release --example bench_tokenizer` → 1M iter floor (intent_tokens 3,021 ns / expand_token 1,036 ns / decompose 5 ns per call).
- **Windows GNU cross-compile pre-flight** (`cargo check --target x86_64-pc-windows-gnu`, mingw-w64 mac local): vibelign-core 0 errors / vibelign-gui/src-tauri 0 errors + 5 cfg(unix) dead_code warnings (의도됨). 어제/오늘 신규 코드 (memory_audit / memory_state / sha2 / tokenizer / bench / pre-sort) 모두 Windows 호환 확인.

### Notes

- 사용자 체감 가속은 **memorySummary direct bridge** 에서. 나머지 변경 (tokenizer Rust 모듈 / fixtures / bench / pre-sort) 은 dormant library + tooling 으로 다음 트랙 (score_path 통째 Rust port) 의 토대.
- patch_suggester tokenizer 트랙 의 측정/디자인 + 단계 1/2 진척, 단계 3 retraction lessons (cProfile/pyinstrument cumtime over-attribution / cache hit ratio 가 wall 단축으로 직결되지 않음) 의 자세한 기록은 `docs/superpowers/plans/2026-05-13-patch-suggester-tokenizer-rust-port-plan.md` §9 참조.

---

## [2.2.5] — 2026-05-12

v2.2.4 GUI release build 에서 발견된 npm lockfile dependency metadata 오염을 복구한 패치 릴리즈입니다. Desktop GUI release 는 v2.2.5 로 재시도합니다.

### Fixed

- **GUI package-lock dependency metadata**: release version bump 가 dependency `json5@2.2.3` tarball URL 까지 바꾸지 않도록 lockfile 을 정상 재생성했습니다. `npm ci` 가 `json5-2.2.4.tgz` 를 찾다가 404 로 실패하던 문제를 해결합니다.

### Verified

- `npm ci` (vibelign-gui) → passed.
- `npm run build` (vibelign-gui) → passed.
- `npm run test` (vibelign-gui) → 2 files / 9 tests passed.
- `python3 -m build --sdist --wheel` → passed.
- Bridge contract check → `command string diff: missing=[] extra=[]`.

---

## [2.2.4] — 2026-05-12

v2.2.3 GUI release build 에서 드러난 legacy `backupCreate` import 호환성 누락을 복구한 패치 릴리즈입니다. PyPI v2.2.3 는 정상 publish 되었지만 Desktop GUI release 는 v2.2.4 로 재시도합니다.

### Fixed

- **GUI backup bridge compatibility**: 기존 `src/lib/vib` public API 의 `backupCreate` export 를 복구해, 아직 `backupCreate` 를 import 하는 GUI 화면도 domain module refactor 이후 정상 build 됩니다.

### Verified

- `npm run build` (vibelign-gui) → passed.
- Bridge contract check → `command string diff: missing=[] extra=[]`, `backupCreate export restored`.
- Branch GUI CI after fix → macOS + Windows passed.

---

## [2.2.3] — 2026-05-12

GUI bridge 구조를 domain module 로 분리하고, 개발 실행 로그의 Rust warning 을 정리한 패치 릴리즈입니다. 사용자-facing 동작은 유지하면서 이후 GUI 기능 확장 시 회귀 위험을 낮췄습니다.

### Changed

- **GUI vib bridge modularization**: `vibelign-gui/src/lib/vib.ts` 의 1,700+줄 command bridge 를 `core`, `docs`, `backup`, `onboarding`, `settings/API key`, `memory/recovery`, `guard/watch`, `errorLogs` domain module 로 분리했습니다.
- **Root import compatibility 유지**: 기존 GUI import 경로 `src/lib/vib` 는 compatibility barrel 로 유지되어 command card, docs, backup, onboarding, settings flow 의 import 변경 없이 동작합니다.

### Fixed

- **Rust dev warning cleanup**: Tauri dev 실행 시 보이던 `PathBuf` unused import warning 과 CAS prune wrapper dead-code warning 을 정리했습니다.

### Verified

- `npm run build` (vibelign-gui) → passed.
- `npm run test` (vibelign-gui) → 2 files / 9 tests passed.
- `cargo check --no-default-features` (vibelign-gui/src-tauri) → passed, Rust warnings cleared.
- Export/import snapshot → `exports=134`, `needed=99`, `missing=[]`.
- Tauri command string diff → `missing=[]`, `extra=[]`.

---

## [2.2.2] — 2026-05-10

DocsViewer 의 HTML 문서 보기 경험과 Windows 경로 안정성을 보강한 패치 릴리즈입니다.

### Added

- **DocsViewer Raw HTML artifact mode**: 선택한 문서를 sandboxed iframe 안의 읽기 쉬운 article-style HTML 로 렌더링합니다. scripts, same-origin, forms 권한은 열지 않아 원문 HTML 을 안전하게 확인합니다.
- **DocsViewer Split mode**: Source 와 Canvas 를 함께 보는 split 탭을 제공하며, 좁은 창에서도 탭 버튼은 항상 표시되고 내부 레이아웃만 1열로 반응합니다.
- **Canvas body preview**: `VisualSection.body_preview` 를 추가해 bullet/checklist/ordered/table row 일부를 원문 순서대로 보존하고, 기존 `heuristic-v2` cache 를 `heuristic-v3` 로 stale 처리합니다.

### Changed

- **Canvas visual renderer**: Canvas 를 문서 원문을 그대로 반복하는 화면이 아니라 `Document Control Map` 으로 재구성했습니다. Outline Source Order → Flow → Decisions → Actions → Risks → Glossary 순서로 보여줍니다.
- **DocsViewer tab affordance**: Source/Easy/Canvas/Raw HTML/Split 중 현재 선택된 탭을 검은 배경과 오렌지 그림자로 강조해 현재 위치를 즉시 알 수 있게 했습니다.
- **Iframe height behavior**: Canvas/Raw HTML/Split 의 고정 세로 제한을 제거하고 artifact 내용량에 따른 높이 추정으로 내부 iframe 스크롤을 줄였습니다.
- **Raw HTML readability**: heading/list/table/code block 스타일을 문서 읽기용으로 정리했습니다.

### Fixed

- **Windows extra doc source picker**: `C:\Repo` 와 `c:\repo\...` 처럼 드라이브/경로 대소문자가 다른 Windows 경로를 프로젝트 밖으로 오판하지 않도록, Windows식 absolute/UNC path 에서만 case-insensitive prefix 비교를 적용했습니다.
- **Split tab visibility regression**: UI 폭이 작아져도 Split 탭 버튼이 사라지지 않도록 수정했습니다.
- **Canvas source omission**: bullet 중심 섹션에서 summary 가 비어 Canvas 에 원문 preview 가 빠지던 문제를 backend artifact contract 로 해결했습니다.

### Verified

- `rtk npm run test -- --reporter verbose` (vibelign-gui) → 9 passed.
- `rtk npm run build` (vibelign-gui) → passed.
- `python3 -m unittest tests.test_doc_sources_cmd tests.test_docs_build_cmd tests.test_docs_visualizer` → 67 passed.
- `cargo test docs` (vibelign-gui/src-tauri) → 28 passed.

---

## [2.2.1] — 2026-05-10

릴리즈 파이프라인 수정 패치 릴리즈입니다. 코드 동작은 v2.2.0 과 동일합니다.

### Fixed

- **GitHub Actions release job 가드**: build job의 마지막 `Post Cache Rust build artifacts` 단계가 실패하면 자산이 다 만들어졌는데도 release job이 `needs:build` fail로 skip 되어 release에 자산 0개로 publish 되던 회귀 — release job 조건에 `always()` 추가로 cache 단계 실패와 무관하게 자산 업로드 진행.
- **Dead config 정리**: `vibelign-gui/src-tauri/tauri.updater.conf.json` 삭제. 워크플로우가 빌드 시점에 `tauri.updater.generated.conf.json` 을 만들어 `--config` 로 머지하므로 이 파일은 어디에도 참조되지 않는 dead config 였음.

---

## [2.2.0] — 2026-05-10

VibeLign 2.2.0 은 **GUI direct bridge (Phase 0+3 PoC) · 통합 에러 로그 뷰 · 자동 백업 가시성 · 다수의 silent 회귀 fix** 를 묶은 마이너 릴리즈입니다. macOS / Windows 모두 자동 혜택을 받는 cross-platform 변경입니다.

### Added

- **vibelign-core 라이브러리 노출 (Phase 0)**: `[lib] crate-type=["rlib"]` + `pub mod ipc` surface 만 노출. 기존 `vibelign-engine` 1-shot 바이너리는 그대로 유지하면서 라이브러리 소비자가 직접 `ipc::handler::handle()` 호출 가능.
- **Tauri ↔ vibelign-core direct bridge (Phase 3 PoC)**: 신규 Tauri command `run_engine_request_direct(request_json)` 가 in-process `handle()` 호출. JSON-in/JSON-out 단일 dispatch 로 모든 EngineRequest variant 처리. GUI 의 `checkpointList`/`undoCheckpoint`/`backupDbViewerInspect`/`backupGraphSummary`/`backupDbMaintenance`/`backupCleanup` 6개 consumer 가 Python `vib` 서브프로세스 없이 엔진 직접 호출. trivial 명령 wall time ~80ms → <5ms.
- **Rust secret_scan pure-function 이전 (Phase 2)**: `vibelign-core/src/secret_scan.rs::scan_unified_diff()` 가 Python `scan_unified_diff_for_secrets` 와 1:1 parity. 환경변수 `VIBELIGN_SECRET_SCAN_RUST=1` 옵트인 시 사용. 골든 fixture 10개 (HC rule 양성 / placeholder skip / allow-marker / multi-`@@` / removed-line / `\ No newline` / HC-wins-keyword / 한글+이모지) 로 parity 보장.
- **GUI 통합 에러 로그 뷰**: 새 "에러로그" 탭 (`pages/ErrorLogs.tsx`). `.vibelign/logs/{cli,gui}-error-*.jsonl` 통합 표시. 종류 필터 (전체/CLI/GUI), 행 클릭 시 raw JSON 상세 모달, **🐛 GitHub 이슈로 보고** 버튼 (단일/다중 선택 — 한 이슈로 묶기 또는 각각 별도 탭), **🗑 정리** 버튼으로 수정 완료된 에러 즉시 클리어.
- **자동 백업 실패 가시화**: post-commit hook (`internal_post_commit_cmd.py`) 이 더 이상 silent skip 하지 않음. 실패 시 stderr 출력 + 통합 에러 로그 (`record_cli_error`) 기록. 사용자가 `vib history` 가 stale 임을 즉시 인지.

### Changed

- **post-commit hook 마커 v2 → v3**: 쉘 템플릿이 `>/dev/null 2>&1` → `>/dev/null` 로 변경되어 stderr 가 git terminal 에 보임. 기존 v1/v2 설치는 다음 `vib start` 시 자동 v3 으로 갱신.
- **3-writer DB concurrency 입증**: WAL + busy_timeout=5000ms 가 (a) Tauri direct in-process write, (b) Python vib subprocess 1-shot, (c) Rust daemon 동시 접근에서 contention 흡수함을 확인 (500 ops 0 errors).
- **백업 카드 라벨**: `cleanBackupNote` 가 git commit 본문 전체 대신 첫 줄 + 80자로 truncate. RestorePreviewPanel 은 hover tooltip 으로 풀 메시지 보존.
- **plan §3 lever 2 ROI 표 측정 기반 갱신**: scan_cache (json 1ms 로드), watch_state (4ms 로드), anchor_tools (<0.2ms/file), strict_patch (cross-cutting 의존) 모두 실측 결과 incremental Rust 포팅 무가치 확정.

### Fixed

- **`vib memory show` FileNotFoundError**: `save_memory_state` 의 tmp path 가 두 프로세스 동시 호출 시 race 로 사라지는 문제 — pid + uuid 로 unique 화. (이전 에러 로그 누적 10건의 주범).
- **`vib doctor | head` BrokenPipeError**: CLI main 에 `signal.SIGPIPE = SIG_DFL` 등록 (Unix 표준 도구 동작). Windows 는 SIGPIPE 미존재로 no-op.
- **RUST_ENGINE_INTEGRITY_FAILED: integrity manifest missing**: `target/{debug,release}` dev 빌드 경로에서 `.sha256` 매니페스트 누락 시 자동 재생성. Windows NTFS case-preserving 대비 case-insensitive 매칭. 번들/설치본 경로는 기존대로 명시 실패 (빌드/배포 누락 신호 보존).
- **GUI unhandledrejection (`listeners[eventId].handlerId`)**: CodemapCard 의 `listen()` cleanup 패턴이 React StrictMode + Vite HMR 의 double cleanup 시 race — Onboarding.tsx 의 idempotent 패턴 (`let unlisten; ...; unlisten?.()`) 으로 통일.
- **홈 카드 그리드 1fr 1fr 불균형**: SortableCardWrapper 에 `width:100%` + `minWidth:0` 추가. dnd-kit transform + 카드별 다른 콘텐츠 폭이 합쳐지면 좌/우 컬럼이 불균형하게 보이던 회귀 수정.

### Verified

- `cargo test --manifest-path "vibelign-core/Cargo.toml"` → 90 passed (이전 74 대비 +16: secret_scan parity 10 + handler/protocol 2 + module unit 4).
- `pytest` 영향 받는 15 suite → 188 passed, 1 skipped.
- `cargo build --manifest-path "vibelign-gui/src-tauri/Cargo.toml"` → 0 errors.
- `npx tsc --noEmit` (vibelign-gui) → No errors.
- `cargo run --release --example concurrency_smoke` → 500 ops PASS, 0 contention errors.
- 실 엔진 e2e 스모크: 6 GUI consumer 모두 raw response 의 모든 parser 필드 정상 라운드트립. secret_scan ASCII / 한글+이모지 path 양쪽 동일 finding.

### Migration

- 기존 사용자: 자동 적용. post-commit hook 은 `vib start` 또는 hook reinstall 시 v3 으로 자동 갱신됨.
- 옵션 `VIBELIGN_SECRET_SCAN_RUST=1`: 명시 ON 시에만 Rust secret scan. 기본 Python.
- 환경변수 `VIBELIGN_PROJECT_SCAN_RUST=0`: Python/fd fallback 강제. 기본 Rust.

---

## [2.1.11] — 2026-05-08

VibeLign 2.1.11 은 **Rust project_scan 기본 라우팅, GUI Explain 분류 보정, CLI help/manual 정합성 개선**을 포함한 릴리즈입니다.

### Added

- Rust 엔진에 `project_scan` IPC를 추가하고 Python CLI가 기본적으로 Rust scan 결과를 사용하도록 연결했습니다.
- `iter_source_file_records()`를 추가해 Rust scan의 `category/imports` metadata를 `scan_cache`가 재사용할 수 있게 했습니다.
- `vib -h`와 `vib manual`에 최근 추가된 `backup-*`, `show`, `doc-sources`, `docs-enhance`, `bench`, `manual` 안내를 빠짐없이 노출합니다.

### Changed

- `scan_cache.incremental_scan()`이 Rust scan metadata를 우선 사용하되, 실패 시 기존 Python/fd fallback을 유지합니다.
- GUI Tauri command 모듈에 anchor 경계를 추가해 VibeLign Explain/CodeMap에서 backend command 파일을 더 명확하게 식별합니다.

### Fixed

- GUI Explain Report에서 `vibelign-gui/src-tauri/src/commands/*.rs`가 `화면`으로 잘못 표시되던 문제를 `명령/설정`으로 보정했습니다.
- stale `.vibelign/project_map.json`이 명확한 command 경로를 `ui`로 덮어쓰지 못하도록 우선순위를 조정했습니다.
- `.mcp.json`, `pyproject.toml`, `vib.spec`, `/commands/`, `/cli/` 경로가 Explain에서 명령/설정 파일로 분류됩니다.

### Verified

- Rust project_scan consumer/fallback focused tests 통과.
- Explain/GUI contract focused tests 통과.
- CLI help/manual coverage tests 통과.
- `GIT_MASTER=1 git diff --check` 통과.

---

## [2.1.10] — 2026-05-05

VibeLign 2.1.10 은 **Gemini 무료 등급 429 에러 안내 개선** 핫픽스입니다.

### Changed

- `vib docs-enhance` 가 Gemini HTTP 429 (분당 한도 초과) 를 만나면, 이제 무료 등급 한도와 유료 전환 안내, 그리고 자동 재시도를 늘리는 환경변수(`GEMINI_HTTP_MAX_ATTEMPTS`, `GEMINI_HTTP_RETRY_CAP`) 사용법을 함께 보여줍니다.
- 동일 메시지가 GUI 의 AI 요약 버튼 에러 영역에도 그대로 표시되며, Google AI Studio 업그레이드 URL 은 클릭 가능한 버튼으로 자동 변환됩니다 (GUI 측 코드 변경 없음).

### Verified

- `_format_http_error` 합성 429 입력으로 메시지 포맷 검증.
- GUI 의 `whiteSpace: pre-wrap` + URL 링크화 기존 로직이 새 메시지를 그대로 처리.

---

## [2.1.9] — 2026-05-05

VibeLign 2.1.9 는 **BACKUPS 탭 즉시 로딩과 복원 미리보기 시각 개선**을 담은 GUI QoL 릴리즈입니다.

### Changed

- BACKUPS 탭 재방문 시 마지막 로드된 백업 목록을 메모리 캐시로 즉시 렌더하고, 백그라운드에서 새 데이터를 받아 자동 갱신합니다 (stale-while-revalidate).
- 프로젝트를 여는 즉시 백업 목록을 백그라운드 프리페치하여 BACKUPS 첫 클릭에서도 서브프로세스 콜드 스타트 지연이 보이지 않습니다.
- 복원 미리보기 카드의 텍스트 한 줄을 칩 3개(상대시간 / 파일 수 / 안전 상태)로 시각화했습니다.
- `formatRelativeTime` 헬퍼 추가 (방금 / N분 전 / N시간 전 / N일 전, 7일 이후 절대시간 fallback).

### Verified

- TypeScript 타입 체크 통과.
- BACKUPS 탭 즉시 렌더 / 저장·복원 후 목록 갱신 수동 검증.

---

## [2.1.8] — 2026-05-05

VibeLign 2.1.8 은 **GUI/CLI API 키 동기화와 복구 후보 AI 추천 안정성**을 보강한 핫픽스입니다.

### Fixed

- GUI와 CLI가 같은 `api_keys.json` 저장소를 기준으로 API 키 저장/삭제 상태를 일관되게 반영합니다.
- 삭제한 키는 VibeLign 삭제 override로 기록되어 외부 환경 변수에 남아 있어도 GUI/CLI에서 삭제된 상태로 취급됩니다.
- 새로 저장한 Gemini 키가 오래된 `GEMINI_API_KEY` 환경 변수보다 우선되도록 key precedence를 조정했습니다.
- GUI `복구 후보 추천 보기`가 Settings에 저장된 AI 키를 `vib recover --recommend`에 전달해 Gemini 추천이 즉시 붙도록 했습니다.
- Windows에서 `%APPDATA%`가 없는 실행 환경에서도 GUI가 CLI와 동일하게 `%USERPROFILE%\AppData\Roaming\vibelign\api_keys.json` fallback을 사용합니다.

### Security

- `vib config` 임시 저장 모드가 실제 API 키를 터미널에 출력하지 않도록 막았습니다.
- GUI 마이그레이션 후 레거시 `gui_config.json`에 남은 API 키 복사본을 제거합니다.
- Settings 화면에서 저장된 키 앞부분도 노출하지 않고 `값 숨김`으로만 표시합니다.

### Verification

- Focused key/recovery tests passed locally.
- GUI production build passed locally.
- Tauri key-command compile check passed locally.
- Diff/working-tree secret pattern scans found no real API keys.

---

## [2.1.7] — 2026-05-05

VibeLign 2.1.7 은 **패키징된 GUI의 초기 저장이 Rust/SQLite 엔진을 확실히 사용하도록 고친 핫픽스**입니다.

### Fixed

- Windows GUI에서 “초기 프로젝트 시작하기”를 눌렀을 때 번들된 `vibelign-engine.exe`를 찾지 못해 Python legacy 백업으로 fallback될 수 있던 경로를 수정했습니다.
- PyInstaller onedir 구조의 `_internal/vibelign/_bundled/vibelign-engine(.exe)`를 Tauri GUI와 Python CLI 양쪽에서 Rust engine 후보로 인식합니다.

### Verification

- CLI `vib start` smoke에서 `.vibelign/vibelign.db`와 `.vibelign/rust_objects/` 생성 확인.
- CLI `vib checkpoint --json` smoke에서 legacy checkpoint 파일 생성 없이 Rust object 저장 확인.
- Focused Python checkpoint/start tests and Tauri `vib_path` tests passed locally.

---

## [2.1.6] — 2026-05-05

VibeLign 2.1.6 은 **Session Memory / Recovery 안내 노출 정리**와 **Windows handoff 안정화**를 담은 릴리즈입니다.

### Added

- GUI Manual 탭에 `세션 메모리`와 `복구 옵션` 항목 카드를 추가했습니다.
- `vib -h`, `vib memory -h`, `vib manual memory`, `vib manual recover`에서 초보자도 이해하기 쉬운 설명을 표시합니다.
- `vib memory <TAB>`에서 `show`, `next`, `proposal-create`, `proposal-accept` 같은 하위 명령과 자주 쓰는 옵션이 자동완성됩니다.
- 자동 추정 handoff 일 때 `PROJECT_CONTEXT.md` 상단에 `work_memory.json` 확인 경고를 표시합니다.

### Changed

- GUI의 AI 이동 카드에서 `--compact`와 `--handoff` 토글을 제거하고, `TRANSFER` 버튼이 항상 handoff 흐름으로 실행되게 했습니다.
- GUI Manual 상세 화면이 실제 CLI 사용법과 서브명령/옵션을 그대로 보여주도록 개선했습니다.

### Fixed

- Windows에서 `vib transfer --handoff` 실행 시 CP949 디코딩과 `stdout=None` 때문에 실패하던 경로를 안정화했습니다.
- `vib manual memory`가 `'memory' 커맨드를 찾을 수 없어요.`로 실패하던 manual registry 누락을 수정했습니다.
- GUI transfer 실패 시 실제 CLI stdout/stderr가 보이도록 해 Windows 디버깅 가능성을 높였습니다.

### Verification

- `86 passed` focused Python regression suite, including Windows-sensitive transfer/handoff tests.
- GUI production build passed with `rtk npm run build`.

### Changed

- **Checkpoint engine cutover**: `vib checkpoint`, `vib history`, and `vib undo` now use the Rust/SQLite checkpoint engine by default, with visible Python fallback for environment failures.
- Legacy JSON checkpoints under `.vibelign/checkpoints/` are preserved on disk, but they are **not automatically imported or merged** into the new SQLite-backed default history/list/restore path. Back up `.vibelign/checkpoints/` before upgrading if you need old checkpoint snapshots.

---

## [2.0.1] — 2026-04-18

PyPI 렌더링 한정 문서 패치.

### Fixed

- README 의 `README.ko.md`, `CHANGELOG.md`, `MIGRATION_v1_to_v2.md` 상대 링크를 PyPI 페이지에서 404 나지 않도록 **절대 GitHub 링크** 로 변경. GitHub 에서는 기존과 동일하게 동작.

### Notes

- 코드 변경 없음. CLI / GUI 동작 동일.
- v2.0.0 의 GUI 바이너리 (`.dmg` / `.exe` / `.msi`) 는 그대로 사용 가능. v2.0.1 은 PyPI 업로드만 의미를 가집니다.

---

## [2.0.0] — 2026-04-18

VibeLign 2.0 은 **데스크톱 GUI 런칭** + **MCP/Patch 모듈화** + **AI 옵트인 체계** 를 담은 메이저 릴리즈입니다.
1.x 사용자는 [MIGRATION_v1_to_v2.md](./MIGRATION_v1_to_v2.md) 를 먼저 확인해주세요.

### Added

- **VibeLign GUI (macOS / Windows)** — Tauri 기반 데스크톱 앱
  - Doctor 페이지: 원클릭 진단·자동 적용 (`vib doctor --apply` 번들)
  - 앵커카드: 앵커 삽입 + intent/aliases 재생성 (코드 기반 / AI 기반, `--force` 로 기존 AI 결과 덮어쓰기)
  - DocsViewer: 프로젝트 문서 AI 보강, 개별 문서별 요약
  - Settings: API 키 관리, AI 옵트인 전역 토글
- **MCP 서버 모듈 재구성** — `vibelign/mcp/` 아래 dispatch/handlers/tool_specs 분리
- **Patch 모듈 분리** — `vibelign/patch/` (builder / handoff / preview / targeting / steps / output / render …)
- **AI 보강 옵트인 체계** — consent UI 제거 → 설정 토글로 일원화
  - 해시 캐시 + 프로그레스바로 진행 상황 가시화
  - Anthropic / OpenAI / Gemini 자동 선택
- **Docs AI enhance 커맨드** — `vib docs-enhance` (문서 요약 래퍼)
- **onedir 런타임 번들링** — PyInstaller `onefile → onedir` 전환으로 GUI 콜드스타트 제거
- **앵커 `_source` 필드** — `anchor_meta.json` 에 `code / ai / manual / ai_failed` 구분 도입, AI/수동 결과를 코드 기반 재생성으로부터 보호

### Changed

- **BREAKING**: `vibelign.vib_cli` → `vibelign.cli.vib_cli` (모듈 경로 이동)
- **BREAKING**: `vibelign.mcp_server` → `vibelign.mcp.mcp_server`
- Doctor 출력 포맷 개선 (score / status / issue 구조 일원화)
- 패치 스위트가 `target_anchor` 기반 소형 패치 우선 — 거대 파일 전면 재작성 방지

### Fixed

- Windows `git` exit 129 회피
- GUI IPC env allowlist + api_keys 파일 권한 강화
- 앱 이동 시 CLI 래퍼 타겟 경로 자동 재검증
- AI 요약 Gemini 기본 모델 503 회피 (`2.0-flash` 로 다운)
- 패치 서제스터 AI 선택 게이트 강화 + 음수 후보 필터

### Performance

- Doctor / DocsViewer 콜드스타트 제거 (PyInstaller onedir)
- `vib` 프리워밍 + `ai-enhance status` 메모리 캐시
- docs visual contract 메모리 캐시 (클릭당 `vib` subprocess 스폰 제거)

### Security

- GUI IPC env allowlist 적용
- `~/.vibelign/api_keys` 파일 권한 제한
- CLI 설치 게이트 추가

---

## [1.7.2] — 2026-03-22

v1.x 의 마지막 CLI-only 릴리즈. 상세 변경사항은 `git log v1.7.2-final` 참고.
