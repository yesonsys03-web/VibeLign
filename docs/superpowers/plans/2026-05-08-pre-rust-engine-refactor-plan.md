# Rust 엔진 확장 전 선행 리팩토링 계획

**작성일**: 2026-05-08  
**대상**: `vibelign-gui/src-tauri`, `vibelign/core/checkpoint_engine`, `vibelign-core/src/ipc`  
**관련 계획**: `docs/superpowers/plans/2026-05-07-rust-engine-utilization-plan.md`

**진행 상태 — 2026-05-08 세션 종료 기준**

- ✅ PR 1~4 코드 리팩토링 완료: Tauri command 모듈화, Python Rust engine transport/discovery 분리, Rust IPC protocol/handler 분리, fallback policy helper 분리.
- ✅ Phase 1 daemon 구현을 위해 의도적으로 비워뒀던 `daemon_client.py` / `daemon.rs` 는 후속 daemon slice 에서 실제 구현 파일로 추가됨.
- ✅ 관련 checkpoint/Rust 회귀 검증은 daemon plan 문서의 마지막 검증 스냅샷 기준으로 통과.
- ⚠️ 이 문서는 “선행 리팩토링” 완료 기록이다. Windows named pipe / benchmark / Phase 2+ 진행 상태는 Rust daemon plan 문서를 기준으로 본다.

---

## 1. 한 줄 요약

> Rust daemon / Tauri → Rust core 직결을 구현하기 전에, 이미 커진 진입 파일과 transport 경계를 먼저 나눠서 **기능 변경 없이 안전한 작업 공간**을 만든다.

---

## 2. 왜 먼저 리팩토링하나

Rust 엔진 활용 계획의 Phase 1/3은 단순 기능 추가가 아니다.

- Phase 1: 1-shot subprocess 외에 daemon transport, request correlation, fallback 정책이 추가된다.
- Phase 3: Tauri GUI가 Python `vib`를 거치지 않고 `vibelign-core`를 직접 호출하는 경로가 생긴다.

현재 구조에 그대로 얹으면 다음 위험이 커진다.

- `vibelign-gui/src-tauri/src/lib.rs`가 이미 앱 bootstrap, docs, watch, settings, error reporting, subprocess bridge를 함께 들고 있다.
- `vibelign/core/checkpoint_engine/rust_engine.py`가 binary discovery, integrity check, subprocess transport, command wrapper를 모두 들고 있다.
- `vibelign-core/src/ipc/protocol.rs`가 protocol type과 large `handle()` match를 함께 들고 있어 V2 envelope / daemon command 추가 시 복잡도가 급증한다.

따라서 이 리팩토링의 목적은 성능 개선이 아니라 **변경 경계 축소**다.

---

## 3. 원칙

1. **기능 변경 금지**
   - CLI/GUI/MCP 출력 shape 변경 금지
   - fallback 동작 변경 금지
   - env flag 의미 변경 금지
   - 단, 정책 문서에는 **silent fallback 금지** 원칙을 명시한다. fallback 이 발생하면 stderr warning / `.vibelign/state.json` / GUI-visible error 중 하나로 반드시 관측 가능해야 한다.
2. **public API 유지**
   - Python `rust_engine.py`의 기존 public wrapper 함수명 유지
   - Tauri frontend가 호출하는 command name 유지
   - Rust 1-shot CLI wire format 유지
3. **한 단계마다 테스트**
   - 모듈 이동 후 바로 관련 테스트 실행
   - daemon / direct-call 기능은 리팩토링 PR에 섞지 않음
4. **폴더 기준으로 책임 분리**
   - 큰 파일을 무작위로 쪼개지 않고, 앞으로 기능이 들어갈 위치를 기준으로 나눈다.

---

## 4. 리팩토링 범위

### 4.1 필수: Tauri `lib.rs` command 모듈화

현재 `vibelign-gui/src-tauri/src/lib.rs`는 2,000줄 이상이며 Phase 3 direct bridge가 들어갈 공간이 없다.

목표 구조:

```text
vibelign-gui/src-tauri/src/
  lib.rs                    # 앱 조립만: plugin, state, invoke_handler, run()
  commands/
    mod.rs
    vib_bridge.rs           # run_vib, run_vib_with_progress, VibResult, progress parsing
    docs.rs                 # read_file, docs index, docs visual, extra doc sources, AI enhance
    watch.rs                # WatchState, start/stop/status/logs/errors
    gui_error.rs            # record_gui_error, queue, flush batching
    settings.rs             # API key store, recent projects, env key status
    project_summary.rs      # read_project_summary, git summary helpers
# core_bridge/ 는 이번 PR 에서 만들지 않는다 (Phase 3 PR 에서 신설).
```

이동 기준:

- `lib.rs`에는 `pub fn run()`과 command registration wiring만 남긴다.
- 기존 Tauri command 이름은 유지한다.
- `tauri::generate_handler![]`에는 새 모듈 경로를 명시한다.
- `WatchState`, `GuiErrorState`, `OnboardingState`처럼 `.manage()`가 필요한 state는 모듈의 public type으로 노출한다.
- `generate_handler![]`가 새 모듈 경로를 참조할 수 있도록 command 함수 / DTO / state wrapper에는 필요한 최소 visibility를 부여한다. 기본은 `pub(crate)`이고, 외부 crate 공개가 필요한 경우에만 `pub`를 사용한다.
- **공유 state/DTO/runtime 타입 위치 결정 (BLOCKING)**: `WatchState`/`GuiErrorState`/`VibResult`/`WatchRuntime` 등 state/DTO/runtime 타입 다수가 다른 commands 모듈에서도 참조될 수 있다. 두 가지 안 중 하나를 PR 시작 전에 고정한다.
  - 안 A: `commands/state.rs` 단일 파일에 모든 공유 state 정의, 각 모듈은 `use super::state::*` 로 참조.
  - 안 B: state 를 정의하는 모듈(예: `watch.rs`)에서 `pub` 노출, 다른 모듈이 import.
  - 어느 안이든 circular import / 모듈 분리 실패를 방지한다.
- **`core_bridge/` placeholder 정책**: 이번 PR 에서는 `mod.rs` 만 두지 않고 폴더 자체를 만들지 않는다. Phase 3 PR 에서 신설. 비어있는 `mod.rs` 가 `unused`/`dead_code` lint 를 유발하는 위험을 차단한다.
- **Cross-platform 엣지 케이스 (Windows/macOS) 보존**:
  - `CREATE_NO_WINDOW` (0x0800_0000) 인라인 const / `hide_console` helper 가 현재 Tauri crate 여러 위치에 흩어져 있다. 이번 PR 에서는 범위를 넓히지 말고, **`lib.rs` 에서 commands/ 로 이동되는 코드에 한해서만** `commands/platform.rs` 로 단일화한다.
  - `vib_path.rs` / `onboarding/*` 의 `hide_console` 은 이번 PR 에서 건드리지 않는다. 전체 Tauri crate 공통 platform helper 로 통합하는 작업은 별도 cleanup PR 로 분리한다.
  - `lib.rs:803-887` 의 watch I/O 스레드는 Windows / Unix 페어 함수 (`spawn_watch_log_thread`, `spawn_watch_error_thread`) 가 `#[cfg(target_os = "windows")]` 와 `#[cfg(not(target_os = "windows"))]` 로 분기되어 있다. `commands/watch.rs` 로 옮길 때 cfg 블록 페어를 깨뜨리지 않는다 (한쪽만 옮기면 빌드 실패).
  - `vib_path::BUNDLED_VIB_PATH` (`OnceLock<PathBuf>`) 는 macOS `.app/Contents/Resources/vib-runtime/vib` 경로 보존 위해 setup() 에서 한 번 set 됨. PR 1 에서 setup 호출 위치가 옮겨지면 OnceLock set 시점 race 가능 — `lib.rs::run()` 안의 setup 훅 안에서만 set 하는 현재 패턴 유지.

완료 기준:

- `lib.rs`가 앱 bootstrap 중심으로 축소된다.
- frontend TypeScript 호출부 수정이 없어야 한다.
- `cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml` 통과.
- **`cd vibelign-gui && npm run build` 통과** (Vite 빌드로 frontend import path 깨짐 차단).
- **command registration parity 검증**: frontend `invoke("name")` 호출 목록과 `generate_handler![]` 등록 목록이 동일함을 grep 스크립트로 확인한다. `onboarding::...`처럼 모듈 경로로 등록된 command 도 같은 이름으로 매칭해야 한다. cargo test 만으로는 dead command 가 잡히지 않는다.
- 가능하면 `tauri dev` 부팅 1회로 각 탭 진입 시 런타임 에러 0개 확인.

---

### 4.2 필수: Python Rust engine transport 분리

현재 `rust_engine.py`는 binary discovery, sha 검증, subprocess transport, request wrapper가 섞여 있다. daemon client가 추가되면 이 파일이 가장 먼저 복잡해진다.

목표 구조:

```text
vibelign/core/checkpoint_engine/
  rust_engine/                  # rust_engine.py 를 패키지로 전환 (Python: 같은 부모에 .py + 폴더 공존 불가)
    __init__.py                 # 기존 public wrapper 유지: create/list/restore/..._with_rust
                                #   (모든 wrapper 함수를 __init__.py 로 옮겨 import path 보존)
    discovery.py                # _binary_name, candidate paths, sha256, integrity check
    transport_oneshot.py        # call_rust_engine 1-shot subprocess 구현
# daemon_client.py 는 이번 PR 에서 만들지 않는다 (Phase 1 daemon 구현 PR 에서 신설).
# mode.py 도 이번 PR 에서 만들지 않는다. 이름이 넓어져 fallback/transport 정책을 섞기 쉽다.
```

⚠️ **import path 보존**: `from vibelign.core.checkpoint_engine.rust_engine import call_rust_engine` 가 그대로 동작해야 한다. `__init__.py` 가 `from .transport_oneshot import call_rust_engine` 등으로 모든 public symbol 을 re-export 한다.

이동 기준:

- `create_checkpoint_with_rust`, `list_checkpoints_with_rust` 등 기존 import 경로는 유지한다.
- `call_rust_engine()`도 우선 기존 이름을 유지하되 내부 구현만 `transport_oneshot.py`로 위임한다.
- daemon 구현은 넣지 않는다. **`daemon_client.py` 파일은 이번 PR 에서 만들지 않는다** — 빈 파일이 import path 에 노출되면 dead module 이 된다. Phase 1 daemon 구현 PR 에서 신설.
- `mode.py`는 만들지 않는다. `VIBELIGN_ENGINE_DAEMON=1` transport 선택은 Phase 1 daemon PR 에서 `daemon_client.py` 와 함께 결정한다. 실패/required/fallback 판단은 PR 4 의 `fallback_policy.py` 로 모은다.
- **Cross-platform 엣지 케이스 (Windows/macOS) 보존**:
  - `discovery.py` 가 현재 `_candidate_paths` 의 **4종 경로** 를 모두 보존해야 한다: (1) `VIBELIGN_ENGINE_PATH` env, (2) PyInstaller 번들 (`sys._MEIPASS`), (3) `sys.executable` 옆 `_internal/vibelign/_bundled/`, (4) dev source tree (`vibelign-core/target/{debug,release}/`). 한 종류만 남기면 PyInstaller onedir 빌드 (사이드카) 또는 dev 빌드 어느 쪽이든 깨진다.
  - `_binary_name()` 의 `sys.platform == "win32"` 분기 (`vibelign-engine.exe` vs `vibelign-engine`) 는 discovery.py 로 따라 이동.
  - `transport_oneshot.py` 의 `subprocess.run` 은 `WINDOWS_SUBPROCESS_FLAGS` (CREATE_NO_WINDOW) 를 그대로 유지. macOS 에서는 0 으로 정의되므로 분기 불필요.
  - `subprocess.run(cwd=root)` 가 Windows 에서 `\\?\` UNC prefix 가 포함된 root 를 받으면 `CreateProcess` 가 거부 (error 267) 한다. 현재는 호출자가 정규화해서 넘기는 가정 — PR 2 에서 이 가정을 주석으로 명시한다 (정규화 로직은 daemon plan 에서 추가).

완료 기준:

- 기존 tests의 import path가 깨지지 않는다.
- `uv run --with pytest python -m pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py tests/test_mcp_checkpoint_handlers.py -q` 통과.
- **import smoke**: `uv run python -c "from vibelign.core.checkpoint_engine.rust_engine import call_rust_engine, find_rust_engine, create_checkpoint_with_rust, list_checkpoints_with_rust, restore_checkpoint_with_rust, diff_checkpoints_with_rust, preview_restore_with_rust, restore_files_with_rust, restore_suggestions_with_rust, prune_checkpoints_with_rust, apply_retention_with_rust, inspect_backup_db_with_rust, maintain_backup_db_with_rust, backup_graph_summary_with_rust"` 가 ImportError 없이 통과.

---

### 4.3 권장: `RustCheckpointEngine` fallback policy 분리

`rust_checkpoint_engine.py`는 Rust 호출과 Python fallback, env flag, state 기록, legacy merge 정책을 함께 들고 있다. daemon 도입 후에는 fallback 경로가 `daemon → 1-shot → Python`으로 늘어난다.

목표 구조:

```text
vibelign/core/checkpoint_engine/
  rust_checkpoint_engine.py  # CheckpointEngine 구현 중심
  fallback_policy.py         # env flag, fallback marker, required mode, state recording
```

이동 기준:

- `_rust_disabled`, `_rust_required`, `_is_environment_fallback`, `_record_engine_state`, `_is_protocol_compatibility_fallback`을 분리한다.
- `fallback_policy.py` 는 Rust 실패 이후의 판단만 담당한다: Rust 비활성화 여부, Rust 필수 모드 여부, 환경 문제 fallback 가능 여부, protocol compatibility fallback marker, engine state 기록.
- **fallback 정책은 fail-fast 우선**으로 둔다. ⚠️ **이 정책은 PR 4 에서 "선언" 만 하고 코드 동작은 변경하지 않는다.** §3 "기능 변경 금지" 원칙과 충돌하지 않도록, 실제 fail-fast 강제는 daemon plan Phase 1 (V2 envelope 도입 시) 또는 별도 후속 PR 에서 처리한다.
  - 허용: 사용자가 명시적으로 Rust를 끈 경우(`VIBELIGN_DISABLE_RUST_CHECKPOINT`), 배포/환경 문제로 Rust binary 를 찾지 못한 경우, 기존 legacy Python checkpoint 를 복구해야 하는 경우, **버전 skew 시 graceful upgrade path** (구 binary + 신 client 또는 그 반대 — 현재 `_is_protocol_compatibility_fallback` 가 `inspect_backup_db` / `backup_graph_summary` 에서 처리 중인 경로).
  - 금지: 데이터 무결성 오류, daemon opt-in 경로의 request correlation 오류, checksum/integrity 의심, Rust 내부 로직 오류. 이 경우 Python fallback 으로 숨기지 말고 에러를 내서 디버그 가능하게 한다.
  - **protocol mismatch 의 분류**: graceful upgrade window 안의 known unknown variant 는 "허용" (위 graceful upgrade path), 그 외 wire shape 위반은 "금지". 이 분류 기준은 daemon plan Phase 1 의 V2 envelope 설계와 함께 정밀화한다.
  - 개발자/CI/GUI Rust 백업 화면처럼 정확한 Rust 경로 검증이 필요한 곳은 `VIBELIGN_REQUIRE_RUST_CHECKPOINT=1` 또는 동등한 strict 정책으로 fallback 을 차단한다.
- `mode.py` 는 만들지 않는다. transport 선택(1-shot vs daemon)과 fallback 판단을 한 파일에 섞지 않기 위해서다. Phase 1 에서 transport 선택 로직이 커지면 그때 `transport_selector.py` 같은 더 구체적인 이름을 검토한다.
- `RustCheckpointEngine`의 method behavior는 유지한다.
- `checkpoint_has_changes`는 현재 Python fallback 경로를 유지하되, Phase 1에서 Rust/daemon 흡수 여부를 별도 결정한다.
- **method 본체에 박힌 정책 분기는 옮기지 않는다 (명시적 결정)**:
  - `list_checkpoints` (line 110-122) 의 Rust + legacy Python merge 분기
  - `inspect_backup_db` / `backup_graph_summary` (line 223, 240) 의 protocol compatibility fallback 호출
  - 이유: helper 가 아니라 method 본체 흐름에 속함. 분리 시 method 가독성 더 떨어짐. fallback marker helper 만 추출하고 호출 위치는 유지.
- **PR 2 의존성**: PR 2 는 `mode.py` 를 만들지 않으므로, PR 4 는 `fallback_policy.py` 를 단일 정책 helper 로 신설한다. env flag/marker/state 기록이 두 파일에 흩어지지 않도록 한다.

완료 기준:

- fallback warning/state 기록 테스트가 그대로 통과한다.
- `VIBELIGN_DISABLE_RUST_CHECKPOINT`, `VIBELIGN_REQUIRE_RUST_CHECKPOINT` 의미가 그대로 유지된다.
- `RUST_ENGINE_PROTOCOL_ERROR` / `unknown variant` marker 분기 동작이 `inspect_backup_db` / `backup_graph_summary` 에서 유지된다.

---

### 4.4 권장: Rust IPC protocol 타입/handler 분리

현재 `vibelign-core/src/ipc/protocol.rs`는 request/response 타입과 `handle()` 구현이 함께 있다. V2 daemon envelope, `Shutdown`, `EngineVersion`이 들어오면 protocol 계약과 실행 로직이 섞인다.

목표 구조:

```text
vibelign-core/src/ipc/
  mod.rs
  protocol.rs               # EngineRequest, EngineResponse, V2 envelope 타입
  handler.rs                # handle(request) 구현
# daemon.rs 는 이번 PR 에서 만들지 않는다 (Phase 1 daemon 구현 PR 에서 신설).
```

이동 기준:

- `EngineRequest` / `EngineResponse` wire shape는 유지한다.
- `main.rs`의 1-shot 흐름은 유지한다.
- `protocol.rs::handle`을 바로 없애기보다, 필요하면 compatibility re-export로 점진 이동한다.
- **handler.rs 분할 정책 결정**: `handle()` 의 각 arm 은 `crate::backup::{checkpoint, retention, db_maintenance, db_viewer, diff, graph_summary, restore, suggestions}` 8 개 모듈을 호출한다. 이번 PR 에서는 단일 `handler.rs` 로 시작하되, V2 daemon command (`Shutdown`, `EngineVersion`) 추가 시 split 기준 (예: `handler/backup.rs` vs `handler/daemon.rs`) 을 Phase 1 PR 에서 결정한다.
- **`daemon.rs` placeholder 정책**: 이번 PR 에서는 `daemon.rs` 파일을 만들지 않는다. Phase 1 daemon 구현 PR 에서 신설하며, 그때 `mod.rs` 에 `pub mod daemon;` 을 추가한다.

완료 기준:

- `cargo test --manifest-path vibelign-core/Cargo.toml` 통과.
- 1-shot stdin JSON → stdout JSON 동작이 그대로 유지된다.

---

## 5. 리팩토링하지 않을 것

이번 선행 작업에서는 아래를 건드리지 않는다.

- daemon transport 구현
- `VIBELIGN_ENGINE_DAEMON=1` 실제 분기
- Tauri → `vibelign-core` 직접 호출 구현
- `project_scan`, `secret_scan`, `strict_patch`, `patch_validation` Rust 이전
- backup/CAS/restore 내부 알고리즘 변경
- CLI/GUI 출력 문구 변경
- MCP tool spec 변경

이 항목들은 리팩토링 이후 별도 Phase에서 처리한다.

---

## 6. 권장 PR 순서

### 6.0 PR 의존 그래프

```text
PR 1 (Tauri commands)     ← 독립. daemon plan 과 무관하게 단독 가치 있음. 즉시 시작 권장.
PR 3 (Rust IPC handler)   ← 독립. PR 1 과 병렬 가능.
PR 2 (Python transport)   ← 독립. PR 1 과 병렬 가능.
PR 4 (fallback policy)    ← PR 2 의존. PR 2 에서 mode.py 를 만들지 않은 상태에서 fallback_policy.py 를 단일 정책 helper 로 신설.
```

- **PR 1, 2, 3 은 서로 다른 언어/디렉터리 → 병렬 머지 안전.**
- **PR 4 는 PR 2 머지 후 시작.** 같은 `vibelign/core/checkpoint_engine/` 패키지 안에서 helper 가 두 PR 에 흩어지면 conflict + 책임 모호. PR 2 는 transport/discovery 만, PR 4 는 fallback policy 만 담당한다.
- **머지 순서 권장**: PR 1 → (PR 2 + PR 3 병렬) → PR 4. PR 1 을 먼저 머지하는 이유는 가장 큰 LOC reduction 이고 daemon plan 과 무관하게 단독 가치가 있기 때문.

---

### PR 1 — Tauri command 폴더화

목표:

- `lib.rs`를 앱 조립 파일로 축소한다.
- `commands/` 폴더를 만들고 docs/watch/settings/error/vib bridge를 이동한다.

검증:

```bash
cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml
cd vibelign-gui && npm run build
```

추가 검증 (cargo test 만으로는 dead command 미검출):

- `generate_handler![]` 등록 목록과 frontend `invoke("name", ...)` 호출 목록 diff 가 빈 집합인지 grep 으로 확인.
- 가능하면 `tauri dev` 부팅 1회로 각 탭 진입 시 콘솔 에러 0개 확인.

성공 기준:

- Tauri tests 통과
- frontend Vite 빌드 통과
- frontend 호출부 변경 없음
- 기능 추가 없음

---

### PR 2 — Python Rust engine transport 경계 분리

목표:

- discovery / integrity / one-shot transport를 분리한다.
- 기존 public wrapper import path를 유지한다.

검증:

```bash
uv run --with pytest python -m pytest \
  tests/test_checkpoint_rust_engine.py \
  tests/test_checkpoint_engine_router.py \
  tests/test_mcp_checkpoint_handlers.py \
  -q
```

성공 기준:

- Rust checkpoint fallback 테스트 통과
- MCP checkpoint handlers 테스트 통과
- `VIBELIGN_ENGINE_PATH` / integrity behavior 유지

---

### PR 3 — Rust IPC handler 분리

목표:

- `protocol.rs`는 wire contract 중심으로 유지한다.
- request 처리 로직은 `handler.rs`로 이동한다.
- 이후 daemon envelope와 daemon runtime이 들어갈 자리를 만든다.

검증:

```bash
cargo test --manifest-path vibelign-core/Cargo.toml
```

1-shot wire contract smoke (cross-platform):

- **권장**: Rust integration test 로 작성 — `vibelign-core/tests/engine_info_smoke.rs` 에서 자식 프로세스로 binary 실행 + stdin write + stdout assert. `cargo test` 한 번으로 macOS/Windows/Linux 모두 검증.
- **임시 수동 smoke** (Unix/macOS): `printf '{"command":"engine_info"}' | cargo run --quiet --manifest-path vibelign-core/Cargo.toml`
- **임시 수동 smoke** (Windows PowerShell): `'{"command":"engine_info"}' | cargo run --quiet --manifest-path vibelign-core/Cargo.toml`
- ⚠️ `printf` 는 Windows cmd/PowerShell 에 기본 내장이 아니므로 위 명령을 그대로 CI 에 넣으면 Windows runner 에서 실패한다.

성공 기준:

- Rust core tests 통과
- `EngineInfo` 1-shot behavior 유지
- `[[bin]] vibelign-engine` 경로 유지
- 1-shot smoke 출력에 `"status":"ok"` 와 `"result":"engine_info"` 가 포함됨
- smoke 테스트가 macOS/Windows/Linux 모두에서 통과 (integration test 채택 시 자동)

---

### PR 4 — fallback policy 정리

목표:

- `RustCheckpointEngine`에서 env/fallback/state helper를 분리한다.
- daemon 도입 시 `daemon → 1-shot → Python` 정책을 넣을 위치를 명확히 한다.

검증:

```bash
uv run --with pytest python -m pytest \
  tests/test_checkpoint_rust_engine.py \
  tests/test_checkpoint_engine_router.py \
  -q
```

성공 기준:

- environment fallback behavior 유지
- required Rust mode behavior 유지
- `.vibelign/state.json` 기록 behavior 유지
- 기존 visible fallback 경로(stderr warning / `.vibelign/state.json` 기록)가 유지되고, 새 silent fallback 이 추가되지 않음
- **`_is_protocol_compatibility_fallback` 분기 동작은 그대로 유지** (graceful upgrade path — 코드 변경 없음). fail-fast 강제는 daemon plan Phase 1 에서 처리.

---

## 7. 다음 단계 연결

이 리팩토링이 끝난 뒤에만 아래 작업을 시작한다.

1. Phase -1 결정 고정
   - per-root daemon
   - official dual-mode
   - V2 transport envelope `{request_id, payload}`
   - request-level DB open/close 유지
   - **lib.rs expose 대상 결정**: PR 3 머지 후 `vibelign-core` 의 어떤 모듈을 lib 로 expose 할지 (handler 만? protocol+handler? backup 까지?) 를 Phase 0 시작 전에 정한다. 이 결정은 Tauri direct bridge 의 import surface 와 빌드 사이즈에 직결된다.
2. Phase 1 daemon opt-in 구현
   - `VIBELIGN_ENGINE_DAEMON=1`
   - daemon client startup/reconnect/timeout
   - `EngineVersion`, `Shutdown`
   - **placeholder 신설**: 이 PR 에서 비로소 `vibelign/core/checkpoint_engine/rust_engine/daemon_client.py` 와 `vibelign-core/src/ipc/daemon.rs` 를 만든다 (리팩토링 PR 에서는 만들지 않았음).
3. Phase 3 direct core bridge
   - `vibelign-gui/src-tauri/src/core_bridge/` 신설 (리팩토링 PR 에서는 만들지 않았음)
   - `core_bridge/checkpoint.rs`
   - checkpoint/history/backup-db 계열부터 Tauri direct call 적용
   - Python `run_vib` fallback 유지

---

## 8. 체크리스트

### 시작 전 결정 (BLOCKING)
- [x] PR 1: 공유 state 타입 위치 (안 A: `commands/state.rs` 단일 파일 vs 안 B: 정의 모듈에서 pub re-export) 고정
- [x] PR 4: PR 2 머지 완료 확인 + `mode.py` 미생성 확인 + `fallback_policy.py` 단일 정책 helper 로 진행

### PR 진행
- [x] PR 1에서 Tauri command 모듈 분리 완료
- [ ] PR 1 검증: `cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml` — 최종 daemon slice 에서는 재실행하지 않음. 집 컴퓨터에서 이어받을 때 한 번 더 확인.
- [ ] PR 1 검증: `cd vibelign-gui && npm run build` — 최종 daemon slice 에서는 재실행하지 않음. 집 컴퓨터에서 이어받을 때 한 번 더 확인.
- [ ] PR 1 검증: `generate_handler![]` 등록 ↔ frontend `invoke()` 호출 parity grep (`onboarding::...` command 포함) — 최종 daemon slice 에서는 재실행하지 않음.
- [x] PR 2에서 Python Rust engine transport 분리 완료 (`rust_engine.py` → `rust_engine/` 패키지)
- [x] PR 2 검증: checkpoint/MCP pytest 통과
- [x] PR 2 검증: import smoke (`uv run python -c "from vibelign.core.checkpoint_engine.rust_engine import ..."`)
- [x] PR 3에서 Rust IPC handler 분리 완료
- [x] PR 3 검증: `cargo test --manifest-path vibelign-core/Cargo.toml`
- [x] PR 3 검증: 1-shot wire contract smoke (권장: `vibelign-core/tests/engine_info_smoke.rs` integration test 로 cross-platform 자동화. 임시 수동 smoke 는 Unix `printf | cargo run` 또는 PowerShell `'...' | cargo run` — Windows cmd 는 미지원)
- [x] PR 4에서 fallback policy 분리 완료 (helper 만, method 본체 분기는 유지)
- [x] PR 4 검증: `RUST_ENGINE_PROTOCOL_ERROR` / `unknown variant` fallback 동작 회귀 없음

### 마무리
- [x] placeholder 파일 (`daemon_client.py`, `daemon.rs`, `core_bridge/`) 이 신설되지 않았는지 확인 — 리팩토링 단계에서는 미생성, daemon 단계에서 `daemon_client.py` / `daemon.rs` 실제 구현 추가됨.
- [x] 기능 변경 없음 확인 (CLI/GUI/MCP 출력 shape, fallback 동작, env flag 의미 동일)
- [x] Rust daemon 계획 문서의 Phase -1/1 구현 범위 재검토
- [x] Phase 0 시작 전: PR 3 머지 후 lib.rs expose 대상 모듈 결정 — Phase 0/3 직전까지 보류, 현재 daemon Phase 1 은 binary/IPC 경로만 사용.
