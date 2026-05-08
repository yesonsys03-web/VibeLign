# Rust 엔진 120% 활용 계획

**작성일**: 2026-05-06 (내일 작업용)
**대상**: vibelign-core (Rust 엔진) + vibelign(Python) + vibelign-gui(Tauri)

**진행 상태 — 2026-05-08 세션 종료 기준**

- ✅ Phase -1 결정 고정 완료: per-root daemon, official dual-mode, V2 daemon envelope `{request_id, payload}`, request-level DB open/close, `checkpoint_has_changes` Python-only 유지.
- ✅ Phase 1 Unix/macOS daemon 골격 구현/검증 완료: `vibelign-engine --daemon --root`, Unix socket JSONL, `Shutdown`/`EngineVersion`, root isolation, PID/socket lifecycle, idle timeout, Python daemon client, daemon opt-in routing, CLI/MCP smoke coverage.
- ✅ 선행 리팩토링 완료: Tauri command 분리, Python `rust_engine/` 패키지 분리, Rust IPC `protocol.rs`/`handler.rs` 분리, fallback policy helper 분리.
- ✅ 안전장치 완료: daemon runtime artifacts checkpoint/project-scan 제외, `.vibelign/engine.log` rotation, unsupported transport 일관 fallback(`RUST_ENGINE_DAEMON_UNSUPPORTED`).
- 🚧 남은 Phase 1 작업: Windows named pipe transport/lifecycle/update 검증, 공식 성능 benchmark 기록, Windows 실제 머신 smoke.
- ⏭️ Phase 2/3 미착수: Rust `project_scan` 이전, GUI direct core bridge.

**마지막 검증 스냅샷**

- `uv run --with pytest python -m pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py tests/test_mcp_checkpoint_handlers.py tests/test_local_checkpoints.py tests/test_gui_cli_contracts.py -q` → 108 passed.
- `cargo test --manifest-path "vibelign-core/Cargo.toml"` → 74 passed.
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
**대상 (우선순위 순)**:

| 모듈 | 이유 | Rust 의존성 (이미 있음) |
|---|---|---|
| `project_scan` | O(N) 파일 walk + 무시 패턴 | walkdir |
| `secret_scan` | 정규식 + 라인 스캔 | (regex 추가 필요) |
| `scan_cache` / `watch_state` | 직렬화 비용 큼 (수 MB) | rusqlite |
| 앵커 파서 | 텍스트 매칭 + 인덱스 | (자체 구현) |
| `strict_patch` / `patch_validation` | 결정론적 정확도 필요 | (텍스트 처리) |

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
- [ ] **벤치마크 baseline 측정 후 plan 에 기록 (Phase -1 deliverable)**: engine-only 1-shot `EngineInfo` baseline 은 기록됨. daemon/list/checkpoint_create 및 end-to-end `vib`/GUI benchmark 는 미완료.
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

- [ ] `vibelign-core/Cargo.toml` 에 `[lib]` 섹션 추가 (`crate-type = ["rlib"]`. `cdylib`/`staticlib` 은 Phase 2 의 ctypes/cffi 직접 호출 노선이 채택될 때만)
- [ ] 현재 `mod backup; mod ipc;` 등을 `lib.rs` 에 노출
- [ ] `[[bin]]` 은 그대로 유지 (1-shot CLI 경로 보존)
- [ ] 빌드 검증: `cargo build` 양쪽 다 성공
- [ ] Phase 3 와 같은 PR 또는 인접 PR 로 묶기

### Phase 1 (3~5일): 데몬화 골격 + 프로토콜 확장
- [x] **프로토콜 V2**: Phase -1 에서 고른 request correlation 방식 구현. 기본안은 daemon JSONL transport envelope `{request_id, payload}` 이며 V1 1-shot `EngineRequest`/`EngineResponse` payload shape 는 유지한다.
- [x] `Shutdown` / `EngineVersion` 명령 추가
- [x] `vibelign-engine --daemon --root <path>` 플래그
- [ ] socket/named pipe transport 위 JSONL framing 리더/라이터 (한 줄 = 한 요청, request_id 로 응답 매칭). stdin/stdout 은 V1 1-shot 전용으로 유지 — **Unix socket 완료, Windows named pipe 미완료**.
- [x] PID 파일 + healthcheck + stale 자동 복구 (`.vibelign/engine.pid`, `.vibelign/engine.sock`)
- [x] Python `rust_engine.py` 에 **데몬 클라이언트** 추가 (`call_rust_engine_daemon()`), 기존 `call_rust_engine()` 1-shot 유지
- [x] 라우터 (`router.py`) 또는 `RustCheckpointEngine` 가 dual-mode 결정: 데몬 가용/혼잡/shadow 모드/환경 fallback 에 따라 분기
- [ ] **전체 router 소비자** 검증: CLI(`vib *`), GUI(via vib), MCP(`mcp_checkpoint_handlers.py`), `vibelign/core/checkpoint_engine/auto_backup.py`, hook setup, recovery, action engine — CLI/MCP/checkpoint router 대표 경로는 완료, auto_backup/hook/recovery/action engine 전체 matrix 는 미완료.

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
- [ ] `project_scan` 을 Rust로 (walkdir + 무시 패턴 + blake3 해시)
- [ ] Python 측은 Rust 결과를 받아서 가공만 (점진적 이전)
- [ ] 캐시 호환성 검증 (`scan_cache.json` 포맷 유지 또는 마이그레이션)
- [ ] `project_scan` contract 를 golden fixture 로 먼저 고정한다:
  - ignore 규칙(`.git`, `node_modules`, build 산출물, `.vibelign` 내부 daemon artifacts) parity
  - `.vibelign` 파일 중 포함/제외 예외(`project_map.json`, `anchor_meta.json` 등) parity
  - entry/ui/service/core 분류 결과 parity
  - anchor index/meta 연결 정보가 기존 Python 결과와 동일한지 검증
  - Windows 경로(`\\?\`, UNC, 한글/이모지, 대소문자 민감도) fixture 포함

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
