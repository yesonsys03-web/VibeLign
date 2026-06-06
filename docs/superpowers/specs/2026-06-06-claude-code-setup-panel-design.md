# Claude Code 설치/관리 패널 복원 — 설계

날짜: 2026-06-06
브랜치: feat/vibelign-product-renew

## 배경 / 문제

현재 온보딩(슬림 redesign, 커밋 a4e0b33)은 "Claude Code도 자동으로 준비하기" **체크박스 + fire-and-forget** 방식이다. 체크 후 전송하면 짧은 "설치중" 화면만 보이고 곧장 기획방으로 이동해 **사용자가 설치 성공 여부를 확인할 수 없다.** 실제로 Windows 테스트 머신(git 설치됨)에서 설치 후에도 `claude`가 PATH에서 잡히지 않았는데, 원인을 눈으로 확인할 방법이 없다.

a4e0b33 이전 온보딩에는 버튼 + 라이브 로그창 + 상태별 액션 버튼 + 언인스톨이 모두 있었으나 redesign에서 제거됐다. 백엔드 명령(`start_native_install`, `add_claude_to_user_path`, `start_login_probe`, `retry_verification`, `uninstall_claude_code`, `get_onboarding_logs`, `listen onboarding_progress`)은 전부 그대로 남아 **고아(orphaned)** 상태다.

## 목표

설치를 **눈으로 확인·제어**할 수 있게, 옛 설치 UI를 포커스된 컴포넌트로 복원한다. 기획 흐름과 분리한다.

## 설계

### 컴포넌트
- 신규 `vibelign-gui/src/pages/onboarding/OnboardingClaudeSetup.tsx` — 설치/검증/PATH/로그인/재시도/언인스톨 + 라이브 로그창을 담당하는 단일 컴포넌트.
- `Onboarding.tsx` 는 입력창 아래 **"Claude Code 준비하기" 토글 버튼**만 추가해 이 패널을 펼친다.

### 패널 UI (모두 `OnboardingSnapshot` 기반)
1. 상태: `snapshot.headline` / `snapshot.detail`.
2. 액션 버튼: `snapshot.nextAction` 기반으로 노출.
   - `start_install` → "설치 시작" (`startNativeInstall("native-powershell")`)
   - `install_git` → "Git 설치" (외부 URL)
   - `retry` → "다시 검증" (`retryOnboardingVerification`)
   - `retry_with_cmd` → "CMD 방식으로 재시도" (`startNativeInstall("native-cmd")`)
   - `add_to_path` → "PATH 추가" (`addClaudeToUserPath`) — 자동 PATH 실패 시 폴백
   - `start_login` → "로그인" (`startOnboardingLoginProbe`)
   - `open_manual_steps` → "수동 안내 보기"
3. 라이브 터미널 로그창: 활성 단계에서 `getOnboardingLogs` 1초 폴링 + `listenOnboardingProgress` 진행 이벤트. `$`/`✓` 스타일. 옛 `terminal` CSS 클래스 재사용(없으면 최소 스타일 추가).
4. 언인스톨: **전체 1버튼** (`uninstallClaudeCode("all")`).

### 데이터 흐름
- 마운트 시 `getOnboardingSnapshot()` 로 현재 상태 로드.
- 액션 버튼 클릭 → 해당 커맨드 호출 → 반환 `OnboardingSnapshot` 으로 상태 갱신.
- `listenOnboardingProgress` 구독 → 진행 이벤트 도착 시 상태/로그 갱신 트리거.
- 활성 단계(`installing_native`/`installing_wsl`/`verifying_shells`/`probing_login`)면 1초 로그 폴링 + 패널 자동 펼침. 종료 상태면 폴링 중단.

### 기획 흐름과 분리
- 기존 `prepareClaudeCode` 체크박스, `prepareClaudeCodeIfRequested`, C 폴링 메시지 코드 **제거**.
- `handlePromptSubmit` 은 더 이상 설치를 트리거하지 않음 → 폴더+프롬프트 전송 시 기획방으로 이동(기존). 설치는 패널에서 명시적으로.
- `OnboardingInputBar` 에서 `prepareClaudeCode` 관련 props 제거.

### 백엔드 (변경 없음, 유지)
- A: Claude 설치의 git 게이트 제거.
- B: 설치 기본 경로 `native-powershell`.
- 자동 PATH: 설치 스레드에서 `path_not_configured` 감지 시 `add_to_user_path` 자동 호출. 실패 시 패널의 `add_to_path` 버튼이 폴백.

## 에러 처리
- 커맨드 호출 실패(reject) → 패널에 오류 라인 표시, 폴링 중단, 재시도 버튼 노출(`snapshot.nextAction`).
- `getOnboardingLogs` 실패 → 조용히 무시(다음 폴링에서 재시도).

## 테스트
- 신규 `OnboardingClaudeSetup.test.tsx`: (a) 버튼이 nextAction에 맞게 노출/호출, (b) 활성 단계에서 로그 폴링 표시, (c) 언인스톨 호출, (d) 종료 상태에서 폴링 중단.
- `Onboarding.pr2-start.test.tsx`: 제거된 체크박스/자동설치 관련 테스트 정리. 전송 시 `startNativeInstall` 이 호출되지 **않음**을 검증.

## 비목표 (YAGNI)
- native/wsl 분리 언인스톨 (전체 1버튼으로 충분).
- 로그 파일 영속화.
- 로그인 상태 완전 검증(login probe 결과 표시까지만).

## 미해결 (구현 중 확인)
- 옛 `terminal*` CSS 클래스가 현재 스타일시트에 남아있는지 → 없으면 패널 로컬 스타일로 최소 복원.
