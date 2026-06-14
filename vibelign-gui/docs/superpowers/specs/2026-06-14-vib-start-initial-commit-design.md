# vib start 초기 커밋 + stale 가이드 오버라이드 정리 — 설계 스펙

- 날짜: 2026-06-14
- 대상: `vibelign/commands/vib_start_cmd.py` (A, Python CLI), `vibelign-gui/src/lib/nav/guide.ts` (B, GUI)
- 상태: 설계 확정 대기(사용자 리뷰)

## 1. 배경 / 문제

가이드의 진행 판정(`changedFileCount`)은 git diff 기반인데, **`vib start`가 `git init`만 하고 초기 커밋을 안 만든다.** 그래서 신규 프로젝트는 "커밋 0개 = 모든 파일 untracked" 상태로 시작하고, **이미 untracked인 파일을 수정해도 git 상태가 그대로라 변경으로 안 잡혀** `changedFileCount`가 0이 된다. 결과:
- 5️⃣ 결과 검증 사이클이 진행되지 않음(`inferStep`은 `changedFileCount > 0`에서만 5/6 계산).
- 과거에 생긴 가이드 단계 **오버라이드가 inferred(4)에 고정**되어 "5단계"가 계속 표시됨(혼란).

실제 사례: 알람앱(커밋 0개) — 재스킨을 했는데 `changedFileCount: 0`, 상태확인을 눌러도 6으로 못 감. 근본 원인은 "커밋 0개". (`vib start`가 init만 하므로 **모든 초보 신규 프로젝트가 이 상태로 시작**.)

## 2. 목표 / 비목표

**목표**
- **A**: `vib start` 시 모든 프로젝트가 **git 베이스라인(초기 커밋 1개)** 을 갖게 한다 → 이후 in-place 수정이 "modified"로 추적되어 `changedFileCount`가 정상 작동.
- **B**: 변경이 없는데(=inferred 4) **검증/저장 단계(5/6) 오버라이드가 남아있지 않게** 정리.
- 커밋 0개인 기존 repo(예: 알람앱류)도 초기 커밋을 받게 한다.
- Windows/macOS 모두 동작.

**비목표**
- 변경집합 카운팅 코어(`countChangesSinceBaseline`)를 "커밋 0개에서 in-place 수정 세기"로 바꾸는 것 — A가 베이스라인을 만들어 불필요. (이미 만들어진 무커밋 프로젝트는 A의 "기존 무커밋 repo도 커밋" 분기로 흡수.)
- git 사용자 전역 설정 변경.
- 기존 커밋이 있는 repo의 히스토리 변경.

## 3. 설계

### A — `vib start` 초기 커밋 (`vib_start_cmd.py`)

**A-1. gitignore 기본값 확장** — `_ensure_gitignore_entry`가 추가하는 라인에 `node_modules/`·`.DS_Store` 포함(초기 커밋이 생성물·OS cruft를 안 담게). `.vibelign` 하위 무시는 그대로. (Python 프로젝트엔 node_modules가 없어도 무해.)

**A-2. 신규 `_ensure_initial_commit(root) -> bool`**:
- git 실행파일 없으면 no-op(False).
- **커밋이 이미 있으면 skip**: `git rev-parse --verify HEAD` 성공 시 return(기존 히스토리 불변).
- 없으면(0 커밋): `git add -A` → `git commit -m "chore: 초기 베이스라인 (VibeLign)"`.
  - **사용자 identity 미설정 대비**: `git -c user.name=VibeLign -c user.email=vibelign@local commit ...` (전역 설정 미변경, 1회 한정).
  - **훅 간섭 차단**: `--no-verify`(베이스라인은 비밀스캔 불필요 + 훅 오류로 베이스라인 실패 방지). 또한 호출 순서상 훅 설치 **이전**에 실행.
  - **커밋할 게 없으면**(add 후 staged 0) skip(빈 repo 방어).
  - 모든 subprocess는 기존 `_find_git_exe()` + `WINDOWS_SUBPROCESS_FLAGS` 패턴 재사용.
- 실패는 조용히 False(시작 자체를 막지 않음) + 경고 1줄.

**A-3. 호출 위치**: `vib start` 흐름에서 `git_active`가 true가 된 직후(새 init이든 기존 .git이든) + `_ensure_gitignore_entry` 적용 후, **`install_pre_commit_secret_hook`/`install_post_commit_record_hook` 설치 이전**에 `_ensure_initial_commit(root)` 호출. (훅 전에 커밋 → 훅 간섭 0.) 성공 시 `clack_success("초기 베이스라인 커밋을 만들었어요")`.

### B — stale 검증 오버라이드 정리 (`guide.ts`)

현재 `resolveOverride`: `override.baseInferred === inferred`면 `override.step` 반환. 변경이 사라져 inferred가 4로 돌아와도 `{step:5, baseInferred:4}` 오버라이드가 4와 일치해 **5가 계속 표시**됨.

**수정**: 검증/저장 단계(5·6) 오버라이드는 **검증할 변경이 있을 때만**(inferred ≥ 5) 유효. 변경이 없으면(inferred < 5 = 4) 폐기하고 inferred 반환:
```ts
export function resolveOverride(override, inferred) {
  if (!override) return inferred;
  // 5️⃣/6️⃣(검증·저장)는 검증할 변경이 있을 때만 의미 — 변경 없음(4)으로 떨어지면 stale 오버라이드 폐기.
  if (override.step >= 5 && inferred < 5) return inferred;
  if (override.baseInferred === inferred) return override.step;
  return inferred;
}
```
이전 단계(2·3·4) 오버라이드 동작은 불변 — 사용자 수동 전방 이동은 그대로 유지.

## 4. 엣지 / 위험
- git 미설치 → A no-op(기존 경고 유지).
- 기존 커밋 있는 repo → A skip(불변).
- user.name/email 없음 → `-c`로 1회 주입(전역 무변경).
- pre-commit 비밀 훅 false-positive → `--no-verify` + 훅 설치 전 실행으로 회피.
- 빈 디렉터리(staged 0) → skip.
- A 적용 후에도 **이미 떠 있는 GUI의 stale 오버라이드**는 B가 처리(혹은 프로젝트 재진입 시 리셋).
- Windows: `_find_git_exe`(여러 Program Files 경로) + `WINDOWS_SUBPROCESS_FLAGS` 재사용 → 콘솔 안 뜸·경로 해석 OK.

## 5. 테스트
- **A (pytest)**: 임시 repo로 `_ensure_initial_commit` — (a) 커밋0+파일있음 → 커밋 1개 생성, (b) 기존 커밋 → skip(히스토리 불변), (c) git없음 → False no-op, (d) user.identity 미설정 환경 → `-c` fallback으로 커밋 성공. `_ensure_gitignore_entry`가 node_modules/.DS_Store 포함.
- **B (vitest)**: `resolveOverride` — (a) {5,base:4}+inferred4 → 4(폐기), (b) {6,base:5}+inferred4 → 4, (c) {5,base:5}+inferred5 → 5(유효), (d) {4,base:3}+inferred3 → 4(전방 이동 유지).
- **통합/수동**: 새 임시 프로젝트에 `vib start` → `git rev-list --count HEAD`==1 확인 → 소스 수정 → GUI에서 changedFileCount>0·5→6 진행. (Windows는 코드 리뷰로 대체, 실기기 수동은 사용자.)

## 6. 범위 / 파일
- Modify `vibelign/commands/vib_start_cmd.py` — gitignore 라인 상수 추가, `_ensure_initial_commit`, 호출부.
- Modify `vibelign-gui/src/lib/nav/guide.ts` — `resolveOverride` 1조건 추가.
- Tests: vib start용 pytest(기존 테스트 위치 따름), `guide.test.ts`에 resolveOverride 케이스 추가.
- 무변경: 변경집합 코어, 가이드 inferStep, git 훅 로직.
