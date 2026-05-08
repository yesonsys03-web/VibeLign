# VibeLign Error Reporting Policy Design

Date: 2026-05-06
Status: Draft (Phase 0 — 정책 확정 + MVP 구현 준비)

## 1. Why This Direction

VibeLign 은 사용자의 로컬 개발 환경에서 동작하는 CLI + GUI 도구다. 사용자 환경에서 어떤 에러가 발생하는지 우리는 지금 아무것도 모른다. 사용자가 직접 깃허브 이슈를 만들지 않으면 버그는 사실상 보고되지 않고, 보고되더라도 재현 정보가 충분치 않다.

문제는 단순히 "에러를 모은다" 가 아니라:

- **프라이버시**: 로컬 경로(`/Users/...`), API 키, 사설 IP, 내부 호스트명은 절대 사용자 동의 없이 외부로 나가서는 안 된다.
- **신호 vs 동의의 트레이드오프**: 자동 telemetry 는 신호량이 많지만 한국 개발자 도구 정서상 부담이 크다. 수동 업로드는 안전하지만 사용자가 보고하지 않으면 우리가 모르는 버그가 누적된다.
- **이미 있는 자산**: `vibelign/core/memory/redaction.py` 의 redact_memory_text/redact_memory_path, `vibelign/core/secret_scan.py` 의 시크릿 스캐너가 성숙해 있다. 이 자산을 재사용하지 않으면 보안 일관성이 깨진다.

따라서 이 스펙이 정의하는 정책은 **로컬 우선, 업로드 opt-in, 마스킹 의무화** 의 3 원칙이다.

## 2. Three-Tier Error Reporting Policy

### Tier 1 — Always-On Local Logging (기본 활성, 사용자 마찰 0)

모든 unhandled exception 은 자동으로 로컬 JSONL 파일에 적재된다.

- **위치**: `.vibelign/logs/cli-error-YYYYMMDD.jsonl`, `.vibelign/logs/gui-error-YYYYMMDD.jsonl`
- **형식**: 1 라인 = 1 에러, JSON 객체
- **마스킹 의무**: 적재 시점에 `error_log.py` 의 canonical redaction 패스 (= `redact_memory_text` + token-prefix 보강 + Windows-broad path 보강) 통과. raw 값이 디스크에 닿기 전에 마스킹 완료. 세부 불변식은 §3.1 참고.
- **보존**: 일자별 파일, 30 일 후 자동 회전(삭제). 파일당 1000 라인 상한.
- **외부 전송 없음**: Tier 1 단계에서는 디스크에만 쓴다. 네트워크 호출 0.
- **Off 스위치**: `.vibelign/config.yaml` 에 아래 nested 설정으로 끌 수 있다 (기본 true). 기존 top-level 설정들과 달리 error-reporting 계열 옵션이 늘어날 것을 대비해 `error_reporting` namespace 를 명시적으로 도입한다.

```yaml
error_reporting:
  local_log: false
```

### Tier 2 — Opt-In Manual Bug Report (명시적 사용자 행위)

사용자가 명시적으로 `vib report-bug` 를 실행하거나 GUI 의 "버그 리포트" 버튼을 누를 때만 동작한다.

- **CLI**: `vib report-bug [--last N] [--include-system] [--out PATH]`
  - 최근 N 개(기본 5) 에러를 모아 마크다운 리포트로 묶음
  - 시스템 정보(OS, Python 버전, vib 버전, Rust 엔진 유무) 포함
  - 두 번째 redaction pass 실행 (defense in depth)
  - 결과를 `.vibelign/reports/bug-TIMESTAMP.md` 에 저장하고, 사용자에게 (a) 파일 경로 (b) GitHub 이슈 신규 생성 URL (제목/본문 query string 채움) 을 보여줌
  - `--upload` 플래그는 v2 까지는 미구현 (의도적 보류)
- **GUI**: Settings 또는 About 페이지에 "버그 리포트 만들기" 버튼. CLI 와 같은 흐름을 Tauri invoke 로 호출.
- **사용자 동의**: 매 실행마다 "다음 파일이 `.vibelign/reports/bug-*.md` 에 생성됩니다. 직접 열어보고 GitHub 등에 첨부하면 내용이 공개됩니다. 생성 진행할까요?" 확인. 묵시적 동의 금지. 파일 생성과 공개(첨부) 는 사용자가 두 단계로 결정한다.

### Tier 3 — Future: Remote Aggregation (현재는 명시적으로 보류)

Sentry/Bugsnag 류 자동 원격 적재는 v2.x 에서 다루지 않는다. 도입 시점에 별도 스펙 필요. 본 정책은 **Tier 3 가 없다는 사실 자체를 명시** 함으로써 사용자에게 "기본은 로컬에서 끝난다" 를 약속한다.

## 3. Privacy Contract (사용자 약속)

다음을 정책으로 못박는다 — 코드 변경이 이 약속을 깨면 그 코드가 잘못된 것이다.

1. **Tier 1 은 디스크 외 전송 0.** 어떤 네트워크 호출도 발생하지 않는다.
2. **모든 에러 페이로드는 적재 전에 마스킹 통과.** CLI 와 GUI 모두 동일한 `error_log.py` canonical pass (`redact_memory_text` + token-prefix 보강 + Windows-broad path 보강) 통과. GUI 경로는 §3.1 GUI buffer + async flush 메커니즘으로 메모리 버퍼만 거치고 Python writer 가 마스킹 후 디스크에 적재 — raw payload 는 어떤 시점에도 디스크에 닿지 않는다. 시크릿 적중 시 카운터 증가, 원본 노출 0.
3. **Tier 2 업로드 흐름은 매번 명시적 동의 요구.** "이번 한 번만 자동" 같은 묵시적 옵트인 금지.
4. **사용자가 로그 디렉토리 직접 열람 가능.** `.vibelign/logs/` 는 사용자 소유. `vib report-bug --out -` 는 stdout 으로도 출력.
5. **로그 회전 시 hard delete.** 보존 정책 만료 후 archive 로 옮기지 않고 삭제.

## 3.1 Implementation Invariants

구현자가 아래 불변식을 깨면 정책 구현이 아니라 정책 위반이다.

- **Best-effort only**: error logging 실패는 원래 unhandled exception 출력/종료 흐름을 가리면 안 된다. writer 실패는 silent drop 또는 stderr debug 수준으로 끝낸다.
- **Redact before disk**: report generation 단계가 아니라 JSONL write 직전에 마지막 redaction pass 를 수행한다.
- **Traceback structure preserved**: traceback/stack 은 프레임·라인 경계를 유지해야 한다. `redact_memory_text` 를 그대로 호출해 전체 traceback 을 한 줄로 collapse 하지 말고, traceback 저장 전용 wrapper 가 각 라인에 동일 masking 규칙을 적용한다.
- **Version source of truth**: `vib_version` 은 `importlib.metadata.version("vibelign")` 을 우선 사용하고, 실패 시 `vibelign.__version__` 또는 `"unknown"` 으로 fallback 한다. GUI `app_version` 도 Tauri package metadata 또는 동일 vib package version 중 하나로 source 를 고정한다.
- **Git hygiene**: `vib start`/init 계열 gitignore 기본 패턴에 `.vibelign/logs/` 와 `.vibelign/reports/` 를 추가한다.
- **Token-prefix coverage**: `redact_memory_text` 의 라벨 기반 매칭(`api_key=`, `token:` 등)으로는 Bearer/Authorization 헤더에 raw 로 노출되는 토큰을 잡지 못한다. `error_log.py` 는 알려진 시크릿 prefix 패턴(`sk-ant-`, `sk-`, `ghp_`, `gho_`, `xoxb-`, `xoxp-`, `AKIA`, `AIza`, `ya29.`) 을 prefix 단독으로도 마스킹하는 보강 패스를 자체 보유한다. 신규 prefix 가 발견되면 본 스펙이 아니라 `error_log.py` 의 패턴 목록을 단일 source 로 유지한다.
- **Single redaction source of truth**: token-prefix / path / IP / internal-host secret 패턴은 Python `error_log.py` 에 단일 source 로 둔다. GUI 측 Rust `record_gui_error` 는 raw GUI error payload 를 직접 JSONL 에 append 하지 않고 Python `error_log.py record_gui_error` 경로로 전달한다. Python writer 는 JSONL write 직전에 canonical redact (`redact_memory_text` + token-prefix 보강 + Windows-broad path 보강) 를 수행한 뒤 append 한다. Python 경로 호출이 실패하면 GUI reporter 는 raw payload 를 디스크에 쓰지 않고 silent drop 한다. Rust 에 동일 secret 패턴을 복제하지 않는 이유는 패턴 동기화 누락 리스크를 피하기 위해서이며, 이 선택은 §3 Privacy Contract 1·2 의 "디스크 닿기 전 마스킹" 보장을 유지하는 방향으로 제한된다.
- **Atomic append**: `.vibelign/logs/*.jsonl` 단일 라인 write 는 cross-platform 으로 직렬화한다. POSIX 는 `fcntl.flock`, Windows 는 `msvcrt.locking` 을 사용한다. 추가로 라인 길이는 8KB 로 cap 하고 초과분은 끝에 `…[truncated]` 마커로 자른다. 이 두 장치로 CLI + MCP server + GUI subprocess 의 동시 쓰기를 안전하게 만든다.
- **Anchor placement**: Phase 1 의 `cli_runtime.py` excepthook 등록은 기존 `CLI_RUNTIME_RUN_CLI_START/END` 앵커 내부에 추가한다. 새 앵커 블록을 만들지 않는다 — project_map 재생성 트리거를 피하고 `run_cli()` 와 excepthook 의 lifecycle 을 같은 단위로 유지한다.
- **Filename-safe timestamp**: 모든 파일명용 timestamp 는 Windows NTFS 금지 문자(`:`, `*`, `?`, `"`, `<`, `>`, `|`)를 포함하지 않는다. Bug report 번들은 `bug-YYYYMMDD-HHMMSSZ.md` (UTC) 형태로 통일한다. ISO 8601 의 `:` 는 파일명에 들어갈 수 없다.
- **Windows-broad path coverage**: `redact_memory_text` 의 `_LOCAL_PATH_RE` 는 `/Users`, `/home`, `C:\Users\` 만 잡는다. Windows 개발자가 `D:\dev\<project>`, `C:\Projects\<client>` 에 코드를 두면 그 경로가 그대로 디스크에 박힌다. `error_log.py` 는 보강 패턴 `[A-Za-z]:\\[^\s\`'"]+` (모든 Windows 드라이브 경로) 와 `file:///[A-Za-z]:/[^\s\`'"]+` (URL 형태) 를 추가로 적용한다. macOS `.app` 번들 경로(`/Applications/...`) 도 같은 패턴 목록에 포함한다. 신규 패턴은 `error_log.py` 가 단일 source.
- **Line ending discipline**: Python 텍스트 모드 `open(path, "a")` 는 Windows 에서 `\n` → `\r\n` 으로 자동 변환되어 JSONL 파서를 깨뜨린다. JSONL writer 는 `open(path, "a", encoding="utf-8", newline="")` (텍스트 모드 + 변환 비활성) 또는 `"ab"` (바이너리 append) 둘 중 하나로 통일한다. GUI 경로도 Rust 가 직접 파일을 쓰지 않고 Python writer 를 호출하므로 동일 writer 규칙을 따른다.
- **UTF-8 round-trip**: `json.dumps(..., ensure_ascii=False)` 로 직렬화하고 파일은 항상 UTF-8 인코딩으로 연다. 한국어 에러 메시지("API 키가 없습니다" 등) 가 `\uHHHH` 이스케이프 형태로 변환되면 마스킹 정규식이 매칭에 실패하고 사용자가 직접 로그를 열 때도 가독성이 깨진다.
- **Lock helper**: `vibelign/core/file_lock.py` 에 `with file_lock(path):` context manager 를 도입한다. POSIX 는 `fcntl.flock(fd, LOCK_EX)`, Windows 는 file 의 현재 위치에서 `msvcrt.locking(fd, LK_LOCK, 1)` 으로 1 byte 락 (실용적 직렬화). 두 API 의 시그니처/의미가 달라 단순 if-else substitution 은 사고로 직결된다. lock 타임아웃 5초, 초과 시 silent skip (Best-effort only 와 정합).
- **UTC-based file rotation**: 일자별 로그 파일명(`cli-error-YYYYMMDD.jsonl`)의 날짜는 UTC 기준으로 결정한다. `ts` 필드가 `Z` (UTC) 인데 파일명이 local time 이면 자정 무렵 발생한 같은 에러 묶음이 두 파일로 갈라져 `vib report-bug` 의 "최근 N개" 추출이 어긋난다.
- **Tauri subprocess on Windows**: Phase 2 의 `vib log-gui-error --batch` background flush subprocess 와 Phase 3/4 의 `vib report-bug` 사용자 트리거 subprocess 모두에 적용된다. Windows 는 (a) entry point 가 `vib.exe` (pip Scripts dir) 임에 유의 — 절대 경로 resolve 또는 `where vib` lookup, (b) 콘솔 깜빡임 방지를 위해 기존 `vibelign.core.structure_policy.WINDOWS_SUBPROCESS_FLAGS` (= `subprocess.CREATE_NO_WINDOW`) 를 재사용한다. Phase 2 의 flush 는 매 5초/10건마다 호출되므로 (b) 누락 시 에러 burst 시 사용자에게 콘솔 창이 반복적으로 깜빡인다 — GUI freeze 못지않게 사용자 체감 큰 문제.
- **Backup exclusion**: `.vibelign/logs/` 와 `.vibelign/reports/` 는 백업 스냅샷에서 제외한다. 구현은 `vibelign-core/src/backup/snapshot.rs` 의 기존 prefix-skip 블록(`rust_checkpoints/`, `rust_objects/`, `checkpoints/`)에 두 prefix 를 추가하는 형태. 이 조치 없이 Tier 1 을 활성화하면 `vib checkpoint` 가 매 회차마다 로그 전체를 dedup-실패 상태로 (로그가 계속 append 되므로 hash 가 매번 바뀜) 스냅샷에 포함시켜 백업 DB 가 비대화된다. 악조건 추산 ~480MB/30일.
- **Rotation policy on overflow**: §2 Tier 1 의 "파일당 1000 라인 상한" 이 같은 일자에 도달했을 때, 가장 오래된 라인을 drop 하지 않고 같은 일자 내에서 `-2`, `-3` 인덱스 suffix 를 붙인 새 파일 (`cli-error-YYYYMMDD-2.jsonl`, `cli-error-YYYYMMDD-3.jsonl`) 을 생성한다. 30 일 회전 삭제는 인덱스 그룹 전체(`cli-error-YYYYMMDD*.jsonl`) 단위로 수행한다. 데이터 drop 보다 디스크 공간 소모를 우선 — 사용자가 직접 삭제하거나 `vib report-bug` 로 추출하기 전까지 어떤 에러 라인도 자동으로 잃지 않는다.
- **No reporter recursion**: `error_log.py` 와 Tauri reporter 는 자신이 발생시킨 예외/실패를 다시 reporter 로 보내지 않는다. 재진입 가드는 (a) reporter 함수 전체를 try/except 로 감싸 내부 실패가 caller 로 전파되지 않게 하고 (b) 모듈 단위 thread-local flag (`_reporting_in_progress`) 로 "현재 reporting 중" 을 표시해 같은 thread 에서의 재진입을 즉시 silent skip 한다. 두 단계 모두 적용 — try/except 만으로는 동일 thread 의 재귀 호출(예: redact 함수 내부 예외 → excepthook → redact 다시 호출)을 막지 못한다.
- **GUI buffer + async flush (no UI freeze)**: GUI 에러 적재로 인한 GUI freeze/stutter 방지가 최우선. Tauri reporter 는 raw GUI error payload 를 메모리 버퍼(`Mutex<VecDeque<...>>`)에 **push 만 동기 수행** (마이크로초 단위, GUI thread 안전). flush 는 N건(기본 10) 또는 N초(기본 5) 도달 시 `tokio::spawn` 으로 background async task 에서 `vib log-gui-error --batch` subprocess 1회 호출로 Python writer 에 전달한다. **subprocess spawn 과 I/O 는 절대 GUI thread 를 블록하지 않는다 — async runtime 위에서만 실행.** Tauri 프로세스 종료 시 unflushed buffer 는 손실되며 (Best-effort only 와 정합), 메모리 버퍼가 1000건 초과 시 가장 오래된 항목부터 drop 한다. **Rotation policy on overflow 의 "데이터 drop 금지" 는 디스크 회전에만 적용**되며, in-memory buffer 는 메모리 OOM 방지를 우선한다. 이 메커니즘으로 raw payload 는 어떤 시점에도 디스크에 닿지 않는다 (§3 Privacy Contract 1·2 정합).

## 4. Log Schema

### 4.1 CLI Error Record (`cli-error-*.jsonl`)

```json
{
  "ts": "2026-05-06T11:48:23.421Z",
  "vib_version": "2.1.10",
  "python_version": "3.12.4",
  "platform": "darwin-arm64",
  "command": "vib transfer --handoff",
  "error_class": "ValueError",
  "error_message": "[masked: see redaction]",
  "traceback_redacted": ["..."],
  "redaction": {"secret_hits": 0, "privacy_hits": 2, "summarized_fields": 0}
}
```

- `command` 는 sys.argv 를 join 하되 `redact_memory_text` 통과 (인자에 시크릿이 들어왔을 가능성 대비)
- `error_message` 는 `redact_memory_text` 통과
- `traceback_redacted` 는 traceback 전용 wrapper 로 프레임/라인 구조를 보존한 채 라인별 redact
- `vib_version` 은 package metadata 를 우선 source 로 삼고, metadata 조회 실패 시 fallback 값만 사용

### 4.2 GUI Error Record (`gui-error-*.jsonl`)

```json
{
  "ts": "2026-05-06T11:48:23.421Z",
  "app_version": "2.1.10",
  "tauri_version": "2.x",
  "platform": "darwin",
  "source": "window.onerror | unhandledrejection | react.errorBoundary",
  "message_redacted": "...",
  "stack_redacted": "...",
  "url": "tauri://localhost/index.html",
  "redaction": {"secret_hits": 0, "privacy_hits": 1, "summarized_fields": 0}
}
```

- `url` 은 Tauri prod 빌드에선 보통 `tauri://localhost/<route>` 형태이고 dev 모드에선 `http://localhost:5173/<route>` 또는 file:// URL 일 수 있다. file:// URL 은 `[local-path]/<basename>` 으로 마스킹된다.
- `message_redacted`, `stack_redacted`, `url` 은 모두 Python `error_log.py record_gui_error` 의 canonical redact/write 경로를 통과한 뒤 디스크에 저장된다 (§3.1 Single redaction source of truth 참고).
- 적재 흐름: Tauri reporter → 메모리 버퍼 push (마이크로초, GUI thread 블록 안 함) → background async flush (N건/N초 도달 시) → `vib log-gui-error --batch` subprocess → Python writer canonical redact → JSONL append. 자세한 메커니즘은 §3.1 GUI buffer + async flush 참고.

### 4.3 Bug Report Bundle (`bug-*.md`)

```markdown
# VibeLign Bug Report — 2026-05-06T11:48:23Z

## System
- OS: darwin-arm64 25.2.0
- Python: 3.12.4
- vib: 2.1.10
- Rust engine: bundled / available

## Recent CLI Errors (last 5)
... (redacted JSONL pretty-printed)

## Recent GUI Errors (last 5)
... (redacted JSONL pretty-printed)

## Reproduce
(사용자가 직접 채워넣기 — 템플릿)

---
Redaction summary: secrets=0, privacy=3 (auto-masked)
```

## 5. Implementation Plan

### Phase 1 — Core log writer + Python excepthook (Tier 1 절반)

**새 파일**:
- `vibelign/core/error_log.py` — JSONL writer, 파일 회전, 마스킹 통합

**수정 파일**:
- `vibelign/cli/cli_runtime.py` — `run_cli()` 에 sys.excepthook 등록 (`CLI_RUNTIME_RUN_CLI_START/END` 앵커 내부, 새 앵커 신설 금지 — §3.1 Anchor placement 참고)
- `vibelign/core/config_loader.py` (또는 동등 위치) — nested `error_reporting.local_log` 읽기. 기존 config helper 가 top-level scalar 만 다루므로, Phase 1 에서 최소 YAML reader/writer helper 를 함께 도입한다.
- `vibelign/commands/vib_start_cmd.py` — `.vibelign/logs/`, `.vibelign/reports/` gitignore 기본 패턴 추가

**테스트**:
- `tests/test_error_log.py` — write/rotate/mask round-trip

### Phase 1.5 — Backup exclusion hardening (Tier 1 저장소 비대화 방지)

Phase 1 의 Python CLI logging MVP 를 Rust 엔진/GUI 배포 변경과 섞지 않기 위해 별도 hardening 단계로 분리한다. 단, Tier 1 이 기본 활성인 상태에서 checkpoint DB 비대화를 막아야 하므로 Phase 2 진입 전 완료한다.

**릴리즈 묶음 강제**: Phase 1 과 Phase 1.5 는 **반드시 같은 릴리즈 버전** 에 함께 포함된다. 코드 PR 은 분리하더라도 release tag 와 PyPI/GUI 번들 publish 시점은 묶는다. Phase 1 만 단독 publish 하면 Tier 1 활성 + 백업 익스클루전 부재 상태로 사용자에게 도달해 checkpoint DB 비대화가 시작되고, 업그레이드하지 않은 사용자는 영영 부풀어 오른다.

**수정 파일**:
- `vibelign-core/src/backup/snapshot.rs` — 기존 prefix-skip 블록에 `.vibelign/logs/`, `.vibelign/reports/` 두 prefix 추가 (§3.1 Backup exclusion 참고)

**테스트/검증**:
- `vibelign-core/src/backup/snapshot.rs` 의 기존 `tests/` 모듈에 회귀 케이스 추가 — `.vibelign/logs/cli-error-X.jsonl` 와 `.vibelign/reports/bug-X.md` 가 `collect()` 결과에 포함되지 않음 검증
- Cargo 빌드 + GUI 번들 재빌드 경로 확인. **버전 bump 필수**: `vibelign-core` crate 산출물이 바뀌므로 patch +1 동반. 모든 버전 파일·태그·GUI CI·PyPI publish 를 같은 값으로 통일 (메모리 규약 `feedback_version_bump_convention.md` 따름).

### Phase 2 — GUI error capture (Tier 1 나머지)

**새 파일**:
- `vibelign-gui/src/lib/errorReporter.ts` — window.onerror, unhandledrejection 핸들러
- `vibelign/commands/vib_log_gui_error_cmd.py` — `vib log-gui-error --batch` 내부용 서브커맨드. stdin 으로 받은 batched JSON 배열을 각각 `error_log.py record_gui_error` 에 통과시켜 적재한다. 사용자 직접 호출용이 아니며 Tauri flush 만 spawn 한다. help/completion/README 명령 목록에는 노출하지 않는다. 구현상 숨김 처리가 애매하면 `_log-gui-error` 처럼 internal prefix 를 사용한다.

**수정 파일**:
- `vibelign-gui/src-tauri/src/lib.rs` — `record_gui_error` Tauri 커맨드. (a) payload 를 Mutex<VecDeque> 메모리 버퍼에 push 만 동기 수행 — GUI thread 블록 0. (b) flush 트리거(N건 또는 N초 도달, 기본 10건/5초)는 `tokio::spawn` 으로 background async task 가 처리해 `vib log-gui-error --batch` subprocess 1회 호출로 Python writer 에 전달. (c) reporter 함수 자체는 try/catch + `_reporting_in_progress` flag 두 단계 가드 (§3.1 Single redaction source of truth + GUI buffer + async flush + No reporter recursion 모두 참고).
- `vibelign-gui/src/App.tsx` — errorReporter 등록 + `ErrorBoundary.componentDidCatch(error, info)` 에서 catch 한 에러도 reporter 로 전달
- `vibelign/cli/cli_command_groups.py` — `log-gui-error` 내부용 서브커맨드 등록 (사용자 노출 X — completion/help 에 노출하지 않음, 또는 `_log-gui-error` 처럼 prefix 로 internal 표기)

**테스트**:
- `vibelign-gui/scripts/test-error-reporter.mjs` (기존 vib JSON parser smoke 와 같은 패턴) — buffer push 가 GUI thread 동기 차단 없음 검증
- `tests/test_vib_log_gui_error_cmd.py` — stdin batched JSON 입력 → `error_log.py record_gui_error` 호출 → JSONL 적재 round-trip 및 마스킹 검증
- Rust 측: `lib.rs` 의 buffer + flush 로직 단위 테스트 — burst (1000건/초) 입력 시 GUI thread 가 블록되지 않고 background flush 가 batched subprocess 1~수회로 정리됨 검증

### Phase 3 — `vib report-bug` 커맨드 (Tier 2)

**새 파일**:
- `vibelign/commands/vib_report_bug_cmd.py`
- `.github/ISSUE_TEMPLATE/bug_report.md`

**수정 파일**:
- `vibelign/cli/cli_command_groups.py` — `report-bug` 서브커맨드 등록 (memory_cmd 와 같은 패턴)
- `vibelign/cli/cli_completion.py` — 자동완성 추가

**테스트**:
- `tests/test_vib_report_bug_cmd.py` — 번들 생성 / 마스킹 / 동의 흐름

### Phase 4 — GUI Bug Report 버튼 (Tier 2 GUI 측)

**수정 파일**:
- `vibelign-gui/src/pages/Settings.tsx` 또는 새 About 섹션 — "버그 리포트 만들기" 버튼
- `vibelign-gui/src-tauri/src/lib.rs` — `vib report-bug` invoke wrapping

### Phase 5 — Doctor 통합 + 문서화

**수정 파일**:
- `vibelign/commands/doctor_cmd.py` — `vib doctor` 출력에 "지난 7일 에러 N건 적재됨" 한 줄 추가
- `vibelign/commands/vib_manual_cmd.py` — `vib manual error-reporting` 항목 추가

## 6. Out of Scope (의도적 보류)

이번 사이클에서 **하지 않음**:

- Sentry/PostHog 등 SaaS 통합 (Tier 3 — 별도 스펙)
- 자동 백그라운드 업로드
- 사용 통계(usage telemetry) — 본 정책은 *에러* 만 다룬다
- 에러 통계 대시보드 / 리더보드
- 사용자별 식별자(user_id) 부여 — 의도적으로 anonymous

## 7. Acceptance Criteria

Phase 1+2 완료 시점에 다음이 참:

- [ ] CLI 에서 임의 unhandled exception 발생 시 `.vibelign/logs/cli-error-*.jsonl` 에 마스킹된 라인 기록
- [ ] GUI 에서 throw new Error("test") 시 `.vibelign/logs/gui-error-*.jsonl` 기록
- [ ] 의도적으로 시크릿 문자열이 포함된 에러 발생 시 디스크 파일에 raw 시크릿이 등장하지 않음 (테스트 검증)
- [ ] traceback/stack 의 프레임·라인 경계가 유지되고, `/Users/...`, private IP, internal host, token/password 인자가 raw 로 남지 않음
- [ ] `.vibelign/config.yaml` 의 nested `error_reporting.local_log: false` 설정 시 적재 0
- [ ] error log writer 자체가 실패해도 원래 CLI exception 출력/exit 흐름을 방해하지 않음
- [ ] GUI reporter 내부 에러가 재귀 보고 루프를 만들지 않음
- [ ] error-reporting Tier 1/2 코드 경로에서는 외부 네트워크 호출 0 (`error_log.py`, `vib_log_gui_error_cmd.py`, `vib_report_bug_cmd.py`, Tauri reporter 경로 한정 grep/코드리뷰 검증)
- [ ] `log-gui-error` 내부용 커맨드는 help/completion/README 명령 목록에 노출되지 않음 (필요 시 `_log-gui-error` prefix 사용)
- [ ] `vib checkpoint` 후 백업 스냅샷 결과에 `.vibelign/logs/*.jsonl` 또는 `.vibelign/reports/*.md` 파일이 등장하지 않음 (Phase 1.5 Backup exclusion 검증)
- [ ] GUI 에서 1000건/초 에러 burst 발생 시에도 GUI thread frame time 이 평소 대비 의미있게 증가하지 않음 (§3.1 GUI buffer + async flush 검증). 측정: 에러 push 가 동기 마이크로초 단위, flush subprocess 가 background async task 에서만 실행되는지 코드 inspection + 부하 시나리오 측정.
- [ ] Bug report 번들 파일명에 `:`, `*`, `?`, `"`, `<`, `>`, `|` 등 Windows NTFS 금지 문자가 포함되지 않음 (§3.1 Filename-safe timestamp 검증). 측정: `vib report-bug` 실행 후 생성된 파일명을 정규식으로 검사.
- [ ] CLI 와 별도 프로세스 (예: GUI flush subprocess, MCP server) 가 같은 `cli-error-*.jsonl` 또는 `gui-error-*.jsonl` 에 동시 write 를 시도해도 라인 손상/뒤섞임이 없음 (§3.1 Atomic append + Lock helper 검증). 측정: 두 프로세스에서 100건씩 동시 write 후 JSONL 파서로 무손실 검증.
- [ ] 한국어 에러 메시지("API 키가 없습니다" 등) 가 적재 후 `\uHHHH` 이스케이프 형태가 아닌 raw UTF-8 로 저장됨 (§3.1 UTF-8 round-trip 검증). 측정: 한글 메시지 발생 → 파일 hex/raw inspection 으로 한글 바이트 직접 확인 + 마스킹 정규식이 한글 본문 내 시크릿도 정상 매칭 검증.

Phase 3 완료 시점에 추가로:

- [ ] `vib report-bug` 가 동의 프롬프트 + 마크다운 번들 + GitHub URL 출력
- [ ] 번들에 raw 시크릿 0 (재마스킹 패스)
- [ ] `vib report-bug --last 0` 같은 엣지 케이스 안전

## 8. Risks & Mitigations

| 리스크 | 완화 |
|---|---|
| 마스킹 누락으로 시크릿 디스크 노출 | `redact_memory_text` 단일 진입점 강제, 적재 직전 마지막 redact 호출 의무화 + 회귀 테스트 |
| 로그 파일이 무한 증식 | 파일당 1000 라인 / 30 일 회전 / 일자 단위 분리 |
| Tauri 측 에러 reporter 가 무한 루프 (reporter 자체에서 에러) | reporter 함수는 try/catch 로 감싸고 실패 시 silent drop, 자기 자신을 다시 reporter 로 보내지 않음 |
| `vib report-bug` 가 큰 로그 첨부로 GitHub URL 길이 초과 | URL 에는 요약만 + 풀 본문은 파일 경로만 안내 |
| 사용자가 logs/reports 를 git 에 커밋 | `.vibelign/logs/`, `.vibelign/reports/` 는 .gitignore 기본 패턴에 추가 (init 시 자동) |
| GUI 에러 burst 가 main thread 를 freeze | 메모리 버퍼 + `tokio::spawn` background flush — push 마이크로초, subprocess 는 async (§3.1 GUI buffer + async flush) |
| Windows 에서 background subprocess spawn 시 콘솔 깜빡임 | `WINDOWS_SUBPROCESS_FLAGS = CREATE_NO_WINDOW` 재사용. Phase 2 의 5초 주기 flush 가 누락 시 burst 시 콘솔 반복 깜빡 (§3.1 Tauri subprocess on Windows) |
| GUI buffer 가 OOM 으로 자라남 (flush 반복 실패) | 1000건 cap + 가장 오래된 항목 drop. in-memory 버퍼 한정 — 디스크 회전의 "데이터 drop 금지" 와 별개 (§3.1 GUI buffer + async flush) |
| Tauri 프로세스 종료 시 unflushed buffer 손실 | Best-effort only 와 정합 — 의도적으로 수용. 사용자가 GUI 종료 시 `vib report-bug` 결과에 마지막 ~5초 GUI 에러가 빠질 수 있다는 점만 한계로 명시 |
| 백업 스냅샷에 logs/reports 가 들어가 DB 비대화 | `vibelign-core/src/backup/snapshot.rs` 의 prefix-skip 블록에 `.vibelign/logs/`, `.vibelign/reports/` 추가 (§3.1 Backup exclusion). Phase 1 + Phase 1.5 동일 릴리즈 버전 묶음 |
