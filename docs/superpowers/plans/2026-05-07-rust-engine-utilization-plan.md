# Rust 엔진 120% 활용 계획

**작성일**: 2026-05-06 (내일 작업용)
**대상**: vibelign-core (Rust 엔진) + vibelign(Python) + vibelign-gui(Tauri)

**진행 상태 — 2026-05-08 세션 종료 기준**

- ✅ Phase -1 결정 고정 완료: per-root daemon, official dual-mode, V2 daemon envelope `{request_id, payload}`, request-level DB open/close, `checkpoint_has_changes` Python-only 유지.
- ✅ Phase 1 Unix/macOS daemon 골격 구현/검증 완료: `vibelign-engine --daemon --root`, Unix socket JSONL, `Shutdown`/`EngineVersion`, root isolation, PID/socket lifecycle, idle timeout, Python daemon client, daemon opt-in routing, CLI/MCP smoke coverage.
- ✅ 선행 리팩토링 완료: Tauri command 분리, Python `rust_engine/` 패키지 분리, Rust IPC `protocol.rs`/`handler.rs` 분리, fallback policy helper 분리.
- ✅ 안전장치 완료: daemon runtime artifacts checkpoint/project-scan 제외, `.vibelign/engine.log` rotation, unsupported transport 일관 fallback(`RUST_ENGINE_DAEMON_UNSUPPORTED`).
- 🚧 남은 Phase 1 작업: Windows named pipe transport/lifecycle/update 검증, Windows 실제 머신 smoke. macOS engine-only / `vib history` CLI / GUI 4-hop end-to-end benchmark 는 2026-05-08~2026-05-09 debug build 기준으로 기록됨 (§Phase -1 benchmark snapshot 참조). GUI bench 결론: Python sidecar startup(~70~80ms) 이 4-hop 을 지배하므로 daemon ON/OFF 차이는 read 9~12% / write ~30% 수준. 사용자 체감 즉각성은 Phase 3(Tauri↔core 직결) 또는 Python keepalive 가 같이 와야 실현됨이 측정으로 재확인. macOS-safe router consumer matrix 는 `tests/test_checkpoint_router_consumers.py` / `tests/test_vib_history_undo_cmd.py` 로 12개 consumer 보강됨(auto_backup/action_engine/transfer/recovery_signals/hook_setup/vib history/vib undo + 2026-05-09 추가: vib_checkpoint_cmd/strict_patch/recovery_sandwich/recovery_apply_restore_files/vib_backup_db_maintenance).
- 🚧 Phase 2 진행: Rust `project_scan` 이전 전 Python behavior contract fixture 추가(`tests/test_project_scan.py`) 및 Rust IPC `project_scan` command + Python wrapper(`scan_project_with_rust`) 1차 구현 완료. `iter_source_files()` 는 기본적으로 Rust scan 결과를 먼저 사용하고, `VIBELIGN_PROJECT_SCAN_RUST=0` 이면 기존 Python/fd 경로만 사용함. 검증된 consumer: `anchor_tools.preview_anchor_targets()`, `scan_cache.incremental_scan()` 경유 `_build_project_map()`, `vib scan` anchor validation. 2026-05-09 추가: `secret_scan` Rust pure-function 이전 + Python 옵트인 라우팅 완료 — `vibelign-core/src/secret_scan.rs::scan_unified_diff()` 구현, `regex` crate 의존 추가, `EngineRequest::SecretScanDiff{diff_text, path_hint}` + handler + `EngineResponse::SecretScanDiffOk{result, path_hint, findings}` 와이어링. Python 측 `secret_scan_diff_request`/`parse_secret_scan_diff`/`scan_secrets_diff_with_rust` 추가하고 `vibelign/core/secret_scan.py::_scan_unified_diff_routed` 가 `VIBELIGN_SECRET_SCAN_RUST=1` 일 때만 Rust 호출, warning/payload shape 불일치 시 Python fallback. `scan_staged_secrets` / `scan_all_history` 가 routing helper 를 사용하도록 전환. Python `scan_unified_diff_for_secrets` 출력을 권위로 `tests/fixtures/secret_scan_diffs/*.{diff,expected.json}` 10개 골든 (empty / 모든 high-confidence rule 양성 / placeholder skip / allow-marker / multi-`@@` line tracking / removed-line ignore / `\ No newline` 처리 / HC-wins-over-keyword / 한글+이모지 path_hint 라운드트립) 으로 commit. Python `tests/test_secret_scan_goldens.py` 가 (a) parametrize 로 Python 출력↔골든 핀, (b) routing helper 가 기본 OFF/Rust ON/Rust 실패 fallback 3 경로를 mock 검증. `cargo test` 90 total (이전 74; secret_scan 10 parity + 1 handler smoke + 1 protocol parse + 4 module support 추가). 실 엔진 e2e 스모크 통과: ASCII / 한글+이모지 path 모두 daemon OFF / `VIBELIGN_SECRET_SCAN_RUST=1` 양 경로에서 동일 finding 산출. 다음 세션 범위: git invocation 이전(`scan_staged_secrets`/`scan_all_history` 의 `_run_git` 자체를 Rust 로) 또는 Phase 2 다음 모듈 (`scan_cache`/`watch_state`/anchor parser) 또는 Phase 0+3 GUI 직결.
- 🛑 Phase 2 incremental 포팅 트랙 마감 (2026-05-09): scan_cache / anchor_tools / strict_patch 측정 결과 모두 단일 세션 포팅 가치 없음 (§3 갱신 표 참조). 남은 동력은 (A) SQLite 등 구조적 재설계 다중 세션, (B) Phase 1 Windows / Phase 3 PROJECT_CONTEXT 분리 등 별 트랙. project_scan / secret_scan 1차는 그대로 유지.
- 🚧 Phase 3 PoC 완료: vibelign-core 라이브러리 노출 + Tauri direct bridge for `checkpoint_list` 1차 슬라이스. `vibelign-core/Cargo.toml` 에 `[lib] crate-type=["rlib"]` + `src/lib.rs` 가 `pub mod ipc` 로 surface 한정 노출(다른 모듈은 private 유지). `src/main.rs` 는 `vibelign_core::ipc::*` 를 consume 하는 thin entrypoint 로 슬림화. `vibelign-gui/src-tauri/Cargo.toml` 에 `vibelign-core = { path = "../../vibelign-core" }` 의존 추가. 신규 Tauri command `commands::vib_bridge::run_engine_request_direct(request_json)` 가 `tauri::async_runtime::spawn_blocking` 안에서 `vibelign_core::ipc::handler::handle()` 호출 → JSON-in/JSON-out (단일 command 로 모든 EngineRequest variant 처리). 프런트 `vibelign-gui/src/lib/vib.ts::checkpointList(cwd)` 가 `runVib(["checkpoint","list","--json"])` → `callEngineDirect({command:"checkpoint_list",root:cwd})` 으로 전환 (다른 호출 사이트는 그대로 `run_vib` 유지, PoC 범위는 1 consumer). `cargo build --lib` / `cargo build --bin vibelign-engine` / Tauri `cargo build` 모두 grün, 기존 `cargo test` 90 passed 유지.
  - **Phase 3 PoC bench (2026-05-09 macOS release build, `cargo run --release --example bench_engine_direct`)**: 
    - 작은 repo (`/tmp/vib-bench-list`, 1 checkpoint, OS file cache warm): direct `handle()` median **0.001ms** (mean 0.003ms, n=50) vs 1-shot subprocess median **3.203ms** (mean 12.402ms, max 452.713ms 콜드, n=50) — **subprocess/direct = 2196.8x**, per-call 약 3ms 순수 spawn 오버헤드. 
    - 큰 repo (VibeLign 본 repo, 다수 checkpoint): direct median **134.413ms** vs subprocess median **147.046ms** (n=30) — engine work 자체가 wall 의 ~91% 를 차지, 그래도 13ms 절감. 
    - **결론**: 엔진 작업이 trivial 한 명령(EngineInfo, 작은 DB list, doctor plan-only)일수록 direct bridge 효과가 압도적이고 (수~수백배), heavy I/O 명령은 절감폭이 13ms 수준. GUI E2E 전체에서는 §Phase -1 GUI bench 가 보여준 Python sidecar ~70~80ms 가 추가로 사라지므로 **사용자 체감으로 의미 있는 80ms 단축**이 확정. Phase 3 의 가치는 측정으로 입증됨.
  - 2026-05-09 추가: **3-writer DB concurrency smoke 통과**. `vibelign-core/examples/concurrency_smoke.rs` 가 `std::thread::scope` 로 (a) in-process `handle(CheckpointCreate)` writer 1개, (b) 1-shot subprocess `CheckpointCreate` writer 1개, (c) in-process `CheckpointList` reader 4개, (d) 1-shot subprocess `CheckpointList` reader 4개 = 10 동시 worker 를 띄워 같은 `vibelign.db` 를 두드림. 50-iter (총 500 ops) 결과: 모두 PASS, 0 errors, 3.04s wall. WAL + `busy_timeout=5000ms` 가 contention 을 흡수함을 입증. plan §5.3 / §7 의 "WAL dual-mode" 가 dual→triple-mode 까지 안전.
  - 2026-05-09 추가: Phase 3 PoC consumer #2 마이그레이션 — `vibelign-gui/src/lib/vib.ts::undoCheckpoint(cwd, checkpointId)` 가 `runVib(["undo","--checkpoint-id",id,"--force","--json"])` → `callEngineDirect({command:"checkpoint_restore",root:cwd,checkpoint_id:id})`. CLI 의 `--force` 는 prompt skip 용이고 engine 에는 prompt 없으므로 direct = force-equivalent. 응답 shape `{status, result:"restored", checkpoint_id}` 는 호출자 `Promise<unknown>` 으로만 소비. `Checkpoints.tsx` / `backupRestore` 두 consumer 자동 혜택.
  - 2026-05-09 추가: Phase 3 PoC consumer #3 + #4 마이그레이션 — `backupDbViewerInspect` / `backupGraphSummary` 가 `runVib(["backup-db-viewer","--json"])` / `runVib(["backup-graph-summary","--json"])` → `callEngineDirect({command:"backup_db_viewer_inspect"|"backup_graph_summary", root:cwd})` 로 전환. shape parity 입증: Python wrapper `{ok:true, ...}` vs engine raw `{status:"ok", ...}` 의 차이는 ok 필드뿐이고 TS parser 가 `raw.ok === false` (explicit) 만 실패로 보므로 engine raw 가 ok 없이도 통과. 캐시 정책(`backupGraphSummaryCache`/`backupDbViewerInspectCache`) 보존. e2e 스모크: 두 명령 모두 직접 호출 시 `db_exists`/`root`/`warnings`/`db_path`/`db_file`/`schema_version`/`checkpoint_count` 등 TS parser 가 읽는 모든 필드 정상 라운드트립.
  - 2026-05-09 추가: Phase 3 PoC consumer #5 + #6 마이그레이션 — `backupDbMaintenance(cwd, apply)` / `backupCleanup(cwd)` direct 전환. #5 는 단일 dispatch (`{command:"backup_db_maintenance", root, apply}`), apply=true 시 cache invalidate 보존. #6 는 컴포지트 — Python `vib backup-cleanup` 이 `apply_retention` + `maintain_backup_db(apply=true)` 두 엔진 호출 후 `{ok, retention, maintenance}` wrap 하던 것을 TS 측에서 두 `callEngineDirect` 순차 실행 후 같은 shape 로 래핑. retention 필드 매핑(`pruned_count → count` 등 5개) 은 Python `parse_retention` 이 하던 일을 TS 에서 동일하게 재현. e2e 스모크: 양쪽 엔진 raw 응답 필드(`mode`/`db_exists`/`planned_action`/`vacuum_recommended`/`checkpoint_recommended` + `pruned_count`/`planned_count`/`planned_bytes`/`reclaimed_bytes`/`partial_failure`) 모두 TS parser/매핑 대상 필드와 일치. **Phase 3 PoC consumer 누적 6개**.
  - 2026-05-09 결정: **`checkpointCreate` 는 Phase 3 direct bridge 후보에서 제외**. Python `vib checkpoint <msg> --json` 은 (a) 엔진 `CheckpointCreate` 호출 외에 (b) `_build_context_content(root)` 으로 `PROJECT_CONTEXT.md` 자동 재생성 (`vib_transfer_cmd.py:1067`+, 1000+ LOC 비즈니스 로직), (c) 기존 handoff 블록 덮어쓰기 경고 까지 한 단위로 묶어 수행. (b) 는 VibeLign 의 핵심 가치(AI 세션 핸드오프 문서) 라서 GUI 체크포인트 생성 시 빠지면 stale. direct 만 분리 마이그레이션 시 사용자 체감 응답 ~80ms 단축은 가능하지만 PROJECT_CONTEXT 가 stale 화. 이전 4개 consumer 가 모두 "순수 엔진 호출" 이었던 것과 다른 카테고리. **결정**: Python wrapper 그대로 유지. write-path GUI 호출은 사용자 수 분~수십 분에 한 번이고, 자동화 가치 손실이 응답 단축 가치보다 큼. Phase 2 의 `_build_context_content` Rust 이전(1000+ LOC) 이 별 PR 로 진행되거나, GUI side-effect 분리 정책이 정해질 때까지 보류.
  - Phase 3 PoC 트랙 누적 4 consumer (`checkpointList`/`undoCheckpoint`/`backupDbViewerInspect`/`backupGraphSummary`) 마이그레이션 + concurrency safety + bench 데이터로 Phase 3 가치 입증은 완료. 트랙은 안정 상태. 다음 세션 후보: Phase 2 다음 모듈(`scan_cache`/`watch_state`/anchor parser, advisor 신규 점검 필요한 fresh 모듈 포팅), Phase 1 Windows named pipe transport (Win 머신 필요), 또는 PROJECT_CONTEXT 갱신 로직 별도 분석/Rust 이전.
  - 2026-05-12 추가: Phase 3 PoC consumer #7~#12 마이그레이션 — config 서브시스템 read/write 양방향 + anchor 메타 read/write 양방향. 신규 Rust 모듈 `src/config.rs` (`ai_enhancement_status`/`auto_backup_status` + 대응 `set_*`) 와 `src/anchor_meta.rs` (`list_anchor_meta`/`set_anchor_intent`) 추가. `EngineRequest` 에 5개 신규 variant (`AiEnhancementStatus`/`AutoBackupStatus`/`AnchorListMeta`/`AiEnhancementSet`/`AutoBackupSet`/`AnchorSetIntent`) + 공유 `EngineResponse::BoolStatusOk { result, enabled }` + `AnchorListMetaOk { meta }` + `AnchorSetIntentOk { anchor_name, entry }` 추가. GUI 측 `getAiEnhancement`/`setAiEnhancement` (docs.ts), `getAutoBackupOnCommit`/`setAutoBackupOnCommit` (backup.ts), `anchorListMeta`/`anchorSetIntent` (anchor.ts) 6개 함수 모두 `runVib` → `callEngineDirect` 전환. **캐시 hack 2개 영구 삭제** (`aiEnhancementCache`, `autoBackupOnCommitCache`) — 이전 PyInstaller cold-start 대응으로 추가됐던 Doctor/Settings 페이지 캐시 정책이 더 이상 필요 없음. **Phase 3 PoC consumer 누적 6 → 12**. 남은 `runVib` 호출은 11 → 8 (audit/recovery/doctor/handoff write 등 multi-session 트랙 후보). 파리티: config.yaml line-replace, db_meta upsert, anchor_meta normalize (canonical 7필드 + 비-string 필터 + 빈 리스트 drop), pretty-JSON + trailing `\n` 모두 Python `hook_setup`/`auto_backup`/`anchor_tools` 의 동작과 1:1. 신규 cargo 테스트 26개 (90 → 116).
  - 2026-05-12 부수 정리: vib.ts 1784 → 3줄 (re-export bridge) 모듈 분할 후 deslop pass — 중복 `getVibPath` 삭제 (`onboarding.ts` 내 정의는 `index.ts`에서 export 되지 않아 도달 불가능했음), `backupCreate` thin wrapper 삭제 (단일 caller `BackupDashboard.tsx` 가 `checkpointCreate` 직접 사용하도록 전환, 반환 타입 `unknown` → `CheckpointCreateResult` 로 강화). Rust `cas.rs::prune_unreferenced` 에 `#[allow(dead_code)]` 추가 (test-only public API 의도적 유지).
  - 2026-05-12 추가: Phase 3 PoC consumer #13 마이그레이션 — `memorySummary` (SessionMemoryCard mount). audit logging parity 가 핵심이라 multi-session 트랙으로 분류됐던 작업을 단일 세션에 완료. 신규 Rust 모듈 두 개: `src/memory_audit.rs` (project_root_hash via SHA256[:16] / chrono 마이크로초 ISO timestamp / sequence_number max+1 / O_EXCL file lock with 5s deadline + 30s stale 제거 / sort_keys=True 직렬화) 와 `src/memory_state.rs` (work_memory.json passthrough + defaults, schema_version 미래 버전이면 downgrade_warning 자동 설정). 신규 dependency `sha2 = "0.10"`. `EngineRequest::MemorySummaryRead { root, tool }` + `EngineResponse::MemorySummaryReadOk { payload: Value }`. handler 가 load_payload → build audit event → append → return payload 한 단위로 처리 (Python parity). GUI 측 `memorySummary` 가 `tool="vib-gui"` 로 호출해 audit 로그에서 GUI/CLI 구분 가능 (다운스트림 aggregator/retention 은 양쪽 다 카운트). 신규 cargo 테스트 18개 (116 → 134). wire smoke 에 13 assertion 추가 (총 46) — payload passthrough + 2회 호출 시 sequence 1/2/project_root_hash 16-hex 검증. **Phase 3 PoC consumer 누적 12 → 13**. 남은 `runVib` 호출 8 → 7 (doctor/recovery/handoff write/manual/scan/anchor progress 등 multi-session 후보).
  - 🆕 2026-05-13 신규 트랙 진입 (consumer migration 외): **patch_suggester tokenizer leaf hot-path Rust port** (design phase 완료, 코딩 미진입). 트랙 B (multi-session) 진입 시 doctor vs recovery ROI 측정에서 `vib recover --preview --json` warm 4.7s vs `vib doctor --json` 118ms (40×) → recovery 우선. 그러나 cProfile 결과 4.7s 중 **86% (`_score_all_files` 13.3s) 가 `patch_suggester` 한국어 토큰 분해/정규화 hot loop** (`_normalize_korean_token` 609k 호출, `_decompose_korean_compound` 705k 호출, `_expand_token` 609k 호출) 에서 소비됨이 드러남. 7-candidate framing 자체가 너무 좁았음 (TS callsite 기준이라 hot path 를 못 봤음) — recovery 가 무거운 게 아니라 patch_suggester 가 무거운 것. **1 포팅 → 5 consumer 동시 가속**: `codespeak.py` (AI suggest), `recovery/planner.py` (recover preview), `patch/patch_contract_helpers.py` (contract tokenize), `patch/patch_targeting.py` (resolve target), `commands/vib_bench_cmd.py` (bench). Leaf 6 함수 (~60 LOC: `_decompose_korean_compound`/`_split_identifier_parts`/`_normalize_korean_token`/`_expand_token`/`tokenize`/`_intent_tokens`) + const table 113 entries (`_TOKEN_ALIASES` 37 + `_KOREAN_ALIAS_KEYS` 37 + `_KOREAN_PARTICLE_SUFFIXES` 39), IPC/AI/write 0개 → secret_scan 선례와 동일 모양으로 단일 세션 가능. Orchestration (`_score_all_files`, 328 호출) 은 Python 유지 — leaf 가속만으로 ~90% 시간 회수. 상세: `2026-05-13-patch-suggester-tokenizer-rust-port-plan.md`. 다음 세션 단계 1~5 (golden fixtures → Rust 모듈 → opt-in flag → wire smoke → bench 재측정).

**마지막 검증 스냅샷**

- `uv run --with pytest python -m pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py tests/test_mcp_checkpoint_handlers.py tests/test_local_checkpoints.py tests/test_gui_cli_contracts.py -q` → 108 passed (2026-05-08 baseline).
- `uv run --with pytest python -m pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py tests/test_mcp_checkpoint_handlers.py tests/test_local_checkpoints.py tests/test_gui_cli_contracts.py tests/test_checkpoint_router_consumers.py tests/test_vib_history_undo_cmd.py tests/test_secret_scan.py tests/test_secret_scan_goldens.py tests/test_project_scan.py -q` → 161 passed, 1 skipped (2026-05-09 secret_scan e+f 옵트인 라우팅 + 한글/이모지 fixture 추가 후).
- `cargo test --manifest-path "vibelign-core/Cargo.toml"` → 134 passed (2026-05-12 consumer #13 + memory_audit/memory_state 모듈 추가 후, 이전 74→89→90→98→105→111→116→127→134).
- `cargo check --manifest-path "vibelign-gui/src-tauri/Cargo.toml"` → 0 errors, 2 crates compiled (2026-05-12 신규 EngineRequest variant 5개 추가 후 incremental).
- `npx tsc --noEmit` (vibelign-gui) → No errors found (2026-05-12 consumer #7~#12 direct bridge 마이그레이션 + vib.ts 모듈 분할 deslop pass 이후).
- `cargo run --release --example concurrency_smoke -- /tmp/vib-concurrency-smoke 50` → 500/500 ops PASS, 0 errors (2-writer + 8-reader, 50-iter, 3.04s).
- `uv run python -m compileall vibelign/core/checkpoint_engine/rust_engine tests/test_checkpoint_rust_engine.py` → passed.

---

## 1. 한 줄 요약

> Rust 엔진은 **천재 직원**이지만, 지금은 **백업 업무**만 시키고 있고 **매번 출근→퇴근**을 반복 중. 상주시키고, 더 많은 일을 맡기고, 중간 다리(Python)를 줄이면 120% 활용 가능.

---

## 2. 현재 상태 (진단)

### 2.1 Rust 엔진(vibelign-core)이 하는 일
- 단일 도메인: **백업/체크포인트/복원/리텐션/DB 점검**만 (~5,938 LOC)
- 진입점: `vibelign-engine` 단일 바이너리
- 호출 방식: **stdin → JSON 한 번 → stdout → 종료** (1회성 CLI)
- 위치: `vibelign-core/src/main.rs:11-31`, `ipc/protocol.rs`

### 2.2 Python(`vibelign/core/`)이 떠안고 있는 핫 패스
- 파일 스캔: `project_scan`, `secret_scan`, `docs_scan`
- 캐시 IO: `scan_cache` (335KB), `watch_state` (1.5MB), `analysis_cache`
- 패치 정확도: `strict_patch`, `patch_validation`, `import_resolver`
- 앵커: `anchor_index.json` (119KB), `anchor_meta.json` (367KB) 파싱

### 2.3 호출 흐름 (현재 4-hop)
```
GUI(클릭) → Tauri(Rust) → vib(Python) → vibelign-engine(Rust 1회성)
```
매 호출마다 Python + Rust 프로세스 둘 다 새로 시작.

---

## 3. 3가지 레버 (ROI 순)

### 레버 1. **Rust를 상주 데몬으로 바꾸기** ⭐ 최우선
**문제**: 명령 한 번에 100~300ms 시작 비용. 큰 레포에서는 호출이 잦으면 누적됨.

**해법**:
- 1회성 CLI → **장수(long-running) 사이드카** 로 전환
- daemon 통신은 socket/named pipe transport 위 JSONL framing 으로 처리
- stdin/stdout JSON 은 V1 1-shot 전용으로 유지
- DB connection lifecycle 결정에 따라 요청 단위 open/close 유지 또는 rusqlite connection/pool 재사용
- 인메모리 anchor index / scan 결과 캐시

**기대 효과**:
- 호출당 ~5-15ms (현 ~150ms 대비 10~30배) — **CLI/MCP 직접 경로 한정**
- GUI 4-hop(`GUI → Tauri → vib(Python) → engine`)은 Python sidecar 가 매번 spawn 하면 체감 거의 없음. **GUI 즉각 반응은 Phase 3 (Tauri 가 vibelign-core 직결) 또는 vib Python keepalive 가 같이 와야 실현됨**
- onedir 사이드카(2026-04-18 완료, warm 0.16s / cold ~1s)와 자연 연결되지만, Python warm 비용이 5ms Rust 위에 그대로 얹힘

**주의**:
- 사이드카 자동 stale 복구 로직 유지 (메모리 기록 참고)
- 데몬 라이프사이클 정책: **owner-less + lazy spawn + idle timeout**
  - 어떤 클라이언트(GUI/CLI/MCP/auto-backup hook)든 first call 시 PID 파일 lock 으로 race-safe spawn
  - 마지막 요청 후 5분 idle 자살 → GUI lifecycle 과 분리, 4 클라이언트 평등
  - Job Object(Win) 는 parent-child 모델 의존이라 detach 데몬에 부적합 → **idle timeout + named pipe 권한 + named mutex** 로 좀비 방지
- bursty 워크로드(예: 1시간 후 첫 클릭)에서는 데몬이 죽어있어 재spawn 비용 ~150ms 발생. ROI 는 `P(daemon alive) × 호출량` 함수

---

### 레버 2. **Python 핫 패스를 Rust로 흡수**

⚠️ **2026-05-09 측정 기반 갱신**: 아래 표의 초기 ROI 추정은 **파일 크기 / 코드 직관**에 의존했고 **실측 없이 작성**되었음. 2026-05-09 세션에서 한 모듈씩 실측한 결과, project_scan / secret_scan 외에는 **단일 세션으로 가치 있게 포팅 가능한 항목이 없음**이 데이터로 입증됨. 이전 표를 그대로 두면 후속 세션이 다시 같은 함정에 빠짐.

| 모듈 | 초기 추정 사유 | **2026-05-09 실측 / 검토** | **현실 평가** |
|---|---|---|---|
| `project_scan` | O(N) 파일 walk + 무시 패턴 | 측정 안 함, 이미 1차 포팅 완료 (Phase 2 §1차) | ✅ 끝. 가치 있음. |
| `secret_scan` | 정규식 + 라인 스캔 | 측정 안 함, 이미 1차 포팅 완료 (pure-function `scan_unified_diff`) | ✅ 끝. 가치 있음. git invocation 이전은 별 슬라이스. |
| `scan_cache` | 직렬화 비용 큼 (수 MB) | `.vibelign/scan_cache.json` 347.7 KB 에서 `json.loads` **1.05ms**, `json.dumps` **5.20ms** (n=20). 큰 dict 가 IPC 경계 넘으면 `json.loads` 가 어차피 IPC 출력에서 또 발생 → **수학적으로 항상 더 느림**. | ❌ 무가치. 포팅하려면 데이터가 Rust 안에 머무는 Option B (다중 세션) 또는 SQLite 구조 전환 (Option C) 만 의미. |
| `watch_state` | 직렬화 비용 큼 (수 MB) | `.vibelign/watch_state.json` 1569.9 KB 에서 `json.loads` **4.16ms**, `json.dumps` **11.11ms** (n=20). 호출 빈도 높음 (`watch_engine.py:273` 파일 삭제 / `:648` 파일 변경마다 `save_state`). 활발한 vib watch 세션에서 50 파일 편집 = 누적 ~550ms 비용. 빈도는 높지만 **scan_cache 와 동일 boundary 함정** — 1.5MB dict 가 IPC 경계 넘으려면 어차피 serialize → Python 측 deserialize → 다시 serialize → 파일 쓰기. **incremental Rust port 로는 못 이김**. 본질 문제는 매번 full dump. | ❌ Rust incremental 무가치. **구조적 fix (Option C: SQLite per-file rows 또는 append-only log)** 만 의미 있음. Python 안에서도 가능, Rust 가 본질 아님. |
| 앵커 파서 (`anchor_tools`) | 텍스트 매칭 + 인덱스 | `extract_anchors` **0.030ms/파일**, `extract_anchor_spans` **0.072ms/파일**, `extract_anchor_line_ranges` **0.167ms/파일** (8 sample files, n=20). 100 파일 기준 17ms 미만. | ❌ 무가치. <0.2ms/파일은 decoration 수준. |
| `strict_patch` / `patch_validation` | 결정론적 정확도 필요 | `apply_strict_patch` 는 anchor_tools 의 `extract_anchor_line_ranges` 를 import (cross-cutting tangle), `_count_search_match` 외에는 파일 I/O + checkpoint engine 호출. patch_validation 은 56 LOC 상수 + 2 helper, 핫스팟 아님. | ❌ 무가치. anchor_tools 가 leaf 의존인데 그게 자체로도 무가치. 묶어 옮길 동기 없음. |

**측정-기반 결론**: Phase 2 의 **단일 세션 incremental 포팅 후보는 모두 소진됨**. 남은 시나리오는:
- (A) 데이터가 Rust 안에 영구 거주하도록 **데이터 모델/스토리지 자체를 재설계** (예: scan_cache → SQLite 마이그레이션). 다중 세션 + 구조적 변경.
- (B) Phase 3 가 GUI 사용자 체감 가속을 끌어왔으므로, **Phase 2 추가 포팅은 ROI 가 낮은 채 정지**. 더 가치 있는 트랙(Phase 1 Windows / Phase 3 PROJECT_CONTEXT 분리 / 신규 트랙) 으로 이동.
- (C) 측정 없이 ROI 표만 따라가는 함정을 다음 세션에서도 반복하지 않도록 **이 표 자체를 신호로 사용**. 새 모듈 후보가 나올 때마다 사전 벤치 의무화.

**남길 것 (Python 유지)**:
- `change_explainer`, `ai_codespeak`, `docs_visualizer` — AI/실험 영역
- `request_normalizer`, `feature_flags` — 자주 바뀌는 정책

**규칙**:
> 규칙이 정해진 반복 작업 → Rust
> 계속 바뀌는 똑똑한 작업 → Python

---

### 레버 3. **GUI가 Python 거치지 않기**
**문제**: `GUI → Tauri → Python → Rust` 4-hop. Python은 단순 라우팅 역할만 하는 명령이 많음.

**해법**:
- vibelign-core를 **라이브러리 크레이트**로도 노출 (`lib.rs` 추가)
- Tauri 앱이 직접 `vibelign-core`를 임포트해서 commands 호출
- Python은 CLI/MCP/AI 협업 경로에만 사용

**기대 효과**: 클릭 → 결과까지 2-hop으로 단축. UX 즉각 반응.

---

## 4. 작업 순서

### ⚠️ 시작 전 결정해야 할 설계 질문 (BLOCKING)

내일 코드 쓰기 전에 **반드시** 답을 정해야 함:

1. **데몬 멀티테넌시**: per-root 1데몬 vs 글로벌 멀티 root 데몬?
   - per-root: 단순. 디렉터리당 PID 파일. (권장)
   - 글로벌: 메모리 공유 가능, 그러나 root 격리/락 복잡
2. **동시 요청 처리**: 직렬 vs 병렬?
   - 직렬: GUI + CLI + auto-backup hook + MCP 동시 호출 시 막힘 (shadow_runner 는 dev-only 비교 도구, watch_cmd 는 router 직접 소비자 아님 — §5 참조)
   - 병렬: protocol에 **request_id 필요** (지금 없음 — 깨는 변경)
3. **1-shot CLI 처리**: fallback 유지 vs 명시적 dual-mode?
   - **권장**: dual-mode. shadow_runner 가 1-shot 의존, auto-update 시 1-shot 만 가능
   - "fallback shim"이 아니라 **공식 두 경로** 로 명세
4. **자동 업데이트 시 데몬 종료 프로토콜**: Windows는 실행 중 `.exe` 덮어쓰기 불가
   - `Shutdown` 명령을 `EngineRequest` 에 추가
   - GUI/CLI 가 업데이트 전 데몬 stop → swap → restart 오케스트레이션
   - **권한 격리**: Unix socket 권한 0600 / Windows named pipe SDDL 로 같은 user 만 Shutdown 가능. 안 그러면 같은 머신 다른 user 가 DoS 가능
5. **EngineVersion 자기보고 한계**: 데몬 자기 자신의 sha 보고는 self-attestation. 클라이언트가 PID 의 exe path 를 OS API(`/proc/<pid>/exe`, `proc_pidpath`, `QueryFullProcessImageName`) 로 직접 sha 계산하는 보강은 Phase 1 이후 검토
6. **점진적 롤아웃 게이트**: `VIBELIGN_ENGINE_DAEMON=1` 옵트인으로 시작 → 안정화 후 디폴트 ON. 기존 `VIBELIGN_DISABLE_RUST_CHECKPOINT` 와 일관된 형태 유지

### Phase -1 (반나절): 프로토콜/영향 범위 정정 ⭐ 선행 필수

검토 결과, 바로 데몬 구현으로 들어가면 기존 1-shot 호출자와 테스트 범위가 뒤늦게 깨질 가능성이 크다. 먼저 아래 결정을 문서/테스트 기준으로 고정한다.

#### Phase -1 결정 고정 (2026-05-08)

- **데몬 범위**: per-root daemon. `.vibelign/engine.pid` / socket(or named pipe) 은 프로젝트 root 별로 둔다.
- **공식 모드**: V1 1-shot CLI 와 V2 daemon 을 모두 공식 지원한다. daemon 은 fallback shim 이 아니라 opt-in 병행 경로다.
- **request correlation**: 선택 C. V1 `EngineRequest` / `EngineResponse` payload shape 는 유지하고, daemon JSONL transport 에만 `{request_id, payload}` envelope 를 씌운다. Python daemon client 는 response envelope 를 unwrap 한 뒤 기존 parser 로 넘긴다.
- **root 격리**: daemon 시작 root 를 connection context 로 고정한다. inner request 의 `root` 는 daemon root 와 canonical match 해야 하며 다르면 거부한다.
- **operation locking**: write 계열은 per-root exclusive lock 으로 직렬화한다. read-only 계열은 writer 진행 중 대기하되 timeout/error 정책을 Phase 1 테스트에 포함한다. `request_id` 는 응답 매칭용이며 DB/FS race 방지 장치가 아니다.
- **daemon runtime/IPC**: Tokio async runtime + `interprocess` 기반 cross-platform transport 를 기본안으로 채택한다. Unix 는 Unix domain socket, Windows 는 named pipe 를 우선한다.
- **DB lifecycle**: daemon 도 요청 단위 DB open/close 를 유지한다. long-lived connection/pool 과 release 명령은 Phase 1 범위에서 제외한다.
- **daemon 전용 명령**: `Shutdown` / `EngineVersion` 은 V2 daemon envelope 에서만 추가한다. V1 1-shot flat request/response 는 유지한다.
- **lib expose 결정**: Phase 0/3 에서 `vibelign-core` 를 라이브러리로 노출할 때는 `ipc::{protocol, handler}` 를 우선 surface 로 삼고, `backup::*` 직접 노출은 Tauri direct bridge 요구가 확정될 때만 검토한다.
- **fallback 범위**: 현재 기능별 fallback/raise 정책을 그대로 시작점으로 삼는다. `checkpoint_has_changes` 는 Phase 1 에서 Python-only 경로 유지로 시작하고, Rust 흡수 여부는 별도 명령 추가 PR 에서 결정한다.
- **baseline**: 2026-05-08 local debug binary, `vibelign-core/target/debug/vibelign-engine`, 20회 `EngineInfo` 1-shot 측정: min 12.181ms / median 12.515ms / max 31.838ms. 출력 shape 는 기존 `{"status":"ok","result":"engine_info",...}` 유지 확인.
- **benchmark snapshot**: 2026-05-08 macOS local debug binary, short `/tmp` project root, direct engine binary 측정. 초기 daemon poll interval 50ms 상태에서는 daemon median 이 ~54ms 로 회귀했으나, Unix accept poll 을 2ms 로 줄인 뒤 최종 수치: `EngineInfo` 1-shot min 3.727ms / median 4.070ms / max 7.601ms (50 runs), daemon min 1.701ms / median 2.555ms / max 2.679ms (50 runs). `checkpoint_list` 1-shot min 3.772ms / median 4.169ms / max 8.181ms (30 runs), daemon min 1.268ms / median 2.564ms / max 2.600ms (30 runs). `checkpoint_create` small changed-file write path 1-shot min 6.350ms / median 6.986ms / max 23.543ms (20 runs), daemon min 4.127ms / median 4.807ms / max 7.538ms (20 runs). Heavy synthetic 400-file `checkpoint_create` 는 1-shot min 40.566ms / median 48.990ms / max 163.198ms (8 runs), daemon min 36.014ms / median 43.687ms / max 133.196ms (8 runs) 로 traversal/snapshot I/O 가 지배적임을 확인. Python CLI end-to-end `vib history` 는 daemon off min 94.471ms / median 96.129ms / max 127.356ms (15 runs), warm daemon on min 84.128ms / median 86.246ms / max 96.175ms (15 runs) 로 Python startup 비용이 지배적임을 확인.
- **GUI 4-hop end-to-end benchmark snapshot**: 2026-05-09 macOS, fresh `/tmp/vib-bench-gui` project root, debug `vibelign-engine`, `VIBELIGN_ENGINE_PATH` injection (Tauri `run_vib` 패턴 mimic), hyperfine 1.20.0 `--warmup 3`. GUI 가 실제 호출하는 명령 3개 측정.
  - `vib checkpoint list --json` (GUI 히스토리 뷰): 1-shot mean 89.7±2.6ms / range 87.8~97.4ms (15 runs), warm daemon mean 80.4±1.7ms / range 78.0~83.4ms (15 runs), 데몬이 1.12배 빠름. Δ ~9ms.
  - `vib doctor --plan --json` (GUI 도닥터 plan-only 뷰): 1-shot mean 100.6±2.2ms / range 97.5~105.7ms (15 runs), warm daemon mean 91.9±1.8ms / range 89.0~95.7ms (15 runs), 데몬이 1.09배 빠름. Δ ~9ms.
  - `vib checkpoint <msg> --json` (GUI 체크포인트 생성): 1-shot mean 108.4±12.7ms / range 91.8~122.1ms (12 runs), warm daemon mean 83.6±2.3ms / range 80.6~87.4ms (12 runs), 데몬이 1.30배 빠름. Δ ~25ms (write path 이라 engine 비중이 높아 read 보다 효과 큼).
  - **Cold daemon spawn**: 데몬 죽인 직후 first call(자동 spawn 포함) 5회 측정, real time 0.13~0.16s. 즉 idle 5분 후 첫 클릭은 Δ ~80~100ms 패널티 발생. plan §3 레버 1 "기대 효과" 와 일치(P(daemon alive) × 호출량 함수).
  - **결론**: Python sidecar startup(~70~80ms)이 4-hop wall time 의 대부분을 차지하여 daemon 의 engine-level 절감(~10~25ms)이 사용자 체감(예: 100ms vs 80ms)으로 잘 드러나지 않음. **Phase 3(Tauri 가 vibelign-core 직접 임포트)** 또는 vib Python keepalive 가 같이 와야 daemon 의 engine-level 1.7~5배 가속(plan §benchmark snapshot 1줄)이 GUI 사용자 체감으로 전이됨. **이 데이터로 Phase 3 우선순위가 측정 근거를 가짐**.

- [x] **공식 dual-mode 명세**: V1 1-shot CLI 는 계속 공식 지원하고, V2 daemon 은 병행 경로로 추가한다.
- [x] **프로토콜 호환성 규칙**:
  - `request_id` 는 Phase -1 에서 아래 방식 중 하나로 고정한다. 1-shot 과 daemon 의 의미는 분기하되, Python parser/handler contract 는 가능한 한 유지한다.
  - 응답 `request_id` echo 방식은 Phase -1 에서 하나로 고정한다:
    - 선택 A: 모든 `EngineResponse` variant 에 `request_id: Option<String>` 필드 추가.
    - 선택 B: `EngineEnvelope { request_id, response }` outer envelope 도입 후 Python parser 전체 갱신.
    - 선택 C: V1 `EngineRequest`/`EngineResponse` payload 는 그대로 두고, daemon JSONL transport 에만 `{request_id, payload}` envelope 를 씌운다. Python daemon client 가 unwrap 한 뒤 기존 parser 로 넘긴다.
    - 기본 권장: 선택 C. `protocol.rs` 의 flat response 생성 지점을 덜 건드리고, 1-shot parser shape 를 유지한다.
  - `EngineInfo` 는 유지하되, `EngineVersion` 또는 확장 응답으로 engine version + binary sha 를 제공한다.
  - `Shutdown` 은 V2 daemon 전용 명령으로 추가한다.
- [x] **per-root daemon root 격리 규칙**:
  - daemon 시작 root 와 요청 root 가 다르면 요청을 거부한다.
  - 또는 daemon transport envelope 의 root 를 connection context 로 고정하고 inner request root 는 검증/무시한다.
  - 어떤 방식을 택하든 다른 프로젝트 root 요청을 같은 daemon 이 처리하지 못하게 테스트한다.
- [ ] **operation-level locking 정책**: 현재 구현은 요청 단위 DB open/close + SQLite WAL/busy timeout 의존으로 시작했다. 명시적 per-root operation lock 은 Windows named pipe / 동시 writer 검증 때 재평가한다.
  - `checkpoint_create`, `checkpoint_restore`, `restore_files`, `prune`, `retention_apply`, `backup_db_maintenance --apply` 는 per-root exclusive lock 으로 직렬화한다.
  - `list`, `diff`, `preview`, `restore_suggestions`, `backup_db_viewer`, `backup_graph_summary` 는 read-only 로 분류하되, writer 진행 중에는 대기/timeout 정책을 명시한다.
  - `request_id` 는 응답 매칭 장치일 뿐 파일시스템/DB race 방지 장치가 아님을 명시한다.
- [x] **daemon runtime/IPC 구현 기반 결정**:
  - 현재 `vibelign-core` 는 동기 1-shot binary 이고 `tokio`/`interprocess` 의존성이 없다.
  - 선택 A: blocking thread + platform socket/named pipe abstraction.
  - 선택 B: Tokio async runtime + `interprocess`/platform pipe.
  - Phase -1 에서 하나를 고정하고 Cargo dependency / 테스트 전략을 함께 적는다.
- [x] **DB connection lifecycle 결정**:
  - 현재 Rust 코드는 작업마다 DB connection 을 열고 닫는 구조다.
  - 선택 A: daemon 도 요청 단위 open/close 유지 → 파일 락 위험 최소화, pool 효과 없음.
  - 선택 B: per-root long-lived connection/pool 유지 → 성능 이득 가능, Windows 파일 락/release 정책 필수.
  - `release` 명령 필요 여부는 이 결정에 종속된다.
- [x] `ipc/protocol.rs` 의 기존 `EngineRequest` 명령 wire 형태는 **유지**하고, Phase -1 에서 고른 방식에 따라 **V2 envelope/필드 + 명령(`Shutdown`, `EngineVersion`) 만 추가**한다.
- [x] **벤치마크 baseline 측정 후 plan 에 기록 (Phase -1 deliverable)**: engine-only 1-shot `EngineInfo` baseline, macOS debug daemon `EngineInfo`/`checkpoint_list`/small `checkpoint_create`/heavy synthetic `checkpoint_create`, Python CLI `vib history` end-to-end benchmark, GUI 4-hop end-to-end benchmark(`checkpoint list`/`doctor --plan`/`checkpoint create` + cold daemon spawn) 모두 §Phase -1 benchmark snapshot 에 기록.
  - `hyperfine --warmup 5 --runs 100 'vibelign-engine < req.json'` 형태로 NoOp(EngineInfo) / list / checkpoint_create(small/heavy) 분리 측정
  - engine-only 수치와 별도로 `vib history`, `vib checkpoint`, GUI `run_vib` end-to-end 시간을 측정해 Python/Tauri hop 이 가리는 비용을 분리한다.
  - 현재 1-shot baseline 수치를 plan §3 레버 1 "기대 효과" 옆에 기록 후 데몬 목표 수치 정의
- [x] MCP 대상 파일을 `vibelign/mcp/mcp_memory_handlers.py` 가 아니라 **`vibelign/mcp/mcp_checkpoint_handlers.py`** 로 고정한다.
- [x] 영향 범위를 “CLI/GUI/MCP 3개”로만 보지 말고 router 소비자 전체로 확장한다:
  - `vibelign/commands/*checkpoint*`, `vib_history`, `vib_undo`, `vib_backup_db_*`
  - `vibelign/mcp/mcp_checkpoint_handlers.py`
  - `vibelign/core/checkpoint_engine/auto_backup.py`, `hook_setup.py`, `strict_patch.py`
  - `vibelign/core/recovery/*`
  - `vibelign/commands/vib_transfer_cmd.py`
  - `vibelign/action_engine/executors/checkpoint_bridge.py`
- [x] fallback 정책을 기능별로 명시한다. 현재 create/list/restore/prune/retention 일부만 Python fallback 이 있고, diff/preview/restore-files/suggestions/backup-db viewer/maintenance 는 실패 시 raise 한다.
  - `retention_apply` 는 Rust 성공 응답(`protocol.rs::RetentionOk`)과 Python fallback 응답 shape 가 다를 가능성이 있으므로, Phase -1 에서 양쪽 shape 를 측정하고 parity 또는 명시적 차이를 plan 에 박는다.
  - `checkpoint_has_changes` 는 클래스 이름이 `RustCheckpointEngine` 임에도 `rust_checkpoint_engine.py:157-158` 가 `self._fallback.has_changes_since_checkpoint(...)` 만 호출 → **Rust 엔진을 우회하는 hidden Python-only path**. MCP 공개 API(`mcp_tool_specs.py:104`)이므로, daemon 도입 시 (a) Rust/daemon 으로 흡수(`CheckpointHasChanges` 명령 추가) vs (b) 우회 유지를 명시 결정한다.

### Phase 0 (반나절): 라이브러리 크레이트 노출 (레버 3 전제 — Phase 3 와 묶음)

⚠️ **주의**: lib 노출 자체는 사용처가 없으면 dead weight. Phase 3 (Tauri 가 vibelign-core 직접 임포트) 가 실행 commit 일 때만 의미 있음. **Phase 3 를 미루면 Phase 0 도 함께 미룬다**. 단독 Phase 0 PR 금지.

- [x] `vibelign-core/Cargo.toml` 에 `[lib]` 섹션 추가 (`crate-type = ["rlib"]` 만 설정. `cdylib`/`staticlib` 은 Phase 2 의 ctypes/cffi 직접 호출 노선이 채택될 때만 — 2026-05-09)
- [x] `vibelign-core/src/lib.rs` 신규 작성, `pub mod ipc;` 만 surface 노출 (`backup`/`db`/`project_scan`/`secret_scan`/`security`/`constants` 는 private 유지). `src/main.rs` 는 `mod` 선언 제거 후 `use vibelign_core::ipc::...` consumer 로 슬림화.
- [x] `[[bin]] vibelign-engine` 그대로 유지 (1-shot CLI / daemon 경로 모두 보존, 기존 통합 테스트 90 passed 유지)
- [x] 빌드 검증: `cargo build --lib` / `cargo build --bin vibelign-engine` / `cargo test` 모두 grün (2026-05-09)
- [x] Phase 3 와 같은 슬라이스로 묶음 (2026-05-09 단일 슬라이스 진행)

### Phase 1 (3~5일): 데몬화 골격 + 프로토콜 확장
- [x] **프로토콜 V2**: Phase -1 에서 고른 request correlation 방식 구현. 기본안은 daemon JSONL transport envelope `{request_id, payload}` 이며 V1 1-shot `EngineRequest`/`EngineResponse` payload shape 는 유지한다.
- [x] `Shutdown` / `EngineVersion` 명령 추가
- [x] `vibelign-engine --daemon --root <path>` 플래그
- [ ] socket/named pipe transport 위 JSONL framing 리더/라이터 (한 줄 = 한 요청, request_id 로 응답 매칭). stdin/stdout 은 V1 1-shot 전용으로 유지 — **Unix socket 완료, Windows named pipe 미완료**.
- [x] PID 파일 + healthcheck + stale 자동 복구 (`.vibelign/engine.pid`, `.vibelign/engine.sock`)
- [x] Python `rust_engine.py` 에 **데몬 클라이언트** 추가 (`call_rust_engine_daemon()`), 기존 `call_rust_engine()` 1-shot 유지
- [x] 라우터 (`router.py`) 또는 `RustCheckpointEngine` 가 dual-mode 결정: 데몬 가용/혼잡/shadow 모드/환경 fallback 에 따라 분기
- [ ] **전체 router 소비자** 검증: CLI(`vib *`), GUI(via vib), MCP(`mcp_checkpoint_handlers.py`), `vibelign/core/checkpoint_engine/auto_backup.py`, hook setup, recovery, action engine — CLI/MCP/checkpoint router 대표 경로는 완료. 2026-05-08 macOS-safe slice 로 auto_backup/action_engine/transfer/recovery 자동 백업 signal/hook_setup 초기 checkpoint 의 daemon opt-in 경로를 `tests/test_checkpoint_router_consumers.py` 에 추가했고, `vib history`/`vib undo --checkpoint-id --json` list/restore daemon 경로를 `tests/test_vib_history_undo_cmd.py` 에 추가했다. 2026-05-09 추가 macOS-safe slice: vib_checkpoint_cmd `create_for_cli` create+prune, `vibelign.core.strict_patch.create_checkpoint` 임포트 바인딩, `recovery.sandwich.create_recovery_sandwich_checkpoint`, `recovery.apply._restore_files` (`checkpoint_restore_files_safe` 명령), `vib backup-db maintenance --json` (`backup_db_maintenance` 명령) — 총 5개 daemon opt-in 경로를 동일 매트릭스 테스트 파일에 추가. GUI/Windows 실기 matrix 는 미완료.

**검증**:
- `vib doctor --strict` 통과 (데몬 켜짐/꺼짐 양쪽)
- 4 모드 사용자 출력 동일성 확인: daemon ON / daemon OFF / `VIBELIGN_ENGINE_DAEMON=1` 옵트인 / `VIBELIGN_DISABLE_RUST_CHECKPOINT=1`
- integrity failure / startup failure / timeout 에서 기존 fallback 또는 명시적 error 정책 유지
- **응답 시간 목표는 명령별 분리** (heavy I/O 명령에는 절대 목표 부여 금지 — baseline 갱신만):
  - NoOp (EngineInfo): 데몬 < 5ms / 1-shot < 200ms
  - list: 데몬 < 20ms / 1-shot < 200ms
  - checkpoint_create (small repo, no changes): 데몬 < 50ms / 1-shot < 250ms
  - checkpoint_create (heavy I/O): 측정 후 baseline 기록만
- 동시 호출 10개: race condition 없음, request_id 매칭 정확
- shadow_runner(`VIBELIGN_SHADOW_COMPARE=1` 비교 도구): 데몬 + 1-shot 병행 실행 OK
- diff/preview/restore-files/suggestions/backup-db viewer/maintenance 는 fallback 없음/있음 정책에 맞게 실패 모드 테스트
- `retention_apply` 는 Rust 성공/fallback 응답 shape parity 를 검증하고, `checkpoint_has_changes` 는 Python-only 공개 API 로 유지할지 Rust/daemon 으로 흡수할지 결정
- **lifecycle**: lazy spawn race-safe (10 동시 first-call 에서 단일 데몬), idle 5분 자살, stale PID 자동 복구
- **로깅**: 데몬 stderr → `.vibelign/engine.log` (rotation 10MB × 3개), level=info 디폴트, `VIBELIGN_ENGINE_LOG=debug` 로 상승
- **daemon artifacts**: `.vibelign/engine.pid`, `.vibelign/engine.sock`, `.vibelign/engine.log*` 는 checkpoint/restore/project_scan 대상에서 제외하고, protect/guard/watch 규칙과 충돌하지 않는지 확인
- **Python reconnect**: socket 끊김 감지 시 1회 즉시 재시도 → 실패 시 1-shot fallback. in-flight `request_id` 가 timeout 되면 응답 폐기 + 새 connection
- **WAL dual-mode**: 데몬과 1-shot 이 같은 `vibelign.db` 동시 접근 시 양쪽 모두 WAL 모드 + `busy_timeout = 5000ms`. writer 단일성은 SQLite 자체 락에 의존 (rusqlite `Connection::busy_timeout`)
- **DB connection lifecycle**: Phase -1 결정에 따라 요청 단위 open/close 또는 long-lived connection/pool 중 하나로 고정. long-lived 선택 시 release/shutdown/file-lock 테스트 필수
- **Unix 신호**: SIGTERM/SIGINT → graceful shutdown (in-flight 응답 후 종료), SIGHUP 무시. Tokio 선택 시 `tokio::signal`, blocking 선택 시 signal-hook 등 동기 처리 전략 명시

### Phase 2 (2~3일): 첫 핫 패스 이전
- [x] Python `project_scan` behavior contract fixture 추가: ignored dirs(`docs`, `tests`, `.vibelign`, `node_modules`, `target`), daemon artifacts exclusion, source file selection, category classification, Python/TS import extraction을 `tests/test_project_scan.py` 에 고정.
- [x] Rust IPC `project_scan` 1차 구현: `vibelign-core/src/project_scan.rs`, `EngineRequest::ProjectScan`, one-shot/daemon handler bridge, Python `scan_project_with_rust()` wrapper 추가. 현재 contract fixture 범위는 path/category/imports 이며, 기존 Python call sites 는 아직 Rust path 로 전환하지 않음.
- [x] Opt-in 라우팅 추가: `VIBELIGN_PROJECT_SCAN_RUST=1` 일 때 `iter_source_files()` 는 Rust `project_scan` 결과의 `files[].path` 를 `Path` 로 변환해 사용하고, Rust warning/실패 시 기존 Python/fd 경로로 fallback.
- [x] Opt-in consumer 검증 추가: `tests/test_vib_scan_cmd.py` 에서 `run_vib_scan()` anchor validation 단계가 `VIBELIGN_PROJECT_SCAN_RUST=1` 상태에서 Rust `project_scan` wrapper 를 호출하는지 확인.
- [x] Opt-in direct consumer 검증 추가: `tests/test_anchor_tools_v2.py` 에서 `anchor_tools.preview_anchor_targets()` 가 `VIBELIGN_PROJECT_SCAN_RUST=1` 상태에서 Rust `project_scan` wrapper 를 호출하는지 확인.
- [x] Opt-in scan_cache consumer 검증 추가: `tests/test_vib_start.py` 에서 `_build_project_map()` → `scan_cache.incremental_scan()` → `iter_source_files()` 경로가 `VIBELIGN_PROJECT_SCAN_RUST=1` 상태에서 Rust `project_scan` wrapper 를 호출하고 Rust-reported file set 만 project map 에 반영하는지 확인.
- [x] 기본 `project_scan` 라우팅 전환: `iter_source_files()` 는 기본적으로 Rust `project_scan` wrapper 를 먼저 호출하고, warning/실패 시 기존 Python/fd path 로 fallback. `VIBELIGN_PROJECT_SCAN_RUST=0` 으로 명시 opt-out 가능.
- [x] Python 측은 Rust 결과를 받아서 가공만 (점진적 이전): `project_scan.iter_source_file_records()` 를 추가해 Rust `files[].path/category/imports` 를 typed record 로 전달하고, `scan_cache.incremental_scan()` 은 Rust metadata 가 있으면 category/imports 를 재계산하지 않고 사용함. anchor/line_count 등 Python-only cache 필드는 기존대로 보강.
- [x] 캐시 호환성 검증: Rust-first `project_scan` 경로로 `_build_project_map()` 을 실행해도 `.vibelign/scan_cache.json` 은 schema_version 2, `entries`, `mtime`, `size`, `anchors`, `anchor_spans`, `imports`, `category`, `line_count` 포맷을 유지함 (`tests/test_vib_start.py`).
- [ ] `project_scan` contract 를 golden fixture 로 먼저 고정한다:
  - [x] ignore 규칙(`docs`, `tests`, `node_modules`, `target`, `.vibelign` source/daemon artifacts) parity 를 Python/Rust paired fixture 에 고정.
  - [x] `.vibelign` 파일 중 `project_map.json`, `anchor_meta.json`, `engine.sock`, source-like `.vibelign/app.py` 제외 parity 를 Python/Rust paired fixture 에 고정.
  - [x] entry/ui/service/core 분류 결과 parity 를 Python/Rust paired fixture 및 Rust metadata handoff tests 에 고정.
  - [x] anchor index/meta 연결 정보 parity: Rust-first `_build_project_map()` 과 `VIBELIGN_PROJECT_SCAN_RUST=0` Python-only `_build_project_map()` 의 `anchor_index`, per-file `anchors`, `anchor_spans` 일치 검증 추가 (`tests/test_vib_start.py`).
  - [x] 한글 경로 fixture 포함: `services/도우미.py` 가 Python/Rust 양쪽에서 source file + service category + import extraction 대상임을 고정.
  - [x] 이모지 경로 fixture 포함: `services/emoji_😀.py` 가 Python/Rust 양쪽에서 source file + service category + import extraction 대상임을 고정.
  - [x] Windows-gated 경로 fixture 추가: `tests/test_project_scan.py` 에 `sys.platform == "win32"` 에서만 실행되는 `\\?\` extended-length root + mixed-case `Node_Modules` exclusion test 추가. macOS 에서는 skip 으로 남김.
  - Windows 실제 runner 필요: UNC share 경로와 Windows filesystem 대소문자 민감도 fixture 는 macOS 에서 완료 처리하지 않음.

### Phase 3 (선택, 1주~): 도메인 확장
- 패치 엔진(strict_patch, patch_validation) 이전
- 앵커 인덱서 이전
- GUI 가 `vibelign-core` 라이브러리 직접 임포트 (Phase 0 완료가 전제)

---

## 5. 영향 범위 (지금 코드에서 깨지거나 손봐야 할 곳)

### 5.1 Python 호출자 (router 소비자 전체 — 모두 검증 필요)
- `vibelign/core/checkpoint_engine/rust_engine.py::call_rust_engine` — subprocess.run 한 번씩 spawn
- `vibelign/core/checkpoint_engine/shadow_runner.py::prepare_shadow_run` — `VIBELIGN_SHADOW_COMPARE=1` 일 때만 동작하는 **개발용 비교 도구** (TempDir 복제 후 Rust 호출). 운영 핵심 경로 아님. **진짜 동시성 위험은 GUI + CLI + auto-backup hook + MCP 가 같은 root 의 데몬을 동시에 두드릴 때**
- `vibelign/core/checkpoint_engine/router.py` 와 `rust_checkpoint_engine.py::RustCheckpointEngine` — 모든 router 소비자가 거치는 dual-mode 결정 지점
- `vibelign/mcp/mcp_checkpoint_handlers.py` — MCP 서버의 체크포인트 엔진 호출 경로 (`mcp_handler_registry.py` 가 동적 import)
- `vibelign/commands/{vib_checkpoint,vib_undo,vib_history,vib_backup_db_*,vib_doctor,...}.py` — 모두 1-shot 가정
- `vibelign/commands/vib_transfer_cmd.py` — handoff 생성 중 `list_checkpoints()` 를 소비하므로 daemon/1-shot parity 검증 대상
- `vibelign/core/checkpoint_engine/auto_backup.py`, `hook_setup.py`, `strict_patch.py`, `core/recovery/*`, `action_engine/executors/checkpoint_bridge.py` — `router.py` 경유 간접 소비자, dual-mode 회귀 대상

### 5.2 GUI (Tauri)
- `vibelign-gui/src-tauri/src/lib.rs::run_vib_with_progress` — 현재 **`vib` (Python) 만** spawn, 엔진 직결 아님
- `vibelign-gui/src-tauri/src/vib_path.rs::find_runtime_rust_engine` / `sha256_manifest_path` — `vibelign-engine.exe` 경로 탐색 + sha256 무결성
- `vibelign-gui/src-tauri/Cargo.toml` — `vibelign-core` 의존성 **없음** → 레버 3 위해 추가 필요
- 4-hop (GUI → Tauri → vib(Py) → engine) 그대로 두면 데몬화 효과는 vib 쪽 startup 비용에 의해 가려질 수 있음

### 5.3 통합 지점 충돌
- **`watch_cmd`** (`vibelign/commands/watch_cmd.py`) — 현재 checkpoint router 직접 소비자는 아니지만 이미 장수 Python 프로세스다. daemon lifecycle / keepalive 정책과 충돌하지 않도록 “watcher 는 데몬 owner 가 아니다” 또는 별도 핸드오프 정책을 Phase -1 에서 결정한다.
- **무결성 SHA256 매니페스트** (`rust_engine.py:99-109`) — 1-shot 은 매번 검사. 데몬은 시작 시 1회 → **자동 업데이트로 바이너리 교체되면 stale 감지 못함**. `EngineVersion` 응답에 binary sha 포함하고, 클라이언트가 주기적으로 확인.
- **rusqlite WAL** — long-lived connection/pool 선택 시 데몬이 DB 파일 핸들을 보유 → 사용자가 `.vibelign/` 삭제 시 (Windows) 락 걸림. 이 경우 명시적 release 명령 필요.
- **DB connection lifecycle** — 현재는 요청 단위 connection 이지만 daemon 에서 pool/long-lived connection 을 선택하면 파일 락 위험이 새로 생긴다. release 명령은 long-lived 선택 시에만 필수로 둔다.
- **fallback parity** — `retention_apply` fallback 응답 shape 축소와 `checkpoint_has_changes` Python-only 공개 API 를 daemon rollout 범위에서 누락하지 않는다.

### 5.4 테스트 보강 대상

현재 테스트는 1-shot subprocess + 부분 fallback 모델을 주로 검증한다. daemon 도입 전/후 아래 테스트를 보강한다.

- `tests/test_checkpoint_rust_engine.py`
  - daemon client startup/shutdown/reconnect/timeout
  - stale PID/socket recovery
  - `EngineVersion` binary sha mismatch
  - concurrent request `request_id` correlation
- `tests/test_checkpoint_engine_router.py`
  - daemon/1-shot/env-disabled routing decision
  - shadow mode 에서 1-shot 유지 또는 격리 보장
  - 기능별 fallback/raise 정책
- `tests/test_mcp_checkpoint_handlers.py`
  - daemon-backed checkpoint/list/diff/preview/restore parity
  - daemon error propagation
  - `checkpoint_has_changes` Python-only 유지/흡수 정책 검증
- `tests/test_gui_cli_contracts.py`
  - GUI 가 소비하는 JSON payload 가 daemon/1-shot 에서 동일한지 검증
  - backup DB viewer/maintenance apply/dry-run parity
- `tests/test_vib_transfer_cmd.py`
  - handoff 생성 시 checkpoint list 가 daemon/1-shot 양쪽에서 동일하게 반영되는지 검증
- `tests/test_checkpoint_retention.py` 또는 기존 checkpoint engine 테스트 확장
  - `retention_apply` Rust 성공/fallback 응답 shape parity 검증
- 신규 권장: `tests/test_vib_history_cmd.py`, `tests/test_vib_undo_cmd.py`
  - history rendering
  - interactive selection/cancel/invalid input
  - checkpoint-id / force 경로
- Rust 쪽 신규/확장
  - `vibelign-core` protocol V1/V2 compatibility test
  - socket/named pipe transport 위 daemon JSONL framing integration test
  - Windows named pipe / Unix socket transport smoke test

---

## 6. Windows 특이사항 (설계 단계에서 결정)

### 6.1 IPC 선택
- **Unix domain socket**: Win10 1803+ 만 지원. 구버전 사용자 컷오프할지 결정.
- **Named Pipe** (`\\.\pipe\vibelign-engine-<root-hash>`): canonical Windows. `interprocess` crate 또는 `tokio::net::windows::named_pipe`.
- **stdin/stdout 파이프**: 단일 클라이언트만 가능 → 다중 호출자 시 부적합.
- **권장**: tokio + `interprocess` (cross-platform). 또는 자체 추상화 ([trait Transport]).

### 6.2 Windows-specific 위험 (테스트 매트릭스에 추가)

| 항목 | 1-shot 모델 | 데몬 모델 위험 | 대응 |
|---|---|---|---|
| `.exe` self-update | 안전 (실행 중 아님) | **실행 중인 `.exe` 덮어쓰기 불가** | `Shutdown` 명령 → 교체 → restart |
| OneDrive/Dropbox/iCloud 동기 폴더의 `.vibelign/vibelign.db` (11.5MB) | WAL 즉시 닫힘 | long-lived connection 선택 시 WAL 핸들 유지 → 동기 충돌 | DB 폴더를 sync 제외 안내 + WAL 체크포인트 강제 명령. 요청 단위 open/close 선택 시 위험 낮음 |
| 콘솔 창 깜빡임 | `CREATE_NO_WINDOW` 사용 중 | 데몬도 동일 플래그 필수 + 백그라운드 visibility | 기존 `WINDOWS_SUBPROCESS_FLAGS` 재사용 |
| 프로세스 고아화 (GUI crash) | 자동 정리 | 데몬 orphan | owner-less 정책 기준: idle 5분 자살 + stale PID 복구 + named pipe 권한. Job Object 는 parent-owned 모델 채택 시에만 사용 |
| 종료 신호 | exit code 만 | Windows 에는 POSIX SIGTERM 이 없음 | JSON `Shutdown` 명령을 기본 종료 경로로 사용. 추가 OS-level fallback 은 runtime/transport 선택 후 결정 |
| 파일 락 (mandatory) | 호출 단위 락 | long-lived connection 선택 시 장시간 락 보유 → 사용자 작업 방해 | long-lived 선택 시 release 명령 + idle timeout 자동 unload. 요청 단위 open/close 선택 시 별도 release 불필요 |
| MAX_PATH=260 | 호출 단위 영향 | 캐시된 path 핸들에서 더 노출 | `\\?\` prefix 일관 사용 |
| Antivirus / SmartScreen | 1회성은 통과 빈도 ↑ | 장수 미서명 바이너리 + 빠른 IPC = 의심 점수 ↑ | 코드 사인 + 데몬 idle 시 자살(self-exit) |
| `replace_target_with_temp` (cas.rs:303-315) | 직렬 호출이라 안전 | 멀티스레드 데몬에서 delete-then-rename race | 파일별 쓰기 락 (이미 SQLite 트랜잭션으로 가드됨 확인 필요) |
| PowerShell vs CMD onboarding | 영향 없음 | 영향 없음 | (현 로직 유지) |

### 6.3 Windows 테스트 환경
- Win10 1809 (LTSC) — AF_UNIX 지원 경계
- Win11 24H2 — 최신
- OneDrive 동기 폴더에 프로젝트 둔 케이스
- 한글/이모지 경로 (이미 path_guard 가 backslash 이스케이프 거부 — 데몬에서도 동일 검증 유지)

---

## 7. 위험 / 트레이드오프

| 위험 | 완화책 |
|---|---|
| 데몬 좀비 프로세스 | PID 파일 + healthcheck + 자동 stale 복구. Win 은 Job Object 대신 idle 5분 자살 + named pipe 권한 |
| GUI 가 데몬화 효과 못 받음 | Phase 1 성과는 CLI/MCP 직접 경로 개선으로 한정. GUI 즉각 반응은 Phase 3 (Tauri↔core 직결) 또는 vib Python keepalive 이후에만 주장 |
| bursty 워크로드(idle 후 첫 클릭)에서 데몬 죽어있음 | first-call ~150ms 비용 수용 또는 GUI 가 keepalive ping 으로 살림 (Phase 3 결정) |
| WAL dual-mode (데몬 + 1-shot 동시) DB 락 경합 | 양쪽 `busy_timeout = 5000ms`, WAL 모드, 경쟁 시 SQLite 자체 락에 위임 |
| DB connection lifecycle 미결정 | Phase -1 에서 요청 단위 open/close vs long-lived pool 중 하나를 고정. long-lived 선택 시 release/shutdown/file-lock 테스트 추가 |
| 데몬 stdio 충돌 (MCP 도 stdio JSON-RPC) | 데몬은 Unix socket / Windows named pipe 만 사용. stdin/stdout JSONL 은 1-shot 전용 |
| Cross-platform IPC 빌드 복잡도 | `interprocess` crate 도입, onedir 전환(2026-04-18) 인프라 재사용 |
| Rust 빌드 시간 증가 | feature flag로 도메인 분리, CI 캐시 활용 |
| Dual-mode 부담 (1-shot + 데몬) | "fallback" 이 아닌 **명시적 두 모드**. router.py 가 결정. |
| 자동 업데이트와 데몬 충돌 | 업데이트 전 명시적 Shutdown 단계, EngineVersion 으로 stale 감지 |
| GUI + CLI + auto-backup hook + MCP 동시 호출 race | request_id + 동시 처리 지원 (Phase 1 핵심). shadow_runner 는 개발 비교 도구로 별도 격리 |
| watch_cmd 와 daemon lifecycle 충돌 | Phase -1 결정: watcher 는 daemon owner 가 아님을 명시하거나 별도 keepalive 핸드오프 정의 |

---

## 8. 절대 옮기지 말 것

- AI 관련 (`ai_codespeak`, `change_explainer`)
- Docs 시각화 (`docs_visualizer`)
- 휴리스틱/정책 자주 바뀌는 부분
- MCP 핸들러 자체 (Python MCP 생태계 활용)

---

## 9. 내일 시작 체크리스트

- [ ] `vib doctor --strict` 로 현재 상태 스냅샷
- [ ] `vib checkpoint "rust 데몬화 시작 전"`
- [x] `vibelign-core` 에 daemon 모드 분기 설계 (`main.rs` 앵커 영역만 수정)
- [x] `ipc/protocol.rs` 의 기존 명령 wire 형태는 유지하되, Phase -1 request correlation 방식 + `Shutdown` / `EngineVersion` 명령 추가 (Phase -1 결정에 맞춤)
- [x] `EngineResponse` request_id echo 는 transport envelope vs variant 필드 vs outer response envelope 중 하나로 확정하고 Python parser 영향 범위를 적기
- [x] daemon runtime 은 blocking thread 기반 vs Tokio async 기반 중 하나로 확정하고 필요한 Cargo dependency 를 적기
- [x] DB connection lifecycle 은 요청 단위 open/close vs long-lived pool 중 하나로 확정하고 release 명령 필요 여부를 적기
- [ ] 1차 PoC: socket(Unix) / named pipe(Windows) transport 위 JSONL 루프 + EngineInfo 핸들링 (stdin/stdout 은 V1 1-shot 전용으로 유지) — **Unix socket PoC/implementation 완료, Windows named pipe 미완료**.
- [x] Python 클라이언트는 1회성 호출 fallback 유지하면서 데몬 우선 사용
- [ ] 벤치마크: hyperfine 으로 NoOp(EngineInfo) / list / checkpoint_create(small/heavy) 명령별 분리 측정 (현재 1-shot vs 데몬)

---

## 참고 위치

- Rust 엔트리: `vibelign-core/src/main.rs:11`
- IPC 프로토콜: `vibelign-core/src/ipc/protocol.rs`
- 백업 모듈: `vibelign-core/src/backup/mod.rs`
- Python 핫 패스: `vibelign/core/{project_scan,secret_scan,scan_cache,strict_patch}.py`
- 이전 사이드카 작업: 메모리 `vibelign_gui_vib_sidecar_onedir.md`
