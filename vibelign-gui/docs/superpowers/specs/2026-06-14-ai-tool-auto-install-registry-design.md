# AI 도구 자동설치 레지스트리 — 설계 스펙

- 날짜: 2026-06-14
- 대상: `vibelign-gui` (백엔드 `src-tauri/src/onboarding/` + `commands/`, 프론트 온보딩/설정/작업방)
- 상태: 설계 확정 대기(사용자 리뷰)

## 1. 배경 / 문제

대화방(기획 페르소나)·작업방의 모델은 전부 **CLI 서브프로세스**로 실행된다(`planning_persona.rs`: claude `-p`, codex `exec`, agy `-p`, opencode `run -m opencode/deepseek-v4-flash-free`). 그런데 **자동설치되는 건 Claude Code 하나뿐**(`onboarding/macos.rs`·`windows.rs`). codex·opencode·antigravity(agy)를 쓰려면 사용자가 직접 설치해야 하고, 초보는 여기서 막혀 이탈한다.

핵심 통찰:
- **진짜 벽은 설치 + 인증 두 가지**다. 설치해도 codex=OpenAI, agy=Google 인증이 필요.
- **opencode는 이미 무료 모델(`deepseek-v4-flash-free`)에 연결**돼 있어 **키·결제·인증이 전혀 필요 없다** → 초보 무키 기본값으로 최적.
- 웹 검증 결과 **셋 다 CLI 설치기 존재**(Claude와 같은 curl/PowerShell 원라이너 패턴). antigravity도 `agy` 바이너리를 설치한다.

## 2. 목표 / 비목표

**목표**
- opencode·codex·antigravity(agy)를 **앱 안에서 원클릭 자동설치**(macOS + Windows 둘 다).
- **초보 기본값 = opencode + 무료 deepseek**(설치만 하면 키·결제 없이 즉시 동작).
- 설치 후 인증이 필요한 도구(codex=OpenAI, agy=Google)는 **인증 단계를 안내**.
- **자동설치가 불가/실패하면 "가이드 수동설치"로 폴백**(설치 페이지 열기 + 단계 안내) — 범용 원칙.
- 작업방 "실행 도구 없음" 데드엔드 제거 → opencode 무료 원클릭으로 직행.

**비목표**
- Claude Code의 기존 설치 플로(`onboarding/`)는 **건드리지 않는다**(검증된 코드 보존). 신규 도구만 새 일반화 경로로.
- 직접-API 호출 경로(키 붙여넣기) — 이번 범위 제외(CLI 전용 유지).
- 인증 자체의 자동화(OpenAI/Google 로그인 대행) — 불가/위험. 안내만.
- cursor·claude_desktop 등 MCP-only 도구 — 범위 밖.

## 3. 설계

### 3-1. 설치 레지스트리 (데이터 주도)

도구별 설치 메타를 **순수 데이터 테이블**로 정의(코드 수정 없이 명령 교정 가능, 테스트 용이):

```
ToolInstaller {
  id,                 // "opencode" | "codex" | "agy"
  displayName,
  probeBinary,        // 설치 후 PATH 에서 찾을 실행파일명 (win 은 .cmd/.exe 포함 해석)
  install: {
    macos:  InstallCmd,   // 예: bash -c "curl -fsSL https://opencode.ai/install | bash"
    windows: InstallCmd,  // 예: powershell -ExecutionPolicy Bypass -c "irm ... | iex"
  },
  auth: "none" | "login",   // 설치 후 필요한 인증
  authHint,                 // 인증 안내 문구 + (있으면) 로그인 명령/URL
  manualUrl,                // 자동설치 실패 시 열어줄 공식 설치 페이지
  recommendedForBeginner,   // opencode=true
}
```

**확정 설치 명령(웹 검증):**

| id | macOS install | Windows install | probe | auth | manualUrl |
|---|---|---|---|---|---|
| **opencode** | `curl -fsSL https://opencode.ai/install \| bash` | `npm install -g opencode-ai` (Node 필요; 없으면 가이드 수동) | `opencode` | none(무료 deepseek) | https://opencode.ai/download |
| **codex** | `npm install -g @openai/codex` (Node22; 없으면 PowerShell/brew 대안 안내) | `powershell -ExecutionPolicy Bypass -c "irm https://chatgpt.com/codex/install.ps1 \| iex"` | `codex` | login(OpenAI) | https://www.npmjs.com/package/@openai/codex |
| **agy** | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` | `powershell -ExecutionPolicy Bypass -c "irm https://antigravity.google/cli/install.ps1 \| iex"` | `agy` | login(Google) | https://antigravity.google/docs/cli-install |

> Node 의존(opencode-win·codex-mac)인 경우: 설치 전 `node -v` 확인 → 없으면 자동설치하지 말고 "Node 설치 필요" 가이드 수동으로 폴백(Node 자동설치는 범위 밖).

### 3-2. 설치 런타임 (백엔드)

신규 `commands/tool_install.rs`(또는 `onboarding/tool_installer.rs`):
- `install_tool(id) -> 스트리밍`: 레지스트리에서 플랫폼별 InstallCmd 선택 → spawn(로그 stdout/stderr 스트림, Claude 설치기처럼 진행 이벤트 emit) → 종료코드 확인 → **셸 프로브**(`find_executable(probeBinary)` + 새 로그인 셸에서 한 번 더 확인, 기존 onboarding 프로브 헬퍼 재사용) → 결과(설치됨/실패) 반환.
- `tool_install_status(id) -> {installed, authReady?}`: `find_executable` 로 설치 여부, (login 도구는) 간단한 인증 프로브.
- PATH: 모든 spawn 은 `augmented_vib_path()` 사용(페르소나 PATH 함정 회피, `~/.local/bin`·`~/.bun/bin` 포함 확인).
- 재사용: 가능한 한 `onboarding/` 의 spawn·로그스트림·셸프로브 헬퍼를 추출해 공유(중복 최소화). Claude 전용 상태머신은 그대로 두고, 신규 도구는 더 단순한 공유 런타임 사용.

검증/안전:
- `id` 는 레지스트리 화이트리스트만(임의 명령 실행 금지). InstallCmd 는 코드 내 상수 — 사용자 입력으로 명령 구성 안 함.
- 설치는 명시적 사용자 클릭에서만 시작(자동 실행 금지).

### 3-3. 인증 안내 (설치 후)
- opencode: 없음 — 설치 즉시 사용 가능(무료 모델 고정).
- codex: "OpenAI 로그인이 필요해요 — 터미널에서 `codex` 실행 후 로그인" + (가능 시) 로그인 트리거 버튼/안내.
- agy: "Google 로그인이 필요해요 — `agy` 최초 실행 시 브라우저 로그인" 안내.
- 인증은 **자동화하지 않고 단계 안내**만(대행 불가·위험).

### 3-4. 가이드 수동설치 폴백 (범용)
자동설치가 불가(예: Node 없음, 지원 안 되는 플랫폼)하거나 실패(종료코드≠0 / 프로브 실패)하면:
- `manualUrl` 열기 버튼 + 플랫폼별 설치 명령을 **복사 가능 텍스트**로 표시 + "설치 후 '다시 확인'" 버튼.
- 절대 조용히 실패하지 않음 — 항상 다음 행동을 제시.

### 3-5. UI / 기본값
- **온보딩/설정 도구 선택**(`ToolSetupSelector` — H3 배지 확장): 각 도구에 "자동설치" 버튼. **opencode = 추천·무키 기본**으로 시각 강조.
- **설치 진행 화면**: Claude 설치기(`OnboardingClaudeSetup`)와 동일 UX를 도구 파라미터로 재사용(설치 중→로그→프로브→완료/인증안내/실패폴백).
- **작업방 "실행 도구 없음" 상태**(`WorkRoom.tsx` `!anyDetected`): "opencode 무료로 바로 설치" 원클릭(키·결제 0) 우선 노출 + 다른 도구 자동설치 링크.

## 4. 엣지 / 위험
- **Node 미설치**(opencode-win, codex-mac npm 경로): 자동설치 전 감지 → 가이드 수동(또는 PowerShell/brew 대안 안내). Node 자동설치는 범위 밖.
- **opencode Windows**: 공식 curl 설치기는 WSL 필요 → 네이티브는 `npm i -g opencode-ai`(Node) 또는 GH 바이너리. 1차=npm, 실패 시 가이드 수동(GH 릴리스).
- **PATH 반영 지연**: 설치 직후 같은 프로세스 PATH 에 안 잡힐 수 있음 → 새 로그인 셸 프로브 + `augmented_vib_path` 로 확인(기존 Claude 프로브와 동일 대응).
- **권한/네트워크**: 설치는 네트워크·전역 설치 → 로그 노출 + 실패 시 폴백.
- **agy/codex 인증 미완**: 설치됐지만 미인증이면 작업방에서 실행 실패 → 상태에 "설치됨·인증 필요" 구분 표시.
- 설치는 시간 소요(수십초~분) → 진행 표시 필수(스피너+로그, Claude 설치기 패턴).

## 5. 테스트
- **순수/단위(우선)**: 레지스트리 조회(`toolInstaller(id)`), 플랫폼별 InstallCmd 선택, probe 이름 해석, 가이드-수동 폴백 판정(종료코드/프로브 실패 → manual), Node-필요 도구의 사전 게이트 로직. (rust + ts 순수 함수)
- **통합/수동**: macOS·Windows 각각에서 opencode(무키) 원클릭 설치 → 작업방에서 즉시 실행 / codex·agy 설치 → 인증 안내 표시 / 실패 시 수동 폴백 노출. (실기기 수동)

## 6. 범위 / 파일
- Create: `src-tauri/src/commands/tool_install.rs`(또는 `onboarding/tool_installer.rs`) + 레지스트리, 프론트 `src/lib/tools/installerRegistry.ts`(순수 메타·폴백 판정) + 설치 invoke 래퍼.
- Modify: `src-tauri/src/lib.rs`(커맨드 등록), `ToolSetupSelector`(자동설치 버튼), `OnboardingClaudeSetup` 패턴을 일반 설치 화면으로 재사용/추출, `WorkRoom.tsx` no-provider 상태.
- 무변경: Claude 기존 설치 플로(`onboarding/macos.rs`·`windows.rs`의 Claude 경로), 모델 실행부(`planning_persona.rs` 실행 자체).
- 단계화 제안: ①레지스트리+백엔드 설치 런타임(opencode부터) → ②설치 UI 일반화 + 작업방 연결 → ③codex·agy + 인증 안내 → ④가이드 수동 폴백 마감.
