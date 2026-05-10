# Changelog

본 파일은 VibeLign 의 주요 변경사항을 기록합니다.
포맷은 [Keep a Changelog](https://keepachangelog.com/) 를 따르며,
버전 체계는 [Semantic Versioning](https://semver.org/) 을 준수합니다.

---

## [Unreleased]

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
