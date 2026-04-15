# VibeLign 온보딩 내 Claude Code 자동 설치 기획안

*작성일: 2026-04-13 | 최종 수정: 2026-04-15 (Anthropic 공식 native install 스크립트 기준으로 재정렬)*
*목적: 별도 인스톨러를 제공하는 것이 아니라, VibeLign 첫 실행 온보딩 화면 안에서 Claude Code **공식 native install 스크립트**를 자동 실행하고, 코알못 사용자가 Windows/macOS에서 설치 직후 바로 `claude`를 실행하게 만드는 통합 온보딩 플로우를 설계한다.*

> **공식 설치 경로 (Source of Truth):** [https://code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup)
>
> 이 문서의 모든 설치 명령·요구 사항·검증 명령은 위 공식 페이지를 단일 출처로 한다. 페이지가 변경되면 본 기획안도 함께 갱신한다.
>
> **공식 native 설치 명령 (Recommended channel):**
>
> | 플랫폼 | 명령 |
> |--------|------|
> | macOS / Linux / WSL | `curl -fsSL https://claude.ai/install.sh \| bash` |
> | Windows PowerShell | `irm https://claude.ai/install.ps1 \| iex` |
> | Windows CMD | `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd` |
>
> **요구 사항:** macOS 13.0+, Windows 10 1809+ (Native Windows 는 Git for Windows 필요, WSL 은 불필요), 4GB+ RAM, x64/ARM64.
> **설치 위치:** `~/.local/bin/claude` (mac/linux/wsl), `%USERPROFILE%\.local\bin\claude.exe` (Windows).
> **검증 명령:** `claude --version`, `claude doctor`.
> **로그인 명령:** `claude` 실행 시 브라우저 prompt. 별도 비상호작용 `claude auth status` 명령은 공식 setup 문서에 노출되어 있지 않으며, 로그인 완료 검증은 실제 `claude` 세션 기동으로만 확인할 수 있다.
> **대체 채널:** Homebrew (mac, 자동 업데이트 없음), WinGet (Win, 자동 업데이트 없음). VibeLign v1은 native 채널만 사용한다.
> **npm 설치는 deprecated.** v1에서는 fallback 으로도 사용하지 않는다.

---

## 1. 문제 정의

### 코알못이 바이브코딩에 진입하지 못하는 가장 큰 이유 = 초기 설치

현재 Claude Code 사용을 시작하려면 다음 단계를 이해하거나 통과해야 함:
- 공식 설치 방식 선택 (Native Windows / WSL / macOS)
- Windows라면 Git for Windows 필요 여부 이해
- 설치 스크립트/PowerShell/CMD 차이 이해
- 환경변수 PATH 반영 여부 확인
- `claude --version`, `claude doctor`, `claude`로 설치 검증
- 로그인 흐름(브라우저 인증) 완료

이 중 한 단계만 막혀도 코알못은 "역시 나는 안 되는구나" 하고 떠난다. 실제 사용은 어렵지 않은데 **시작이 어려워서 진입조차 못 하는 사용자가 다수**.

### 타겟 사용자
- 개발자가 아닌 일반인 (디자이너, 기획자, 학생, 자영업자 등)
- 윈도 사용자 비중이 높음
- Claude Pro/Max 구독자 또는 잠재 구독자

### 비즈니스 임팩트
원클릭 설치 경험이 VibeLign의 **킬러 차별점**이 될 수 있음. Claude Code 자체는 개발자 도구라 진입이 어렵지만, VibeLign이 **첫 실행 온보딩 안에서 Claude Code 공식 설치를 코알못도 실패 없이 통과하게 도와주는 친화적 진입 레이어**가 되면 시장이 완전히 달라짐.

### 제품 목표
- Claude Code 자체 설치는 **공식 setup 문서 기준**으로 유지한다.
- VibeLign은 **첫 실행 온보딩 화면 안에서 공식 설치 실행 + 멀티 셸 환경 설정 + 설치 검증 + 첫 실행 안내**를 제공한다.
- VibeLign은 문제가 생겼을 때 **설치 중단 / 부분 설치 정리 / 언인스톨(깨끗한 제거)** 경로도 함께 제공한다.
- 이 기능은 **별도 설치 앱/별도 인스톨러**가 아니라 VibeLign 제품 내부 온보딩의 한 단계로 제공한다.
- 온보딩 성공의 기준은 파일이 깔린 상태가 아니라, **Windows에서는 CMD / PowerShell / WSL, macOS에서는 bash / zsh에서 사용자가 `claude`만 입력하면 바로 실행되는 상태**다.

### 우선순위

**v1 필수**
- Claude Code 공식 설치 실행 (Windows Native / macOS)
- Windows(CMD / PowerShell / WSL)에서 `claude` 실행 보장
- macOS bash / zsh에서 `claude` 실행 보장
- 로그인 완료 및 첫 대화 시작 검증 (PTY 기반 REPL 응답 감지)
- 설치 실패 또는 사용자 요청 시 **Claude Code 관련 설정/경로를 안전하게 제거하는 언인스톨/정리 경로** 제공

**v1.1 확장**
- VS Code 통합 터미널 / Git Bash 등 후속 셸 최적화
- 고급 자동 복구 규칙 확대

**후순위**
- 통합 채팅 UI
- 설치 이후 지속 사용 UX 고도화

### 비목표
- Claude Code 자체 기능을 VibeLign 내부에 재구현하지 않는다.
- v1에서는 deprecated 된 npm 설치 경로를 사용하지 않는다 (공식 native install 스크립트만 사용).
- v1에서는 Homebrew / WinGet 분기를 자동 설치 경로로 제공하지 않는다 (auto-update 미지원이라 운영 부담만 증가).
- 첫 버전에서 독자 채팅 UI로 Claude Code를 대체하지 않는다.
- 모든 고급 개발자 셸 조합을 첫 출시에서 완벽 지원하는 것을 목표로 하지 않는다.

---

## 2. 범위 — VibeLign 내부 제공 방식

### 옵션 A — 온보딩 화면 내 자동 설치 (1차 출시 목표)

VibeLign이 **첫 실행 온보딩 화면 안에서** Claude Code 자동 설치를 제공하고, 설치가 끝나면 사용자는 평소처럼 터미널에서 `claude`를 실행한다. 단, 온보딩 종료 시점에 Windows에서는 **CMD / PowerShell / WSL**, macOS에서는 **bash / zsh**에서 모두 `claude`가 바로 실행되어야 함.

**흐름:**
1. 사용자가 VibeLign을 실행하면 온보딩 화면 진입
2. 온보딩에서 자동 환경 점검 → Claude Code **공식 설치 경로** 선택 및 실행
3. 설치 완료 → Windows는 CMD / PowerShell / WSL, macOS는 bash / zsh에서 `claude` 실행 가능하도록 자동 설정
4. 온보딩 안에서 로그인과 첫 실행까지 안내
5. 설치 완료 후 VibeLign이 다음 단계(예: 안전한 AI 작업 흐름, 설정, 가이드)로 연결

**장점:**
- 구현 단순, 빠른 출시 (예상 2~3주)
- 사용자가 익숙한 방식으로 Claude Code 사용 (터미널)
- 별도 Claude 전용 인스톨러를 만들지 않고 VibeLign 내부 경험으로 묶을 수 있음
- VibeLign이 가벼움
- 유지보수 부담 적음
- 옵션 B로 확장 시 코드 재활용 가능

### 옵션 B — 통합 모드 (장기)

VibeLign GUI 안에서 Claude Code CLI를 subprocess로 띄우고 출력 가공해서 보여주는 통합 채팅 UI 제공.

**장점:**
- 사용자가 터미널 자체를 안 봐도 됨
- VibeLign이 anchor meta, patch CodeSpeak 같은 자체 기능을 자연스럽게 보여줄 수 있음

**단점:**
- 구현 비용 큼 (채팅 UI, 도구 호출 시각화, 권한 다이얼로그 등)
- Claude Code CLI 업데이트 따라가야 함

### 권장: 옵션 A 먼저, 옵션 B는 사용자 반응 보고 결정

즉, 초기 목표는 **VibeLign 내부 온보딩에서 자동 설치와 첫 실행을 책임지는 것**이지, Claude Code용 별도 설치 전용 앱을 만드는 것이 아니다.

---

## 3. 인증 방식 — 구독자 우선

### 일반 사용자 (대다수)
- Claude Pro/Max 구독자 → **브라우저 로그인**
- 추가 비용 없음, 구독 한도 안에서 동작
- 온보딩 내 설치 완료 후 `claude` 실행 → 공식 로그인 흐름으로 연결

### 개발자 (소수)
- API 키 직접 입력
- "API 키 사용" 옵션은 고급 설정에 숨겨두고, 기본 화면에는 노출 안 함

### 가입 안 한 사용자
- "Claude 무료 체험으로 시작하기" 버튼으로 anthropic 가입 페이지 안내

### 로그인 흐름 실패 대응

온보딩 내 설치 완료 후 `claude` 실행 시 브라우저 기반 로그인이 필요한데, 이 단계에서 막히는 경우가 빈번할 수 있다.

| 실패 시나리오 | 대응 |
|-------------|------|
| 기본 브라우저가 안 열림 | 로그인 URL을 클립보드에 복사 + 화면에 표시, 수동 붙여넣기 안내 |
| 브라우저 열렸지만 콜백 실패 | 로컬 포트 충돌 감지 → 대체 포트 시도 또는 수동 토큰 입력 안내 |
| 회사 SSO/프록시로 인증 페이지 차단 | 프록시 감지 결과 표시 + "IT 담당자에게 이 URL 허용 요청" 안내 |
| 로그인 성공했지만 터미널에 반영 안 됨 | 자동 재시도 + 수동 `claude login` 명령 안내 |
| 로그인은 됐지만 Claude Code 사용 권한이 없는 계정 | 무료 플랜/권한 부족 상태를 감지해 Pro/Max/Team/Enterprise 필요 안내 |

**온보딩 "성공"의 정의**: `claude --version` 통과가 아니라, **로그인까지 완료되어 `claude`를 실행하면 대화가 시작되는 상태**를 성공으로 본다.

---

## 4. 플랫폼별 배포

### macOS
- **Claude Code 설치 방식**: 공식 native install 스크립트
  - `curl -fsSL https://claude.ai/install.sh | bash`
- **VibeLign Tauri 앱 자체의 배포 포맷**: `.dmg` (drag-to-Applications). `.pkg` 는 Gatekeeper 트리거 위험으로 v1 에서는 사용하지 않는다.
- **VibeLign 앱 공증/서명**: 초기엔 생략 검토하나, Notarization 부재 시 macOS 가 "Damaged" 로 처리하는 케이스가 있어 Apple Developer ID + Notarization 비용 ($99/년) 을 v1 출시 전 결정 항목으로 격상한다.
- **공증 없을 때 우회 (대안)**: 우클릭 → "열기" → 다시 한 번 "열기"
- **다운로드 페이지에 스크린샷 + 단계별 안내 필수**
- **설치 후 보장 상태**: Terminal.app / iTerm 등에서 bash / zsh 셸로 `claude` 실행 가능 (`~/.local/bin/claude`)

#### macOS 구현 메모

- 공식 `install.sh`를 기본 경로로 사용
- 설치 후 Terminal.app / iTerm 등에서 bash / zsh 셸 기준 `claude` 실행 보장

**환경 편차 대응:**

| 항목 | 대응 |
|------|------|
| Apple Silicon / Intel | `uname -m` 으로 아키텍처 감지. 공식 install.sh 가 아키텍처를 자동 처리하는지 Phase 0 에서 확인, 미지원 시 분기 |
| zsh / bash | `$SHELL` 감지 후 해당 rc 파일(`.zshrc` / `.bashrc` / `.bash_profile`)에 PATH 반영 여부 확인 |
| Homebrew 기존 설치 | `brew list --formula`에서 Claude Code 존재 여부 감지 → 유지/공식 경로 전환/재설치 선택 제공 |
| PATH 미반영 | rc 파일에 PATH가 없으면 사용자 확인 후 추가. 새 터미널 세션에서만 반영되는 점 안내 |
| 공증 미서명 우회 | `xattr -d com.apple.quarantine` 자동 실행 또는 우클릭 → 열기 단계별 스크린샷 안내 |
| 디스크 권한 / SIP | `/usr/local` 또는 `~/.local` 쓰기 권한 사전 점검. 실패 시 `sudo` 필요 여부 안내 |

### Windows
- **Claude Code 설치 방식**: 공식 native install 스크립트
  - PowerShell: `irm https://claude.ai/install.ps1 | iex`
  - CMD: `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd`
- **공식에는 .exe / .msi 형태의 Windows installer 가 존재하지 않는다.** VibeLign 도 자체 .exe installer 를 만들지 않고 위 스크립트를 그대로 실행한다.
- **전제 조건**:
  - Windows 10 1809+ / Windows 11 / Windows Server 2019+
  - Native Windows: Git for Windows 필수 (WSL 경로는 불필요)
  - PowerShell 경로 사용 시 ExecutionPolicy 가 `irm | iex` 실행을 허용해야 함 (제한 환경에서는 `-ExecutionPolicy Bypass` 로 감싸 spawn)
- **VibeLign Tauri 앱 자체의 Windows 배포 포맷**: Tauri 가 생성하는 `.exe` (NSIS) 또는 `.msi`. **이는 VibeLign 앱의 배포 포맷이며 Claude Code 설치 포맷이 아님을 분리해서 본다.**
- **서명**: VibeLign 앱 자체는 초기엔 미서명 → SmartScreen 경고 발생
- **우회**: "추가 정보" 클릭 → "실행" 버튼 노출
- **다운로드 횟수 누적되면 SmartScreen 경고 점차 감소**
- **스크립트 실행 단계의 보안 차단:** PowerShell ExecutionPolicy, AMSI, Windows Defender 실시간 검사가 `irm | iex` 자체를 차단할 수 있으므로 SmartScreen 보다 이쪽이 v1 의 주요 블로커가 된다.

### 향후 서명 추가 시점
- Apple Developer ($99/년) — 사용자 100명+ 시점
- Windows EV Code Signing ($300~) — 1000명+ 시점

### 빌드 도구
- **Tauri 사용 중** — 한 React 코드베이스로 Mac/Windows 양쪽 빌드
- `tauri build`로 VibeLign 앱 패키지를 두 OS에 배포
- `updater` 플러그인으로 자동 업데이트 구현 → 첫 설치만 어렵고 이후는 자동

#### Tauri 백엔드 아키텍처 메모

- **OS 명령 실행 경로 (확정)**: `tauri-plugin-shell` 의 allowlist 는 정적 명령만 허용하므로 `irm | iex`, `curl | bash`, `-ExecutionPolicy Bypass` 같은 동적 pipe 조합에는 부적합. v1 은 **Rust 백엔드에서 `std::process::Command` (또는 `tokio::process::Command`) 로 직접 spawn** 하고, shell 플러그인은 사용자가 버튼으로 여는 정적 명령(예: 터미널 열기)에만 한정한다. PTY 제어가 필요한 단계(로그인 REPL 감지)는 `portable-pty` crate (Windows ConPTY / Unix pty 추상화) 를 사이드카로 사용한다
- **ExecutionPolicy Bypass 정책**: 자동 Bypass 는 기업 EDR/AMSI 에서 의심 서명으로 탐지될 수 있어 **무음 자동 적용 금지**. 감지 후 사용자에게 "이 기기의 PowerShell 정책이 스크립트 실행을 막고 있어요. VibeLign 이 이번 설치 세션에 한해 Bypass 로 실행해도 될까요?" 확인 다이얼로그를 거친다. 기업 정책상 거부 시 CMD 경로로 fallback
- **UAC / 권한**: native install 스크립트가 사용자 영역(`%USERPROFILE%\.local\bin`, `~/.local/bin`)에 설치하므로 sudo/관리자 권한 불필요
- **프로세스 관리**: 설치 스크립트를 child process로 실행하고 stdout/stderr를 실시간 캡처하여 GUI 진행 상태에 반영. 타임아웃(5분) 설정으로 hung 프로세스 방지. 설치 완료 후 검증은 **새 셸 세션을 별도 spawn** 하여 수행 (현재 세션 PATH 변경 미반영)
- **에러 핸들링**: Rust 백엔드에서 `Result<T, E>` 기반 에러 체인 구성. 설치 단계별 에러를 구조화된 enum으로 분류하여 프론트엔드에 전달 → 사용자 친화적 메시지로 변환
- **IPC 구조**: Tauri command(`#[tauri::command]`)로 프론트엔드 ↔ 백엔드 통신. 설치 진행 이벤트는 Tauri event system으로 push

### 업데이트 전략

VibeLign 업데이트와 Claude Code 업데이트는 별개 채널이다. 둘이 충돌하지 않도록 명확히 분리한다.

| 항목 | VibeLign 자체 | Claude Code |
|------|-------------|-------------|
| 업데이트 주체 | Tauri updater 플러그인 | Claude Code 자체 업데이트 메커니즘 (`claude update`) |
| 트리거 | VibeLign 실행 시 자동 확인 | Claude Code 실행 시 자체 확인 |
| 사용자 알림 | VibeLign GUI 내 알림 | Claude Code CLI 자체 알림 |
| 충돌 방지 | VibeLign은 Claude Code 업데이트에 개입하지 않음. 업데이트 후 `claude --version` 재검증만 수행 |

- VibeLign 업데이트는 **앱 실행 시 백그라운드 확인 → 재시작 시 적용** 방식
- Claude Code 메이저 버전 변경 시 VibeLign 호환성 검증이 필요할 수 있으므로, VibeLign이 지원하는 Claude Code 최소/최대 버전 범위를 설정 파일로 관리
- Claude Code 버전이 변경되면 VibeLign은 다음 실행 시 설치 경로, 셸 실행, 로그인 가능 여부를 재검증

---

## 5. 구현 가능한 윈도 설치 흐름

이 기획의 핵심은 “무조건 모든 환경을 한 번에 완벽 지원”이 아니라, **사용자가 실제로 가장 많이 여는 대표 셸에서는 첫 버전부터 바로 `claude`를 실행하게 만들고, 그 밖의 고급/부가 셸은 단계적으로 최적화**하는 것이다.

### v1 범위 (필수)

1. VibeLign 실행 → 온보딩 화면 진입
2. 환경 점검
   - Windows 버전
   - Git for Windows 설치 여부
   - 기존 Claude Code 설치 여부
   - 인터넷 연결 / 디스크 공간
   - 프록시/VPN 환경 감지 (시스템 프록시 설정 읽기)
3. Claude Code **공식 native install 스크립트** 실행
   - 기본 경로: PowerShell 에서 `irm https://claude.ai/install.ps1 | iex` (필요 시 `-ExecutionPolicy Bypass` 로 spawn)
   - PowerShell 차단 환경 fallback: CMD 경로 (`curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd`)
   - WSL 경로도 v1 필수 범위에 포함. WSL이 미설치/미활성화 상태면 VibeLign이 설정 경로를 안내하고, 사용 가능 상태가 되면 WSL 안에서 `curl -fsSL https://claude.ai/install.sh | bash` 실행까지 이어간다.
4. 설치 후 검증
   - **새 셸 세션을 spawn 한 뒤** 검증 수행 (PATH 변경은 현재 세션에 자동 반영되지 않음)
   - PowerShell 새 세션에서 `claude --version`
   - CMD 새 세션에서 `claude --version`
   - WSL 새 세션에서 `claude --version`
   - `claude doctor`
   - Git Bash 경로 인식 확인 (필요 시 settings.json 의 `CLAUDE_CODE_GIT_BASH_PATH` 설정)
5. 로그인 검증
   - `claude` 실행 후 브라우저 로그인 유도
   - 로그인 완료 확인 (대화 세션 시작 가능 여부)
   - 실패 시 섹션 3 "로그인 흐름 실패 대응" 적용
6. 필요 시 바탕화면 바로가기 생성
7. 온보딩 완료 후 사용자가 클릭하면 감지된 기본 터미널에서 `claude` 실행

#### 바로가기 원칙

- 바로가기는 **셸을 열고 그 안에서 `claude`를 실행**하는 방식으로 제공
- 기본 터미널은 자동 선택하되, 사용자가 설정에서 바꿀 수 있게 함

#### 바로가기 실사용 시나리오 대응

| 시나리오 | 문제 | 대응 |
|---------|------|------|
| CMD에서 `claude` 실행 후 종료 시 창이 닫힘 | 사용자가 결과를 못 봄 | 바로가기에 `/K` 플래그 사용 (`cmd /K claude`) → 종료 후에도 창 유지 |
| PowerShell 실행 정책 제한 | 스크립트 실행 차단 | 바로가기에 `-ExecutionPolicy Bypass` 추가 또는 사전 점검에서 안내 |
| 터미널 인코딩 문제 | 한글/이모지 깨짐 | CMD는 `chcp 65001`(UTF-8) 선행 실행, PowerShell은 `OutputEncoding` 설정 |
| 폰트 미지원 | 유니코드 문자 깨짐 | Windows Terminal 사용 권장 안내. 레거시 CMD는 폰트 변경 가이드 제공 |
| macOS 바로가기 | `.app` 번들 또는 Automator 앱으로 Terminal 열기 | Tauri 앱 자체가 런처 역할 → 별도 바로가기 대신 앱 재실행으로 통일 가능 |

### macOS 범위 (필수)

1. VibeLign 실행 → 온보딩 화면 진입
2. 환경 점검
   - macOS 버전
   - 기본 셸 확인 (zsh / bash)
   - 인터넷 연결 / 디스크 공간
3. Claude Code 공식 native install 스크립트 실행: `curl -fsSL https://claude.ai/install.sh | bash`
4. 설치 후 검증 (새 셸 세션 spawn 후)
   - zsh에서 `claude --version`
   - bash에서 `claude --version`
   - `claude doctor`
5. 로그인 검증
   - `claude` 실행 후 브라우저 로그인 유도
   - 로그인 완료 확인 (대화 세션 시작 가능 여부)

### v1.1 범위 (확장)

1. VS Code 통합 터미널 / Git Bash 추가 최적화
2. 셸별 자동 복구 규칙 확대
3. 고급 환경 편차 대응 강화

### 기존 설치 감지

- Homebrew / WinGet / 기존 native 설치가 이미 있으면 현재 설치 방식을 먼저 감지한다.
- VibeLign은 무조건 덮어쓰지 않고, **유지 / 공식 경로로 전환 / 재설치** 중 하나를 선택하게 한다.

### 왜 이렇게 나누는가

- Windows와 macOS 모두에서 사용자가 실제로 자주 여는 대표 셸에서 바로 `claude`가 실행되어야 온보딩 완료라고 볼 수 있다.
- 따라서 첫 버전부터 Windows는 **CMD / PowerShell / WSL**, macOS는 **bash / zsh**를 필수 성공 범위로 잡아야 한다.
- 후속 버전에서는 대표 셸 바깥의 환경 편차와 최적화 범위를 넓히는 것이 현실적이다.

전체 소요 시간 목표:
- v1 기준: 5~10분
- WSL 지원까지 v1 필수 범위에 포함하므로, 실제 설치 시간은 환경에 따라 더 길어질 수 있음

---

## 6. 멀티 셸 지원 전략

### 핵심 원칙
**코알못은 터미널 종류를 모른다.** Windows에서는 cmd든 PowerShell이든 WSL이든, macOS에서는 bash든 zsh든, 어느 터미널에서 `claude`를 입력해도 무조건 동작해야 함.

### 구현 원칙

**1. 공식 설치를 우선 신뢰한다**

- Claude Code 가 공식 native install 스크립트로 정상 설치되면, 그 설치 결과(`~/.local/bin/claude` / `%USERPROFILE%\.local\bin\claude.exe`, 자동 등록 PATH)를 최대한 그대로 사용한다.
- VibeLign은 공식 경로를 대체하지 않고, 누락된 실행 경로와 검증만 보완한다.

**2. v1은 대표 셸 전부를 보장한다**

- Windows에서 가장 흔한 실행 환경은 CMD, PowerShell, WSL이다.
- macOS에서는 기본 셸이 zsh이지만, bash 사용자도 여전히 존재한다.
- v1은 이 대표 셸 전부에서 `claude` 실행 성공을 필수 기준으로 둔다.
- Windows native에서는 `claude` 실행 자체뿐 아니라 Git Bash 인식까지 확인해야 실제 사용 단계에서 막히지 않는다.

**3. PATH 보정은 대표 셸 기준으로 끝까지 확인한다**

- 공식 설치 후 `claude`가 바로 동작하지 않을 때만 경로 보정/shim을 시도한다.
- 시스템 전체를 크게 바꾸기보다 사용자 범위 PATH를 우선 사용한다.
- 단, 온보딩 종료 전에는 Windows(CMD / PowerShell / WSL)와 macOS(bash / zsh) 각각에서 실제로 `claude`가 잡히는지 검증해야 한다.

### 지원 매트릭스

| 터미널 | 동작 방식 | 결과 |
|--------|-----------|------|
| cmd | `claude` 실행 | v1 필수 |
| PowerShell 5/7 | `claude` 실행 | v1 필수 |
| WSL 안 Ubuntu | `claude` 실행 | v1 필수 |
| Windows Terminal | 기본 프로필 기준 `claude` 실행 | v1 포함 |
| macOS zsh | `claude` 실행 | v1 필수 |
| macOS bash | `claude` 실행 | v1 필수 |
| VS Code 통합 터미널 | 셸 종류에 따라 동작 | v1.1 최적화 |
| Git Bash | 실행 가능하면 지원, 아니면 fallback | v1.1 최적화 |

사용자는 자기가 무슨 터미널을 쓰는지 몰라도 됨.

### 구현 메모

- PATH 수정과 환경 반영은 필요 시에만 수행한다.
- 저수준 Win32 호출은 설계 메모 수준으로 남기되, 기획 단계에서는 특정 crate/API에 과도하게 고정하지 않는다.

---

## 7. 윈도 환경 편차 대응 전략

### 우선 대응할 에러 카테고리

v1에서는 모든 Windows 문제를 다루기보다, 실제 빈도가 높고 설치 성공률에 직접 영향을 주는 항목부터 대응한다.

#### A. 공식 설치 실패
- PowerShell/CMD 공식 install 스크립트 실행 실패 (ExecutionPolicy 차단, AMSI/Defender 차단, curl 부재 등)
- 네트워크/프록시 문제 (회사 프록시, 방화벽, VPN 환경 포함)
- Git for Windows 미설치

#### A-1. 공식 install 스크립트 변경 리스크

VibeLign은 Anthropic 의 공식 native install 스크립트(`install.sh` / `install.ps1` / `install.cmd`)를 감싸는 래퍼이므로, 스크립트 내용·URL·설치 위치가 바뀌면 영향을 받는다. 스크립트는 .exe 형태의 installer 보다 변동 빈도가 더 높을 수 있다.

- 스크립트 내부 동작이 아니라 입력(공식 스크립트 URL)과 출력(`claude --version`, `claude doctor`, 로그인 가능 여부, 설치 경로 `~/.local/bin/claude` 또는 `%USERPROFILE%\.local\bin\claude.exe`) 기준으로 최소 결합한다.
- 변경 감지 시 공식 문서 링크와 수동 경로를 안내한다.
- 이 리스크는 운영 단계에서 빠르게 패치할 수 있는 구조를 전제로 관리한다.

**모니터링 및 자동 검증 계획:**
- **주간 CI 자동 검증**: GitHub Actions scheduled workflow로 Windows/macOS 러너에서 공식 install 스크립트 fetch → 실행 → 새 셸 spawn → `claude --version` → `claude doctor` 통과 여부 자동 확인
- **스크립트 콘텐츠 변경 감지**: `install.sh` / `install.ps1` / `install.cmd` 의 SHA256 / 길이 / 설치 경로 출력 변화를 주기적으로 비교하여 변경 시 Slack/Discord 알림 (URL 변경뿐 아니라 스크립트 콘텐츠 자체 변경도 감시)
- **공식 문서 변경 감지**: code.claude.com/docs/en/setup 페이지를 주기적으로 스크래핑하여 URL/명령어 변경 시 알림
- **버전 핀 관리**: VibeLign이 지원하는 Claude Code 최소/최대 버전 범위를 설정 파일(`installer_compat.json`)로 관리. CI 검증 실패 시 해당 파일 업데이트 PR 자동 생성
- **핫픽스 체계:** 스크립트 깨짐을 감지하면 1차로 다운로드 페이지에 공지 배너 + 수동 설치 링크를 즉시 게시 (24시간 SLA). 앱 패치 배포는 best-effort 로 후속 진행. Tauri updater 는 사용자가 앱을 실행해야 적용되므로 SLA 의 1차 라인이 될 수 없다.

#### B. 실행 경로 문제
- 설치는 되었지만 CMD/PowerShell에서 `claude`가 안 잡힘
- PATH 반영 지연
- 기존 설치와 경로 충돌
- Git Bash 경로를 못 찾아 실제 명령 실행 단계에서 실패

#### C. 권한/보안 문제
- SmartScreen/UAC로 인한 설치 중단
- 회사 PC 정책 제한

#### D. WSL 관련 문제
- WSL 미설치
- WSL 1/2 차이
- 회사 환경에서 WSL 비활성화

이 중 **A/B/C/D 모두를 v1 핵심**으로 다룬다. 다만 v1에서 보장하는 것은 **WSL이 이미 사용 가능하거나 사용자가 활성화할 수 있는 환경에서 `claude` 실행까지 완료되는 것**이며, VS Code 통합 터미널 / Git Bash 같은 후속 셸 최적화는 v1.1로 둔다.

### 대응 전략

#### 1. 진단 우선
설치 시작 전 환경 점검 단계 강화. 문제를 미리 발견하고, 사용자가 다음 행동을 바로 알게 한다.

```
✅ Windows 11 Pro
✅ Git for Windows 설치됨
⚠️  Claude Code가 아직 설치되지 않았어요 [설치 시작]
❌ PowerShell에서 인터넷 연결 확인이 필요해요 [해결 방법]
⚠️  WSL은 아직 설정되지 않았어요 [지금 설정] [설정 방법 보기]
⚠️  기존 WinGet 설치가 감지됐어요 [유지] [공식 경로로 재설치]
```

#### 2. 로그 저장
설치 단계별 로그를 남기고, 실패 시 사용자가 복잡한 설명 없이 공유할 수 있게 한다.

#### 3. 폴백 체인
한 방법 실패 시 자동으로 다음 시도:
- 시스템 PATH 등록 실패 → 사용자 PATH로 fallback
- Native Windows 설치 실패 → 공식 CMD/PowerShell 대체 명령 제시
- WSL 설정 실패 → 수동 가이드 + 마이크로소프트 스토어 링크 직접 열기

#### 4. 베타에서 에러 패턴 수집
실사용자 에러를 모아 자동 복구 규칙을 점진적으로 늘린다.

#### 5. "도움말 화면" 강화
실패 시 에러 코드만 보여주지 말고 **"이런 에러는 보통 X가 원인이에요. 다음 중 시도해보세요"** 형태로 정리. 코알못이 무력감 안 느끼게.

#### 6. 베타 테스트 광범위하게
출시 전 주변 코알못 10~20명한테 다양한 윈도 환경에서 테스트:
- 회사 컴 (IT 정책 제한)
- 노트북 (가정용 에디션)
- 게이밍 PC (높은 사양)
- 가족 컴 (구버전)
- 한 명의 개발자 PC만 테스트하면 절대 못 잡음

### 추가 권장 엣지케이스 체크리스트

현재 문서에 주요 설치/로그인/셸/PATH 이슈는 이미 많이 포함되어 있다.
다만 실제 출시 기준으로는 아래 엣지케이스를 추가로 명시하는 것이 안전하다.

#### 1. 네트워크 / 다운로드 실패

- 설치 중 인터넷이 끊기면 어디까지 진행됐는지 보여주고 재시도할 수 있어야 한다.
- 회사망/느린 네트워크에서 install 스크립트 fetch / 바이너리 다운로드 timeout 시 수동 설치 링크를 바로 제공해야 한다.
- 프록시/VPN 감지는 했더라도, 인증이 필요한 프록시(로그인형 프록시)는 별도 안내가 필요하다.

#### 2. 기업 보안 환경

- 백신 (V3 / 알약 / 네이버 / Defender) / MDM / AppLocker / 실행 제한 정책으로 install 스크립트나 다운로드 바이너리가 차단될 때 사용자 친화적 메시지와 우회 안내가 필요하다.
- 회사 PC에서 PowerShell 실행 정책 또는 UAC 제한으로 설치가 막힐 경우 수동 설치 경로를 분명히 보여줘야 한다.
- IT 관리자에게 전달할 허용 URL / 프로세스 목록을 한 번에 복사할 수 있으면 지원 비용이 줄어든다.

#### 3. 기존 설치 / 기존 설정 충돌

- 이미 `claude`가 PATH에 있는데 다른 위치를 가리키는 경우 충돌을 감지해야 한다.
- 기존 로그인 세션 / 설정 파일 / 인증 상태가 남아 있을 때 유지 / 재설정 / 재로그인 중 무엇을 할지 선택할 수 있어야 한다.
- Homebrew / WinGet / 수동 설치본이 동시에 존재할 때 우선순위를 명확히 정의해야 한다.

#### 4. 셸 / 실행 환경 다양성

- Windows Terminal 커스텀 프로필처럼 기본 셸이 CMD / PowerShell / WSL이 아닌 경우를 고려해야 한다.
- macOS에서 fish 등 비표준 셸 사용자는 v1 지원 범위 밖인지, 수동 안내 대상인지 명확히 해야 한다.
- VS Code 통합 터미널은 v1.1 대상으로 두더라도, 최소한 “v1 필수 보장 범위 아님”을 문서에 명확히 적어야 한다.

#### 5. 로그인 / 인증 마무리 실패

- 브라우저 로그인 성공 후에도 터미널 쪽 세션 반영이 늦는 경우 재검증 루프가 필요하다.
- 사용자가 브라우저를 닫았거나 중간에 취소했을 때 로그인 단계로 쉽게 복귀할 수 있어야 한다.
- 로그인은 됐지만 첫 대화 시작이 실패한 경우를 별도 실패 상태로 구분해야 한다.

#### 6. 롤백 / 수동 전환

- 자동 설치가 중간 실패했을 때 “원래 상태 유지” 또는 “수동 설치로 전환” 경로가 있어야 한다.
- 일부만 설치된 상태(파일은 생겼지만 PATH 미반영, 로그인 미완료 등)를 어떻게 정리할지 정의해야 한다.
- 자동 설치 실패 후 수동 가이드로 전환되는 흐름을 명확히 UX에 포함해야 한다.
- 사용자가 "설치가 꼬였으니 처음 상태로 돌리고 싶다"고 느낄 때를 위해, 언인스톨/정리 버튼과 기대 결과를 명확히 제공해야 한다.

#### 6-1. 언인스톨 / 깨끗한 제거

- VibeLign이 추가한 PATH / shim / 설정 / 바로가기 / 앱 내부 상태를 어디까지 제거할지 명확히 정의해야 한다.
- 공식 installer로 설치된 Claude Code 본체 제거와, VibeLign이 덧붙인 실행 보정/온보딩 상태 제거를 구분해서 안내해야 한다.
- 언인스톨 후 기대 상태는 **"사용자가 설치 전 상태로 돌아왔다고 이해할 수 있는 상태"** 여야 한다.
- 언인스톨은 삭제 대상과 보존 대상을 사용자에게 보여주고 실행해야 한다.
- 로그인 정보/캐시/로그를 유지할지 함께 지울지 선택할 수 있으면 지원 비용을 줄일 수 있다.

**삭제 대상 목록 (v1 확정안):**

| 구분 | macOS / Linux / WSL | Windows Native |
|------|---------------------|----------------|
| Claude Code 바이너리 | `~/.local/bin/claude` | `%USERPROFILE%\.local\bin\claude.exe` |
| Claude 설정/세션 | `~/.claude/` (하위 설정·세션·캐시) | `%USERPROFILE%\.claude\` |
| 인증 토큰 저장소 | macOS Keychain `com.anthropic.claude` 항목, Linux `~/.config/claude/`, WSL 동일 | Windows Credential Manager `Claude Code` 항목 |
| 셸 PATH 라인 | `.zshrc` / `.bashrc` / `.bash_profile` / `.profile` 내 VibeLign 추가 마커 블록(`# >>> vibelign >>>` ~ `# <<< vibelign <<<`) | 사용자 PATH 환경변수의 `%USERPROFILE%\.local\bin` 엔트리 (VibeLign 이 추가한 경우만) |
| VibeLign shim/바로가기 | `~/Applications/VibeLign-Claude.command`, 바탕화면 `.command` | `%USERPROFILE%\Desktop\Claude Code.lnk`, Start Menu 바로가기 |
| VibeLign 온보딩 상태 | `~/Library/Application Support/VibeLign/onboarding.json` | `%APPDATA%\VibeLign\onboarding.json` |

**삭제 정책:**
- VibeLign 은 자신이 **직접 추가한 항목만** 제거한다. 사용자가 수동으로 건드린 rc 파일 라인은 손대지 않기 위해 추가 시 마커 블록으로 감싸고, 제거 시 마커 블록 단위로만 삭제한다.
- Claude Code 제거는 **공식 제거 경로**를 기준으로 한다. 즉, 공식 uninstall 명령이 있으면 그것을 1차 경로로 사용하고, 없으면 공식 setup 문서에 나온 수동 삭제 절차를 VibeLign 이 GUI uninstall flow 로 감싼다.
- 공식 제거 경로 실행 후에도 위 목록 기준으로 남은 항목이 있으면 보조 cleanup 으로 정리한다.
- 3단계 선택 UI: **[전체 제거] / [VibeLign 추가분만 제거(Claude Code 본체·로그인 유지)] / [취소]** — 각 선택지의 "삭제될 파일 목록" 을 실행 전 미리 보여준다.
- Keychain / Credential Manager 토큰은 기본 "유지" 로 두고, 사용자가 명시적으로 체크할 때만 삭제 (재로그인 비용 고려).

**Phase 0 추가 확인:**
- 공식 제거 경로 확인: 전용 uninstall 명령이 있는지, 없으면 공식 setup 문서의 수동 삭제 절차가 최신 기준으로 어떻게 안내되는지 실기기 확인
- macOS Keychain · Windows Credential Manager 의 실제 항목 이름 (Claude Code 가 어떤 키로 저장하는지 실기기 확인)

#### 7. 초보자용 안내 문구

- 실패 메시지는 기술 용어보다 “지금 무엇을 하면 되는지” 중심이어야 한다.
- 설치 성공 기준은 계속 `claude --version`이 아니라 “실행 + 로그인 + 첫 대화 가능”으로 통일해야 한다.
- 사용자가 터미널 종류를 몰라도 되도록, 실패 화면은 버튼/다음 행동 중심으로 설계해야 한다.

### 출시 전 최소 추가 권장 항목

v1 출시 전에는 아래 3가지를 최소 필수 엣지케이스로 추가하는 것을 권장한다.

1. 오프라인/느린 네트워크 실패 시 재시도 + 수동 설치 전환
2. 기존 설치 / PATH 충돌 감지
3. 자동 설치 중간 실패 시 롤백 또는 정리 경로
4. 설치 이후 문제 발생 시 깨끗하게 되돌리는 언인스톨/정리 경로

#### 7. 출시 전략
"기능 다 만들고 출시"보다 "**최소 기능 출시 → 실제 사용자 에러 모으기 → 패치**" 사이클이 효과적. 베타 출시 → 디스코드에서 사용자 피드백 받으며 반복.

---

## 8. 다운로드 후 첫 실행 온보딩 UX

### 다운로드 직후 진입 경험
- "Mac용 다운로드" / "Windows용 다운로드" 큰 버튼 두 개
- 사용자 OS 자동 감지해서 해당 OS 버튼 강조
- 다운로드 후 사용자는 **VibeLign을 실행하면 바로 온보딩 화면에서 Claude Code 자동 설치를 진행**한다.

### 다운로드 페이지 내 보안 경고 안내 섹션
"처음 실행 시 보안 경고가 뜰 수 있어요"
- macOS: 우클릭 → 열기 스크린샷 단계별 안내
- Windows: SmartScreen "추가 정보 → 실행" 스크린샷 단계별 안내
- 톤은 "정상이에요, 이렇게 하시면 됩니다"

### 시스템 요구사항
- Windows 10 (1903 이상) / Windows 11
- macOS 12 (Monterey) 이상
- 디스크 5GB 이상
- 인터넷 연결 필요 (설치 시)

### 동영상 가이드 (선택)
1분 이내 짧은 설치 영상 → 코알못이 시각적으로 안심

---

## 9. 작업 순서

### Phase 0 — 사전 조사 (1주)
- code.claude.com/docs/en/setup 의 native install 스크립트 명령·요구 사항·설치 위치 (`~/.local/bin/claude`, `%USERPROFILE%\.local\bin\claude.exe`) 최신 상태 확정
- Windows PowerShell `irm | iex` 실행이 ExecutionPolicy / AMSI / Defender / 한국 백신 (V3, 알약, 네이버) 환경에서 실제 동작하는지 실기기 확인
- Windows CMD `install.cmd` 경로의 curl 가용성 / 인코딩 / 종료 코드 확인
- macOS `install.sh` 가 Apple Silicon / Intel 모두에서 동일 결과를 내는지 확인
- WSL 1 / WSL 2 환경에서 `install.sh` 동작 확인
- **로그인 완료를 비상호작용으로 검증할 수 있는 명령(`claude auth status` 류)이 실제로 존재하는지 확인.** 없으면 v1 의 "성공 판정" 을 사용자 수동 클릭 또는 `claude` REPL 의 첫 응답 감지로 낮춘다
- 다양한 윈도 환경에서 수동 테스트 (10가지 이상 케이스, 한국 환경 포함)

### Phase 1 — v1 온보딩 내 자동 설치 기본 흐름 (4~5주)

Phase 1 세부 일정 (Track 단위):

| 주차 | Track | 산출물 |
|------|-------|--------|
| 1주 | Track B (환경 점검) | OS/셸 감지, Windows 사전 조건 점검, macOS bash/zsh 환경 점검 |
| 2주 | Track C (설치 실행) | 공식 install 스크립트 래퍼 (PowerShell/CMD/sh), ExecutionPolicy 처리, 기존 설치 감지/분기 처리 |
| 3주 | Track D (실행 보장) | CMD/PowerShell/WSL/bash/zsh PATH 보정, 셸별 검증, 바로가기 |
| 3~4주 | Track E (로그인/성공) | 로그인 유도, 실패 대응, 성공 판정 |
| 4~5주 | Track A + F (UI + 로그) | 진행 상태 UI 마무리, 로컬 로그 저장, 텔레메트리 기초 |

- 각 Track은 독립적이지 않으므로 완전 병렬은 불가하나, Track B 완료 후 C/D는 부분 병렬 가능
- Windows 실기기 테스트 시간을 별도로 확보해야 하므로 기존 2~3주 → 4~5주로 조정

### Phase 2 — v1 베타 + 에러 수집 (2~4주)
- 디스코드/슬랙 베타 테스터 모집
- 로그 공유 기능
- 에러 패턴 DB 구축
- 우선순위 높은 에러부터 폴백 체인 추가

### Phase 3 — v1.1 후속 셸 최적화 확장 (2주)
- VS Code 통합 터미널 / Git Bash 최적화
- 셸별 자동 복구 규칙 확장
- 고급 환경 지원 UX 정리

### Phase 4 — 정식 출시 (1주)
- 다운로드 페이지 정비
- 동영상 가이드 제작
- 마케팅 자료

### Phase 5 — 옵션 B 검토 (사용자 반응 보고 결정)
- 통합 모드 가치 측정
- 사용자가 터미널 사용에 만족하면 Phase 5 보류

### 구현 체크리스트

#### v1 구현 체크리스트

- [ ] 온보딩 첫 화면에 Windows / macOS 설치 진입점 배치
- [ ] OS 감지 및 플랫폼별 설치 경로 분기
- [ ] Windows에서 Git for Windows 설치 여부 감지
- [ ] 기존 Claude Code 설치 방식(native / Homebrew / WinGet / npm / 기타) 감지
- [ ] Claude Code 공식 native install 스크립트 실행 래퍼 구현 (PowerShell / CMD / install.sh)
- [ ] PowerShell ExecutionPolicy 감지 + 필요 시 `-ExecutionPolicy Bypass` spawn
- [ ] 설치 후 **새 셸 세션 spawn** 후 검증 수행 (현재 세션 PATH 미반영 문제 회피)
- [ ] 설치 로그 파일 저장 (사용자명·홈 경로·도메인 마스킹 포함)
- [ ] 설치 후 PowerShell에서 `claude --version` 검증
- [ ] 설치 후 CMD에서 `claude --version` 검증
- [ ] 설치 후 WSL에서 `claude --version` 검증 (v1 필수)
- [ ] 설치 후 macOS zsh에서 `claude --version` 검증
- [ ] 설치 후 macOS bash에서 `claude --version` 검증
- [ ] 설치 후 `claude doctor` 검증
- [ ] Git Bash 경로 인식 실패 시 fallback 처리
- [ ] 브라우저 로그인 유도 흐름 구현
- [ ] 로그인 실패 대응 UI 구현
- [ ] 로그인 완료 후 대화 시작 가능 상태 확인
- [ ] 기본 터미널 자동 선택 및 바로가기 생성
- [ ] PATH 반영 실패 시 사용자 범위 fallback 구현
- [ ] 설치 실패 시 부분 설치 정리(cleanup) 경로 구현
- [ ] 사용자가 직접 실행할 수 있는 언인스톨/재설정 흐름 설계
- [ ] 삭제 대상 / 유지 대상 / 재로그인 필요 여부를 표시하는 언인스톨 UX 정의
- [ ] SmartScreen / Gatekeeper 안내 화면 제공
- [ ] 옵트인 로그 공유 / 텔레메트리 동의 UI 구현
- [ ] 온보딩 내 설치 성공/실패 이벤트 측정 포인트 정의

#### v1.1 구현 체크리스트

- [ ] VS Code 통합 터미널 추가 검증
- [ ] Git Bash 최적화 및 fallback 강화
- [ ] 셸별 자동 복구 규칙 추가
- [ ] 고급 환경 편차 대응 확대

#### 출시 전 검증 체크리스트

- [ ] Windows 10 / 11 실기기 테스트
- [ ] macOS Apple Silicon / Intel 테스트
- [ ] Git for Windows 미설치 환경 테스트
- [ ] 기존 WinGet 설치 환경 테스트
- [ ] 프록시/VPN 환경 테스트
- [ ] SmartScreen / Gatekeeper 경고 UX 점검
- [ ] 로그인 성공 / 실패 / 권한 부족 계정 시나리오 테스트
- [ ] WSL 환경 실기기 테스트
- [ ] macOS zsh / bash 각각에서 실행 테스트
- [ ] Claude Code 자동 업데이트 후 재검증 테스트

### 개발 태스크 분해

아래 항목은 실제 구현 시 이슈/PR 단위로 바로 나눌 수 있는 작업 묶음이다.

#### Track A — 온보딩 설치 진입 UI

**A1. 온보딩 시작 화면**
- 목표: Windows / macOS 사용자가 VibeLign 온보딩 안에서 바로 Claude Code 설치를 시작할 수 있는 첫 화면 제공
- 산출물: 플랫폼별 설치 버튼, 현재 OS 강조, 경고/안내 슬롯

**A2. 진행 상태 UI**
- 목표: 설치 단계가 어디까지 왔는지 시각적으로 표시
- 산출물: 단계 리스트, 진행 바, 성공/실패 상태 표시

#### Track B — 환경 점검 엔진

**B1. OS / 셸 / 환경 감지**
- 목표: 현재 OS, 터미널 환경, 디스크 공간, 네트워크 상태 점검
- 산출물: 진단 결과 모델, 점검 결과 카드 UI

**B2. Windows 사전 조건 감지**
- 목표: Git for Windows, 기존 Claude Code 설치 방식, WSL 존재 여부 확인
- 산출물: Windows 전용 진단 로직, 설치 방식 분류 결과

#### Track C — Claude Code 설치 실행

**C1. 공식 install 스크립트 실행 래퍼**
- 목표: 플랫폼별 Anthropic 공식 native install 스크립트를 안전하게 실행 (Win PowerShell / Win CMD / macOS / Linux / WSL)
- 핵심 동작:
  - PowerShell 경로는 ExecutionPolicy 감지 → 필요 시 `-ExecutionPolicy Bypass` spawn
  - CMD 경로는 `curl` 사용 가능성 점검 후 fallback
  - 스크립트 stdout/stderr 실시간 streaming 으로 GUI 진행 표시
  - 설치 후 **새 셸 세션을 spawn 하여** 검증 (현재 세션 PATH 미반영 문제 회피)
- Win/macOS 모두 "스크립트 실행 래퍼" 단일 추상화로 설계하고, 플랫폼별 분기는 "어떤 스크립트 URL + 어떤 셸 + 어떤 ExecutionPolicy 처리" 만 다르게 한다
- 산출물: install script wrapper (Rust), 실행 로그 수집, 새 셸 spawn 검증 helper

**C2. 기존 설치 처리**
- 목표: 기존 native / WinGet / Homebrew / npm 설치가 있을 때 유지/재설치 선택 제공
- v1 범위: **유지 / 재설치 두 가지만 제공**. "공식 경로로 전환"(=기존 제거 + 재설치 + 로그인 재요구) 은 v1.1 로 유예
- npm 설치 감지 시 deprecated 안내 + 공식 native 재설치 권장 메시지 표시
- 산출물: 기존 설치 감지 로직(native binary path / Homebrew cask / WinGet package / npm global), 사용자 선택 UI, 분기 처리

#### Track D — 실행 가능 상태 보장

**D1. v1 셸 실행 보장**
- 목표: Windows CMD / PowerShell / WSL과 macOS bash / zsh에서 `claude` 실행 가능 상태 보장
- 산출물: 실행 검증 로직, PATH fallback, 셸별 확인 로직, 기본 터미널 선택

**D2. Git Bash 경로 fallback**
- 목표: Claude Code 내부 Git Bash 인식 실패 시 자동 보정
- 산출물: Git Bash 경로 탐지, 설정 반영 fallback

**D3. 바로가기 생성**
- 목표: 사용자가 설치 후 바로 더블클릭으로 Claude Code를 실행
- 산출물: 바탕화면 바로가기, 기본 터미널 launch 설정

#### Track E — 로그인 / 온보딩 성공 판정

**E1. 로그인 유도 플로우**
- 목표: 설치 후 자연스럽게 브라우저 로그인까지 연결
- 산출물: 로그인 시작 버튼/가이드, 상태 표시

**E2. 로그인 실패 대응**
- 목표: 브라우저 미실행, 콜백 실패, 권한 부족 계정 등 실패 시나리오 처리
- 산출물: 실패 유형별 가이드 UI, 재시도 흐름

**E3. 성공 판정 (PTY 기반 REPL 응답 감지)**
- 목표: 단순 설치가 아니라 온보딩 안에서 실제 대화 시작 가능 상태까지 확인
- 구현 전제: 공식 setup 문서에 비상호작용 `claude auth status` 가 없으므로, **PTY 에서 `claude` 를 기동 → 프롬프트 출력 감지 → 테스트 메시지 1회 전송 → 스트리밍 응답 첫 토큰 수신까지** 를 성공 조건으로 정의
- 기술 스택:
  - Rust `portable-pty` crate 로 Windows ConPTY / Unix pty 추상화 통일
  - stdout 를 ANSI escape 제거 후 정규식/상태머신으로 파싱
  - 타임아웃 60초 (네트워크·브라우저 로그인 지연 고려)
- 실패 분류: (a) PTY 기동 실패, (b) 로그인 프롬프트에서 멈춤, (c) 로그인 후 응답 없음, (d) 권한 부족 계정 메시지 감지 — 각각 E2 의 대응 흐름으로 라우팅
- Phase 0 선행 확인: `claude --print`, `claude --headless`, `claude auth status` 중 공식 지원 명령이 추가됐는지 재확인. 존재 시 PTY 경로 대신 해당 명령을 1차로 사용
- 산출물: `pty_probe` 모듈(Rust), 응답 파싱 상태머신, 성공/실패 분류 enum, 완료 화면

#### Track F — 로그 / 측정 / 베타 운영

**F1. 로컬 로그 저장**
- 목표: 설치 단계별 로그를 로컬에 남기고 공유 가능하게 하기
- 산출물: 로그 파일 포맷, 로그 열기/공유 UI

**F2. 옵트인 텔레메트리**
- 목표: 설치 성공률과 실패 지점을 정량 측정
- 산출물: 동의 다이얼로그, 이벤트 스키마, 전송 파이프라인

**F3. 에러 패턴 수집 루프**
- 목표: 베타에서 수집한 실패 유형을 자동 복구 우선순위로 연결
- 산출물: 에러 분류표, 우선순위 큐, 회고 템플릿

#### Track G — v1.1 셸 최적화 확장

**G1. VS Code / Git Bash 추가 최적화**
- 목표: 대표 셸 외의 자주 쓰는 환경에서도 실행 안정성을 높임
- 산출물: 추가 셸 감지/보정 로직, 최적화 UI/안내

**G2. 셸별 복구 규칙 확장**
- 목표: 셸별 실패 패턴을 더 많이 자동 복구할 수 있게 함
- 산출물: 복구 규칙 세트, 셸별 validation flow

**G3. 고급 환경 복구 가이드**
- 목표: 기업망/특수 셸/고급 환경 편차에서 수동 복구 경로 제공
- 산출물: 복구 가이드, 문서 링크, 실패 화면

#### 권장 구현 순서

1. Track B (환경 점검)
2. Track C (설치 실행)
3. Track D (대표 셸 실행 보장)
4. Track E (로그인 / 성공 판정)
5. Track A (UI polish + 진행 상태)
6. Track F (로그 / 측정)
7. Track G (후속 셸 최적화 확장)

---

## 10. 측정 지표

### 성공 지표
- VibeLign 온보딩 진입 → 실제 `claude` 첫 실행까지 도달률 (목표: 80% 이상)
- 평균 설치 소요 시간 (목표: 다운로드 제외 5분 이내)
- 설치 실패율 (목표: 10% 이하)
- v1 기준: 설치 후 **Windows(CMD / PowerShell / WSL)와 macOS(bash / zsh)에서 `claude`가 실행되는 비율**
- v1.1 기준: 설치 후 **대표 셸 + 후속 최적화 셸(VS Code 통합 터미널 / Git Bash 등)에서 `claude`가 실행되는 비율**
- 온보딩 안에서 **로그인까지 완료**되어 대화 시작 가능한 비율 (진정한 성공 지표)
- 설치 후 7일 내 재방문률 (Claude Code 실제 사용 지표)

### 측정 방법

지표를 수집하려면 수단이 필요하다. 사용자 동의 기반으로 다음 방식을 적용한다.

| 방식 | 설명 | 시점 |
|------|------|------|
| 익명 텔레메트리 (옵트인) | 설치 단계별 도달/실패 이벤트를 익명 ID로 전송. 개인정보 없음 | v1 베타부터 |
| 로컬 로그 | 모든 설치 단계를 로컬 파일에 기록. 사용자가 "로그 공유" 버튼으로 자발적 제출 | v1부터 |
| 베타 설문 | 설치 완료 후 간단한 만족도 설문 (1~2문항). 강제 아님 | v1 베타 |
| 다운로드 카운터 | 다운로드 페이지에서 OS별 다운로드 수 집계 | v1부터 |

- 텔레메트리는 **첫 실행 시 명시적 옵트인** 다이얼로그를 보여주고, 거부하면 로컬 로그만 유지
- 수집 항목: 설치 시작/완료 타임스탬프, 각 단계 성공/실패, OS 버전, 에러 코드 (개인정보·IP 제외)

**측정 인프라 후보:**

| 용도 | 후보 | 비고 |
|------|------|------|
| 이벤트 텔레메트리 | PostHog (자체 호스팅 또는 클라우드) | 오픈소스, 무료 티어 충분, 퍼널 분석 내장 |
| 다운로드 카운터 | GitHub Releases API 또는 자체 CDN 로그 | 추가 인프라 불필요 |
| 로그 공유 | GitHub Gist 자동 생성 또는 디스코드 봇 업로드 | 사용자가 한 번 클릭으로 공유 가능 |
| 베타 피드백 채널 | 디스코드 전용 채널 | 한국 사용자 비중 높으면 카카오톡 오픈채팅 병행 |

- v1 베타에서는 PostHog 클라우드 무료 티어로 시작, 사용자 수 증가 시 자체 호스팅 전환 검토
- 로그 공유는 로컬 로그 파일을 클립보드 복사 또는 GitHub Gist로 자동 업로드하는 두 경로 제공

### 에러 지표
- 카테고리별 에러 발생 빈도
- 자동 복구 성공률
- 사용자 보고 횟수

---

## 11. 경쟁 환경 분석

| 제품 | 설치 방식 | 설치 난이도 | 비고 |
|------|----------|-----------|------|
| **Cursor** | `.dmg` / `.exe` 다운로드 → 더블클릭 | 매우 쉬움 | 자체 IDE |
| **Windsurf** | `.dmg` / `.exe` 다운로드 → 더블클릭 | 매우 쉬움 | 자체 IDE |
| **GitHub Copilot** | VS Code 확장 설치 | 쉬움 | 기존 IDE 사용자 대상 |
| **Claude Code (현재)** | CLI 설치 + 터미널 사용 | 어려움 | 개발자 대상 설계 |
| **VibeLign (목표)** | VibeLign 앱 (`.dmg` / `.exe`) 다운로드 → 실행 → 온보딩 안에서 Anthropic 공식 native install 스크립트 자동 실행 | 쉬움 | Claude Code 자체는 공식 스크립트로 설치하고, VibeLign 은 그 실행과 검증을 코알못 친화적으로 감싸기만 함 |

### VibeLign의 차별점

- 자체 IDE를 새로 배우게 하지 않는다.
- Claude Code 자체를 대체하지 않고, **VibeLign 온보딩 안에서 설치와 첫 실행의 진입 장벽만 제거**한다.
- 장기적으로는 설치 이후에도 VibeLign 자체 기능과 연결되어야 제품 가치가 유지된다.

---

## 12. 검토 사항 (확정 전 결정 필요)

1. **Windows에서 Native PowerShell 스크립트 / CMD 스크립트 / WSL 선택 구조를 어떻게 UI로 설명할지** (코알못은 이 셋의 차이를 모름. 기본은 PowerShell, fallback 자동 결정 권장)
2. **API 키 옵션 노출 위치** — 기본 화면 vs 고급 설정 vs 완전 숨김
3. ~~**자동 업데이트 시점**~~ → 섹션 4 "업데이트 전략"에서 결정 완료
4. **로그 수집 동의** → 섹션 10 "측정 방법"에서 옵트인으로 결정. 텔레메트리 수집 항목의 최종 범위만 확정 필요
5. **정식 코드 서명 도입 시점** — 사용자 수 기준
6. **베타 채널 운영 방식** — 디스코드 / 슬랙 / 카카오톡 오픈채팅
7. **온보딩 이후 장기 가치 전략** — 설치 이후에도 VibeLign이 계속 사용되는 이유를 어떻게 만들지 (섹션 11 경쟁 분석 참고)

   **초기 방향:** 설치 완료 후에도 VibeLign GUI를 여는 이유를 만들어야 제품이 존속한다. 후보:
   - **프로젝트 대시보드**: anchor 구조 시각화, 패치 이력, 코드 건강도를 한눈에 보여주는 허브
   - **Claude Code 상태 모니터**: 설치 상태, 버전, 로그인 만료, 사용량을 VibeLign에서 확인
   - **온보딩 가이드 연속 제공**: 설치 후 "첫 프로젝트 만들기", "anchor 설정하기" 등 단계별 가이드로 자연스럽게 VibeLign 기능 도입
   - **설정 관리자**: CLAUDE.md, hook, MCP 서버 설정을 GUI로 관리
   - 이 중 어떤 방향을 우선할지는 v1 베타 사용자 반응을 보고 결정하되, 설치 완료 화면에서 "다음 단계"로 자연스럽게 연결되는 구조는 v1에 미리 설계해 둔다

---

## 13. 마무리

이 기능은 VibeLign의 **시장 확장 결정 지점**. 코알못 진입 장벽 0으로 만들면 잠재 사용자가 개발자에서 일반인으로 확장됨. 단, 이 기능은 별도 인스톨러가 아니라 **VibeLign 제품 내부 온보딩 경험**으로 제공되어야 한다.

핵심 원칙:
1. Claude Code 설치는 code.claude.com/docs/en/setup 의 native install 스크립트 기준으로 유지하되, VibeLign 온보딩 안에서 스크립트 변경에 대비한 감지/폴백 전략 확보 (자체 .exe / .msi installer 를 만들지 않는다)
2. 사용자가 터미널 종류를 몰라도 Windows(CMD / PowerShell / WSL)와 macOS(bash / zsh) 어디서든 `claude`만 입력하면 동작
3. v1은 대표 셸 전부를 지원하고, v1.1은 후속 셸 최적화와 자동 복구 범위를 확장
4. 환경변수 자동 등록 + 실행 경로 보정으로 `claude` 실행 가능 상태 보장
5. **온보딩 성공 = 로그인까지 완료되어 대화 시작 가능한 상태**
6. 윈도 환경 편차에 대비한 진단 + 폴백 + 로그 시스템
7. 옵트인 텔레메트리로 지표 수집, 데이터 기반 개선
8. 베타로 빨리 출시 → 실사용자 에러 수집 → 패치 사이클

옵션 A로 빠르게 출시하고, 사용자 데이터로 옵션 B 가치 판단하는 단계적 접근 권장.

---

*이 문서는 2026-04-13 Claude Dispatch 세션에서 작성. VibeLign-LSP-논의.md, VibeLign-줄수-구현가이드.md와 함께 참고.*
