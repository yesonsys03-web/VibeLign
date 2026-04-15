# VibeLign 온보딩 Claude Code 설치/제거 스펙

> **Status:** final implementation contract. This spec is intended to drive implementation after Phase 0 real-machine confirmations are completed.

## 문제

Claude Code 자체는 강력하지만, 비개발자에게는 설치 시작 단계가 가장 큰 진입 장벽이다.

- Windows에서는 PowerShell / CMD / WSL 차이를 이해해야 한다.
- Native Windows는 Git for Windows가 필요하다.
- PATH 반영은 셸마다 다르게 보인다.
- 로그인은 브라우저 인증을 거쳐야 하고, 성공 여부를 초보자가 스스로 판단하기 어렵다.
- 문제가 생겼을 때 “처음 상태로 되돌리는 방법”이 없으면 신뢰를 잃는다.

이 기능의 목표는 별도 Claude 전용 설치 앱을 만드는 것이 아니라, **VibeLign 첫 실행 온보딩 안에서 Claude Code 공식 설치를 우선 자동으로 시도하고, 실패하면 원인을 진단해 사용자를 다음 성공 경로로 안전하게 안내하는 것**이다.

---

## Source of Truth

이 기능의 설치/제거/요구 사항 기준은 Claude Code 공식 문서와 그 문서에서 공식적으로 안내하는 제거 절차만 사용한다.

- Official setup/removal docs: `https://code.claude.com/docs/en/setup`

문서에서 현재 확인된 사실:

- Native install commands
  - macOS / Linux / WSL: `curl -fsSL https://claude.ai/install.sh | bash`
  - Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`
  - Windows CMD: `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd`
- Requirements
  - macOS 13.0+
  - Windows 10 1809+ / Windows Server 2019+
  - 4GB+ RAM
  - x64 / ARM64
- Native Windows requires Git for Windows. WSL does not.
- Verification commands documented in setup page:
  - `claude --version`
  - `claude doctor`
- Official uninstall page documents **removal steps**, not a guaranteed dedicated `--uninstall` flag.
- Phase 0 real-machine evidence additionally showed that on Windows the official PowerShell installer may print success even when no runnable `claude` binary is produced, and may fail during native build install with Bun out-of-memory while still printing a success footer. Therefore installer stdout alone is never a success signal.

---

## Product Goal

VibeLign은 온보딩 단계에서 아래를 책임진다.

1. 공식 설치 경로 자동 시도
2. 대표 셸에서 실제 실행 가능 여부 검증
3. 로그인 및 첫 대화 시작 가능 상태 확인
4. 실패 시 초보자용 복구·우회 경로 제시
5. 필요 시 깨끗한 uninstall / cleanup 제공

온보딩 성공의 정의는 파일 설치가 아니다.

> **성공 = 사용자가 대표 셸에서 `claude`를 실행했고, 로그인 후 실제 대화 시작 가능 상태에 도달했거나, VibeLign 안내를 따라 다음 성공 경로로 무리 없이 넘어갈 수 있는 상태에 도달한 것**

---

## v1 Scope

### In scope (v1 core)

- VibeLign 온보딩 안에서 Claude Code 공식 native install 자동 시도
- Windows Native **CMD / PowerShell** 에서 `claude` 실행 보장
- macOS **bash / zsh** 에서 `claude` 실행 보장
- 브라우저 로그인 유도 및 성공 확인
- 설치 실패 시 cleanup / retry / guided fallback
- 사용자 요청 시 uninstall / reset flow
- Windows installer false-success detection and recovery UX

### Conditional (v1 WSL track — separate success metric)

- WSL이 **이미 설치·활성화된 환경에 한해** WSL install script 실행/검증 제공
- WSL 성공률은 v1 core 지표와 **분리 집계**
- WSL 미설치 환경에서는 자동 활성화(`wsl --install`)를 시도하지 않고 Microsoft 공식 안내 링크만 제공

### Out of scope

- WSL 자동 활성화·배포판 자동 설치 (v1.1)
- Claude Code 기능 재구현
- 자체 채팅 UI로 Claude Code 대체
- npm 설치 경로 사용
- Homebrew / WinGet을 v1 기본 설치 경로로 채택
- VS Code 통합 터미널 / Git Bash 완전 보장
- 모든 기업 보안 환경 100% 자동화

---

## Phase 0 Gate (Implementation Blocker)

**Phase 0가 끝나기 전에는 구현 시작 금지.**

실기기로 아래 3개를 확인해야 한다.

### Gate A — Official removal path

확인할 것:

- 공식 uninstall 명령이 실제로 존재하는지
- 없다면 공식 setup 문서의 수동 삭제 절차가 최신 기준으로 무엇인지
- 플랫폼별 제거 대상이 무엇인지

Phase 0 산출물:

- macOS / Linux / WSL 제거 명령 확정
- Windows 제거 명령 확정
- "전용 uninstall command 있음/없음" 판정
- **분기 규칙 문서화**: 전용 uninstall command 가 **있으면** → 1차 경로로 사용 + 위 Removal targets 표를 보조 cleanup 으로 실행. **없으면** → 공식 setup 문서 수동 절차를 GUI uninstall flow 로 래핑 + Removal targets 표 실행. 두 경우 모두 결과는 `docs/superpowers/specs/phase0-evidence.md` 에 기록

### Gate B — Login success verification path

확인할 것:

- `claude --print`, `claude --headless`, `claude auth status` 같은 공식 비상호작용 성공 판정 명령이 실제로 지원되는지
- 공식 명령이 없다면 PTY 기반 REPL probe가 v1 성공 판정 경로로 가능한지

우선순위:

1. 공식 비상호작용 명령이 존재하면 그것을 1차 경로로 사용
2. 없으면 PTY 기반 probe를 사용

### Gate C — Credential storage naming

확인할 것:

- macOS Keychain 실제 저장 항목명
- Windows Credential Manager 실제 항목명
- Linux / WSL credential file 경로와 형식

이 값은 문서의 placeholder가 아니라 **실기기에서 확인된 값으로 고정**해야 한다.

### Required evidence format

Phase 0는 아래 매트릭스를 `docs/superpowers/specs/phase0-evidence.md` 에 남겨야 한다. 각 컬럼은 담당 Gate 의 산출물이다.

| Machine | OS | Shell | Install path (Gate —) | Removal path (Gate A) | Auth/status path (Gate B) | Credential store name (Gate C) | Result |
|---|---|---|---|---|---|---|---|

- **Gate A** → Removal path 컬럼 + 전용 uninstall command 유무 판정 + 분기 규칙
- **Gate B** → Auth/status path 컬럼 (공식 명령명 또는 "PTY probe")
- **Gate C** → Credential store name 컬럼 (macOS Keychain 항목명, Windows Credential Manager 항목명, Linux/WSL 파일 경로)
- **Install path** 는 공식 문서에 이미 명시된 값이므로 Gate 가 아닌 전 환경 공통 기록 항목

---

## Platform Contract

### Windows

v1 core 성공 계약:

- CMD에서 `claude` 실행 가능
- PowerShell에서 `claude` 실행 가능
- 위 2개는 **설치 스크립트 종료 메시지와 무관하게**, 새 셸에서 실제 명령 실행으로만 판정한다.

v1 conditional 성공 계약 (WSL 트랙 선택 시):

- WSL에서 `claude` 실행 가능

설치 경로:

- Native Windows install script: PowerShell / CMD
- WSL install script: WSL shell 내부에서 Linux 경로 사용 (사용자가 WSL 트랙 선택 시)

전제:

- Native Windows는 Git for Windows 필요
- WSL 트랙은 WSL이 이미 활성화되어 있어야 한다. 미활성화 환경에서 VibeLign 은 자동 활성화를 시도하지 않고 Microsoft 공식 안내만 제공한다.
- Native Windows install 은 메모리 부족/Bun crash/placeholder artifact 같은 실패 모드를 가질 수 있으므로, install child process의 stdout/stderr와 새 셸 실행 결과를 함께 확인하기 전에는 성공으로 간주하지 않는다.

해석:

> Windows v1 core 최소 구현 계약은 **CMD / PowerShell** 이다. WSL은 별도 트랙이며 성공률은 분리 집계한다.

### macOS

v1 성공 계약:

- bash에서 `claude` 실행 가능
- zsh에서 `claude` 실행 가능

설치 경로:

- `curl -fsSL https://claude.ai/install.sh | bash`

---

## Implementation Stack (normative)

이 섹션은 구현 계약이다. 구현자는 아래 결정을 임의로 변경할 수 없다.

### Process spawn

- 공식 install 스크립트 실행(특히 `irm | iex`, `curl | bash`, `-ExecutionPolicy Bypass` 와 같은 동적 pipe 조합)은 **Rust 백엔드의 `std::process::Command` / `tokio::process::Command` 를 통해 직접 spawn** 한다.
- `tauri-plugin-shell` 의 allowlist 는 정적 명령만 허용하므로 설치 실행 경로로 사용하지 않는다. shell 플러그인은 사용자가 버튼으로 여는 정적 명령(예: 터미널/브라우저 열기)에만 한정한다.
- 설치 완료 후 검증은 반드시 **새 셸 세션을 별도 spawn** 하여 수행한다 (현재 세션의 PATH 변경 미반영 회피).
- 설치 child process 가 `0` 종료 또는 성공 문자열을 출력해도, 새 셸 검증이 실패하면 설치 결과 상태는 반드시 `failed_verification` 으로 기록한다.

### PTY control (login success probe)

- PTY 가 필요한 단계(특히 로그인 성공 판정)는 **`portable-pty` crate** 를 사용해 Windows ConPTY / Unix pty 를 통일된 추상화로 제어한다.
- stdout 는 ANSI escape 제거 후 정규식/상태머신으로 파싱한다.

### Timeouts and retries (fixed)

- 설치 스크립트 child process 타임아웃: **5분**
- PTY 로그인 probe 타임아웃: **60초**
- PTY probe 재시도: 최대 **2회**, 재시도 간 **5초** 백오프
- 이 숫자는 구현자가 임의로 조정하지 않는다. 변경 시 스펙 개정 필요.

### IPC

- 프론트엔드 ↔ Rust 백엔드 통신은 Tauri command (`#[tauri::command]`) 로 구성한다.
- 설치/검증/로그인 진행 이벤트는 Tauri event system 으로 push 한다.

---

## Security Policy (normative)

### PowerShell ExecutionPolicy Bypass

- **무음 자동 적용 금지.** VibeLign 은 `-ExecutionPolicy Bypass` 를 사용자 동의 없이 적용하지 않는다.
- ExecutionPolicy 가 스크립트 실행을 차단하는 상황을 감지하면 다음 다이얼로그를 거친다:
  > "이 기기의 PowerShell 정책이 스크립트 실행을 막고 있어요. VibeLign 이 이번 설치 세션에 한해 Bypass 로 실행해도 될까요?"
- 사용자가 거부하면 CMD fallback 경로를 실행한다.
- Bypass 는 **설치 세션 범위**로만 적용하고 시스템 정책을 영구 변경하지 않는다.

### Credential handling

- Keychain / Credential Manager 항목은 uninstall 기본 동작에서 **유지**한다. 사용자가 명시적으로 체크한 경우에만 삭제한다.
- VibeLign 은 Claude Code 의 인증 토큰을 읽거나 복사하지 않는다.

### Telemetry

- 텔레메트리는 옵트인이며, 수집 이벤트·보존 기간·삭제 요청 창구를 옵트인 다이얼로그에서 명시한다.
- IP / 사용자명 / 홈 경로 / 도메인은 마스킹 후 전송한다.

---

## Install Flow Contract

1. 앱 실행 → 온보딩 진입
2. OS / 셸 / 선행 조건 진단
3. 공식 native install 실행
4. 새 셸 세션 spawn
5. 대표 셸별 `claude --version` / `claude doctor` 검증
6. 로그인 유도
7. 성공 판정
8. 다음 단계 안내

### Onboarding UX state model

구현은 아래 상태 이름을 그대로 사용하거나, 최소한 이 의미를 보존하는 1:1 상태 모델을 가져야 한다.

| State | 의미 | 사용자에게 보여줄 핵심 메시지 | 다음 액션 |
|---|---|---|---|
| `idle` | 아직 시작 전 | Claude Code 설치를 시작할 준비가 되었음 | 시작 |
| `diagnosing` | OS / shell / prerequisite 점검 중 | 기기 환경을 확인하는 중 | 대기 |
| `needs_git` | Windows native prerequisite 미충족 | Git for Windows가 필요함 | Git 설치 / 다시 확인 |
| `ready_to_install` | 자동 설치 시도 가능 | 공식 설치를 시작할 수 있음 | 자동 설치 시작 |
| `installing_native` | PowerShell 또는 CMD native install 실행 중 | Claude Code를 설치하는 중 | 대기 |
| `installing_wsl` | WSL 경로 설치 중 | WSL 안에서 Claude Code를 설치하는 중 | 대기 |
| `verifying_shells` | 새 셸에서 실행 검증 중 | 설치 후 실제 실행 가능 여부를 확인하는 중 | 대기 |
| `needs_cmd_fallback` | PowerShell 경로 실패, CMD fallback 권장 | PowerShell 경로가 실패해 CMD 경로로 전환이 필요함 | CMD로 다시 시도 |
| `needs_wsl_fallback` | Native Windows 경로 실패, WSL 경로 권장 | Windows native 대신 WSL 경로가 더 안전함 | WSL로 진행 |
| `needs_manual_step` | 자동 처리 불가, 사용자 개입 필요 | 자동 설치를 마무리하지 못했으므로 안내된 수동 단계를 진행해야 함 | 수동 단계 보기 |
| `login_required` | 설치/검증은 끝났고 로그인 필요 | 브라우저 로그인으로 마무리해야 함 | 로그인 시작 |
| `probing_login` | 로그인 성공 여부를 판정 중 | Claude Code가 실제로 대화 가능한 상태인지 확인하는 중 | 대기 |
| `success` | 사용 가능 상태 도달 | Claude Code를 지금 바로 사용할 수 있음 | Claude 실행 |
| `blocked` | 현재 장비/환경에서는 더 진행 불가 | 이 환경에서는 자동 진행이 막혀 있음 | 로그 공유 / 다른 경로 선택 |

### UX state transition rules

- `idle` → `diagnosing` → `ready_to_install` 이 기본 시작 흐름이다.
- Windows 에서 Git 미설치가 감지되면 `diagnosing` → `needs_git` 로 전환한다.
- install 시작 후에는 `installing_native` 또는 `installing_wsl` 로 전환한다.
- install child process 종료 후에는 항상 `verifying_shells` 로 전환한다. 성공 문자열만으로 `success` 로 가면 안 된다.
- PowerShell path 실패 후 CMD 가 여전히 유효 후보이면 `needs_cmd_fallback` 으로 전환한다.
- native Windows path 가 불안정하거나 prerequisite 상 불리하면 `needs_wsl_fallback` 으로 전환 가능하다.
- 자동 설치가 더 이상 의미 없고 사용자 개입이 필수이면 `needs_manual_step` 으로 전환한다.
- 검증 통과 후에는 `login_required` → `probing_login` → `success` 순서로 간다.
- fatal error, unrecoverable crash, unsupported environment 는 `blocked` 로 전환한다.

### Backend ↔ frontend payload contract

백엔드와 프론트엔드는 install / verify / login 단계에서 아래 구조를 공통 계약으로 사용한다.

#### 1. Snapshot payload

Tauri command 응답과 화면 초기 복원에는 아래 snapshot 구조를 사용한다.

```ts
type OnboardingState =
  | 'idle'
  | 'diagnosing'
  | 'needs_git'
  | 'ready_to_install'
  | 'installing_native'
  | 'installing_wsl'
  | 'verifying_shells'
  | 'needs_cmd_fallback'
  | 'needs_wsl_fallback'
  | 'needs_manual_step'
  | 'login_required'
  | 'probing_login'
  | 'success'
  | 'blocked';

type NextAction =
  | 'start_install'
  | 'install_git'
  | 'retry'
  | 'retry_with_cmd'
  | 'continue_with_wsl'
  | 'open_manual_steps'
  | 'start_login'
  | 'launch_claude'
  | 'share_logs'
  | 'none';

interface OnboardingSnapshot {
  state: OnboardingState;
  os: 'macos' | 'windows' | 'linux';
  installPathKind: 'native-powershell' | 'native-cmd' | 'wsl' | 'manual' | 'unknown';
  shellTargets: string[];
  nextAction: NextAction;
  headline: string;
  detail?: string;
  primaryButtonLabel?: string;
  logsAvailable: boolean;
  diagnostics: {
    gitInstalled?: boolean;
    wslAvailable?: boolean;
    claudeOnPath?: boolean;
    claudeVersionOk?: boolean;
    claudeDoctorOk?: boolean;
    loginStatusKnown?: boolean;
  };
  lastError?: {
    code:
      | 'missing_git'
      | 'exec_policy_blocked'
      | 'installer_false_success'
      | 'installer_oom'
      | 'placeholder_artifact'
      | 'command_not_found'
      | 'login_probe_failed'
      | 'unsupported_environment'
      | 'unknown';
    summary: string;
    detail?: string;
    suggestedAction?: NextAction;
  };
}
```

#### 2. Progress event payload

장시간 실행 단계에서는 Tauri event payload 로 아래 progress 구조를 push 한다.

```ts
interface OnboardingProgressEvent {
  phase: 'diagnose' | 'install' | 'verify' | 'login';
  state: OnboardingState;
  stepId:
    | 'check_os'
    | 'check_git'
    | 'run_powershell_installer'
    | 'run_cmd_installer'
    | 'run_wsl_installer'
    | 'verify_version'
    | 'verify_doctor'
    | 'probe_login'
    | 'complete';
  status: 'started' | 'stream' | 'succeeded' | 'failed';
  message: string;
  streamChunk?: string;
  shellTarget?: string;
  observedPath?: string;
  errorCode?: OnboardingSnapshot['lastError']['code'];
}
```

#### 3. Command surface

최소 v1 command surface 는 아래를 포함해야 한다.

- `get_onboarding_snapshot() -> OnboardingSnapshot`
- `start_native_install(pathKind: 'native-powershell' | 'native-cmd') -> OnboardingSnapshot`
- `start_wsl_install() -> OnboardingSnapshot`
- `retry_verification() -> OnboardingSnapshot`
- `start_login_probe() -> OnboardingSnapshot`
- `get_onboarding_logs() -> { text: string }`

#### 4. Contract rules

- command 응답은 항상 최신 `OnboardingSnapshot` 을 반환한다.
- event 는 상태 변화를 설명하는 보조 채널이고, source of truth 는 최신 snapshot 이다.
- `headline`, `detail`, `primaryButtonLabel`, `nextAction` 은 백엔드에서 채워 프론트가 ad hoc 문구를 만들지 않게 한다.
- `lastError.code` 는 analytics / QA / retry logic 의 기준 키로 사용한다.
- 하나의 snapshot 은 하나의 `nextAction` 만 가진다. 여러 버튼이 필요하면 secondary action 으로 별도 UI 정책에서 다루고, 계약상 primary action 은 하나만 가진다.

### Install success rule

다음 조건을 모두 만족할 때만 설치 성공으로 본다.

1. install child process 가 비정상 종료하지 않을 것
2. install stdout/stderr 에 치명적 오류가 없을 것
3. 새 셸에서 `claude --version` 이 성공할 것
4. 필요 경로/산출물이 비정상 placeholder 상태가 아닐 것

다음은 모두 **실패**로 분류한다.

- 설치 스크립트가 성공 문자열을 출력했지만 `claude` 가 실행되지 않음
- 설치 스크립트가 성공 문자열을 출력했지만 출력 로그에 OOM / crash / fatal error 가 존재함
- `claude` 가 0-byte 파일이나 비실행 artifact 로 남음

### Native Windows install order

1. PowerShell 경로 우선 시도
2. ExecutionPolicy / AMSI / 보안 제품 차단 시 CMD fallback
3. WSL 경로는 사용자가 WSL 트랙을 선택한 경우에만 별도 실행
4. 각 경로 후 새 셸에서 `claude --version` 검증 실패 시 install success 로 승급하지 않는다

### WSL contract (conditional track)

WSL은 v1 core 가 아닌 **선택 트랙**이다.

- WSL이 이미 활성화된 경우: 사용자가 WSL 트랙을 선택하면 온보딩 내에서 설치/검증 진행
- WSL이 미설치/비활성화인 경우: Microsoft 공식 활성화 안내 링크만 제공. VibeLign 이 `wsl --install` 을 자동 실행하지 않는다
- WSL 트랙 실패는 v1 core 성공률 지표에 포함되지 않는다

---

## Success Criteria

### v1 core technical success

- Windows Native **CMD / PowerShell** 에서 `claude --version` 성공, 또는 실패 원인이 구조화되어 다음 경로(CMD fallback / 수동 진행)로 안전하게 전환 가능
- macOS **bash / zsh** 에서 `claude --version` 성공
- `claude doctor` 성공
- 로그인 후 첫 응답 시작 가능
- 설치 스크립트 로그에 fatal crash/OOM 가 남지 않음, 또는 남았더라도 새 셸 검증이 실제로 통과했음을 별도로 증명

### v1 conditional technical success (WSL 트랙)

- 사용자가 WSL 트랙을 선택하고 WSL이 이미 활성화된 경우에 한해 WSL에서 `claude --version` 성공
- WSL 성공률은 core 지표와 분리 집계

### v1 user success

- 사용자가 “설치됨”이 아니라 “지금 바로 쓸 수 있음 / 지금 무엇을 하면 되는지”를 이해할 수 있어야 한다
- 실패 시 사용자가 다음 행동을 버튼 하나로 선택할 수 있어야 한다

### Login success detection

우선순위는 아래와 같다.

1. 공식 비상호작용 상태 확인 명령이 있으면 사용
2. 없으면 PTY 기반 probe 사용

PTY probe 성공 정의:

- `claude` 기동
- 프롬프트 감지
- 테스트 메시지 1회 전송
- 첫 응답 토큰 수신

실패 분류:

- PTY 기동 실패
- 로그인 프롬프트에서 멈춤
- 로그인 후 응답 없음
- 계정 권한 부족

---

## Error Handling Contract

실패는 에러 코드만 보여주지 않는다. 항상 다음 행동을 함께 제시한다.

### State-driven error presentation

- 모든 install/auth failure 는 단순 문자열이 아니라 위 UX state model 의 상태 전환으로 표현한다.
- 하나의 상태는 하나의 주 행동(primary action)만 가져야 한다.
- 상태가 `needs_git`, `needs_cmd_fallback`, `needs_wsl_fallback`, `needs_manual_step`, `blocked` 중 하나라면 사용자는 다음 행동을 버튼 하나로 이해할 수 있어야 한다.
- `blocked` 는 “왜 막혔는지 + 무엇을 해야 다시 진행 가능한지”를 함께 보여줘야 한다.

### Install / environment failures

- 인터넷 실패 → 재시도 / 수동 설치 링크
- PowerShell 정책 차단 → 이번 세션만 Bypass 허용 (사용자 확인 필수) / CMD fallback
- AMSI / Defender / 보안 제품 차단 → 수동 설치 링크 + 허용 URL 목록 클립보드 복사
- WSL 미활성화 → Microsoft 공식 활성화 안내 링크 / 설정 후 다시 시도
- Git for Windows 미설치 → 공식 다운로드 링크 / 설치 후 다시 시도
- 설치 스크립트 false-success (`✅ Installation complete!` but no runnable `claude`) → 설치 실패로 분류, artifact 경로 표시, 재설치/CMD fallback/로그 공유 제안
- native build OOM/crash → 설치 실패로 분류, VM/메모리 부족 가능성 안내, 더 큰 장비 또는 다른 Windows 환경에서 재시도 제안

### Login probe failures (4 categories, each with required next action)

각 실패는 Success Criteria 의 4분류 각각과 1:1 로 대응한다. 구현자는 네 분기를 모두 구현해야 한다.

| 실패 분류 | 감지 신호 | 다음 행동 (계약) |
|---|---|---|
| (a) PTY 기동 실패 | `claude` 프로세스 spawn 자체 실패 / ConPTY/pty 초기화 에러 | 설치 검증 단계로 되돌아가 `claude --version` 재확인 → 실패 시 재설치 제안 / 로그 공유 버튼 |
| (b) 로그인 프롬프트에서 멈춤 | 60초 내 브라우저 콜백 미수신 | 로그인 URL 클립보드 복사 + 화면 표시 / 브라우저 수동 열기 / 프록시 감지 결과 안내 |
| (c) 로그인 후 응답 없음 | 로그인 후 첫 응답 토큰 60초 내 미수신 | PTY probe 재시도 (최대 2회, 5초 백오프) / 네트워크·프록시 재점검 안내 / 수동 `claude` 실행으로 전환 |
| (d) 계정 권한 부족 | 응답 스트림에서 권한 부족 메시지 패턴 감지 | Pro / Max / Team / Enterprise 요금제 안내 링크 / 다른 계정으로 재로그인 버튼 |

---

## Uninstall / Cleanup Contract

### Principle

VibeLign은 **공식 제거 경로**를 기준으로 uninstall을 제공한다.

- 공식 uninstall 명령이 있으면 1차 경로로 사용
- 없으면 공식 setup 문서의 수동 삭제 절차를 GUI uninstall flow로 감싼다
- 제거 후에도 잔여 항목이 있으면 보조 cleanup 수행

### Removal policy

언인스톨 정책은 두 모드로 분리한다.

1. **전체 제거**
   - 공식 제거 경로를 기준으로 Claude Code 본체와 공식 데이터 경로를 제거한다.
   - 그 다음 VibeLign이 추가한 항목(PATH, marker block, shortcut, onboarding state, shim)을 정리한다.
2. **VibeLign 추가분만 제거**
   - Claude Code 본체, 공식 데이터 경로, 로그인 상태는 유지한다.
   - VibeLign이 직접 추가한 항목만 제거한다.

즉 “VibeLign은 자신이 직접 추가한 항목만 제거한다”는 원칙은 **부분 제거 모드**에 적용되고,
전체 제거 모드에서는 **공식 제거 경로 + VibeLign 추가분 정리**를 함께 수행한다.

VibeLign이 직접 추가한 항목의 범위는 아래와 같다.

- rc file marker block
- PATH entry (VibeLign이 추가한 경우만)
- shortcut / launcher
- onboarding state
- VibeLign-managed shim

### Removal targets

아래는 **Phase 0 확정 전 placeholder**가 아니라, 확인 후 고정되어야 하는 계약 항목이다.

| Category | macOS / Linux / WSL | Windows |
|---|---|---|
| Binary | `~/.local/bin/claude` | `%USERPROFILE%\.local\bin\claude.exe` |
| Native data | `~/.local/share/claude` (Phase 0 확인 필요) | `%USERPROFILE%\.local\share\claude` (Phase 0 확인 필요) |
| User config/state | `~/.claude`, `~/.claude.json` | `%USERPROFILE%\.claude`, `%USERPROFILE%\.claude.json` |
| Project config | `.claude`, `.mcp.json` | `.claude`, `.mcp.json` |
| Shell rc marker block | `.zshrc` / `.bashrc` / `.bash_profile` / `.profile` 의 `# >>> vibelign >>>` ~ `# <<< vibelign <<<` 블록 | — |
| User PATH entry | — | 사용자 PATH 환경변수의 `%USERPROFILE%\.local\bin` (VibeLign 이 추가한 경우만) |
| VibeLign shim / shortcut | `~/Applications/VibeLign-Claude.command`, 바탕화면 `.command` | `%USERPROFILE%\Desktop\Claude Code.lnk`, Start Menu 바로가기 |
| VibeLign onboarding state | `~/Library/Application Support/VibeLign/onboarding.json` | `%APPDATA%\VibeLign\onboarding.json` |
| Credential store | Phase 0 Gate C real-machine confirmation required (결과는 `docs/superpowers/specs/phase0-evidence.md` 에 고정) | Phase 0 Gate C real-machine confirmation required (결과는 `docs/superpowers/specs/phase0-evidence.md` 에 고정) |

**Native data / Credential store 항목은 Phase 0 Gate C 산출물로 고정된 뒤에만 구현 대상이 된다.**

### UX contract

언인스톨은 최소 3단계 선택지를 제공한다.

1. **전체 제거**
2. **VibeLign 추가분만 제거** (Claude Code 본체/로그인 유지)
3. **취소**

옵션별 의미는 아래와 같다.

- **전체 제거**: Claude Code 본체 + 공식 데이터 경로 + VibeLign 추가분 제거. credential store는 기본 유지, 사용자가 명시적으로 체크한 경우에만 삭제.
- **VibeLign 추가분만 제거**: Claude Code 본체 / 공식 데이터 경로 / 로그인 상태는 유지하고, VibeLign이 추가한 PATH/marker/shortcut/onboarding state/shim만 제거.
- **취소**: 아무 것도 변경하지 않음.

실행 전 반드시 보여줄 것:

- 삭제 대상
- 유지 대상
- 재로그인 필요 여부

---

## Cross-Platform Constraints

- raw shell differences를 UI에서 노출하지 않는다
- PATH 반영은 새 셸 세션에서 검증한다
- Windows PowerShell / CMD / WSL, macOS bash / zsh를 각각 독립적으로 확인한다
- 로그는 로컬 저장하고, 공유는 opt-in이어야 한다

---

## Metrics

v1에서 추적해야 할 지표:

- 설치 시작 대비 완료율 (v1 core / WSL 트랙 **분리 집계**)
- 대표 셸별 성공률 (Windows CMD / PowerShell / macOS bash / zsh / WSL[conditional])
- 로그인 완료율
- 첫 대화 시작 성공률
- uninstall **실행률 및 성공률** (성공률 = 선택한 삭제 대상이 실제로 제거된 비율)
- uninstall 직후 재설치 전환율 (품질 프록시 지표)
- 실패 유형별 비율: 네트워크 / PowerShell 정책 / AMSI·보안 제품 / PATH / 로그인 분류 a~d / WSL 활성화 / 권한 부족

---

## Implementation Order (normative)

이 기능은 "설치 버튼" 보다 **성공 판정과 복구 흐름**이 더 중요하다. 구현자는 아래 순서를 따른다.

1. Phase 0 실기기 확인 (Gate A/B/C 전부 통과 + `phase0-evidence.md` 기록)
2. Native install + 대표 셸 검증 (v1 core: Windows CMD/PowerShell, macOS bash/zsh)
3. 로그인 성공 판정 (공식 비상호작용 명령 있으면 1차, 없으면 PTY probe)
4. cleanup / uninstall (Removal targets 표 전체)
5. WSL 조건부 트랙 (v1 core 가 안정화된 이후)
6. 후속 셸 최적화 (v1.1)

v1의 본질:

> **공식 설치를 VibeLign 안에서 안전하게 실행하고, 대표 셸에서 바로 쓸 수 있게 만들고, 꼬였을 때 깨끗하게 되돌릴 수 있게 하는 것.**
