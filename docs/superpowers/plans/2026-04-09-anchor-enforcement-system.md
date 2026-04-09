# VibeLign 앵커 집행 시스템 기획안

> **상태:** 기획 단계 (구현 전)
> **목적:** 새 소스 파일에 앵커가 빠졌을 때 가능한 이른 시점에 자동 보정·경고·차단으로 회수하는 시스템

---

## 1. 문제 정의

### 현재 상황
- AGENTS.md에 "앵커를 삽입하라"는 규칙이 있음
- AI는 이 규칙을 무시해도 막을 수 없음
- `vib guard`는 사후 검증 → 이미 앵커 없는 파일이 여러 개 생긴 후에야 감지
- 실제 사례: 리팩토링 완료 후 새로 생성된 파일에 앵커가 하나도 없었음

### 목표
"AI가 규칙을 어기지 못하게 막는다" (불가능) 대신
**"AI가 규칙을 어기는 즉시 자동 교정된다"** (가능)

### 왜 100% 사전 강제가 불가능한가
앵커 이름은 코드 구조(클래스명, 함수명)에서 나온다.
코드를 쓰기 전에는 그 구조를 알 수 없으므로, 앵커를 미리 만들 수 없다.
→ **파일 작성 직후 즉시 자동 삽입이 현실적 최선**

---

## 2. 핵심 설계 원칙

- 기존 `anchor_tools.py`의 `insert_module_anchors()`를 최대한 재사용 — 새 앵커 생성 로직은 최소화
- AST 파싱으로 클래스/함수 감지 → 코드 구조에 맞는 앵커 이름 자동 생성
- 세 계층이 독립적으로 동작 → 하나가 없어도 나머지가 보완
- 기존 훅/가드/메타 상태 흐름과 충돌하지 않도록 통합 우선

---

## 3. 3단계 방어 계층

| 계층 | 대상 | 집행 시점 | 강도 |
|---|---|---|---|
| watch --auto-fix | **watch를 실행 중인 사용자** | 파일 저장 직후 (이벤트 기반) | 자동 교정 |
| 기존 pre-commit hook 확장 | git 사용자 | 커밋 직전 | 차단 |
| Claude Code PreToolUse | Claude Code 사용자 | Write 도구 호출 직전 | 경고 → 재작성 유도 |

---

## 4. 각 계층 설계

### 계층 1: watch --auto-fix (watch 실행 사용자)

watchdog은 이미 이벤트 기반 → 파일이 변경될 때만 동작, 부하 없음.

```
vib watch --auto-fix (백그라운드 실행)
    ↓
새 .py / .ts / .tsx / .js / .jsx 파일 감지
    ↓
insert_module_anchors(path) 자동 호출
    ↓
앵커 삽입 완료 → "[auto-fix] 앵커 삽입: filename.py" 출력
```

**설계 결정:**
- 소스 파일(.py, .ts 등)에만 적용, .json/.md는 건너뜀
- 앵커가 이미 있는 파일은 건너뜀 (중복 방지)
- 빈 파일/부분 저장 상태에서는 다음 저장 이벤트에서 재시도 가능해야 함
- 기존 `WatchConfig`에 `auto_fix: bool` 필드 추가

> 이 계층은 "모든 사용자"용이 아니라 **watch 프로세스를 실제로 켜 둔 사용자**용 자동 교정이다.

### 계층 2: 기존 pre-commit hook 확장 (git 사용자)

```
기존 hook 설치 경로 사용  ← 한 번만 실행
    ↓
.git/hooks/pre-commit 생성 (실행 권한 포함)
    ↓
이후 모든 git commit 시 자동 실행:
    vib secrets --staged
    vib guard --strict
    앵커 위반이 fail이면 커밋 차단
```

**설계 결정:**
- 신규 `vib install-hook`를 따로 만들기보다 기존 `git_hooks.py` / secrets hook 흐름에 앵커 검사를 통합
- 핵심은 `--exit-code` 플래그 추가가 아니라 **앵커 부재를 언제 fail로 볼지 guard 규칙 정의**
- 외부/사용자 커스텀 hook을 덮어쓰지 않는 기존 안전 정책 유지
- git 저장소 외부에서 실행 시 명확한 오류 메시지

### 계층 3: Claude Code PreToolUse 훅 (Claude Code 전용)

이 계층만 진짜 "사전 강제" — 디스크에 쓰기 전에 내용을 검사 가능.

기본 방향은 **수동 JSON 편집이 아니라 VibeLign이 프로젝트 로컬 Claude 설정에 hook을 자동 설치/복구**하는 것이다.
단, 사용자는 PreToolUse 기능 자체를 on/off 할 수 있어야 한다.

자동 설치/복구는 **`vib start` 및 관련 setup 명령 실행 시에만** 수행하며,
read-only 명령이나 단순 조회 명령에서는 수행하지 않는다.

```
AI가 Write 도구 호출 (파일 내용 포함)
    ↓
PreToolUse 훅 스크립트 실행
  stdin으로 Claude hook JSON 수신:
  {
    "tool_name": "Write",
    "tool_input": {
      "file_path": "/path/to/file.py",
      "content": "..."
    }, ...
  }
    ↓
vib pre-check 호출 (stdin JSON 그대로 전달)
  FILE_PATH=$(jq -r '.tool_input.file_path')
  FILE_CONTENT=$(jq -r '.tool_input.content')
    ↓
앵커 있음 → exit 0 (도구 호출 진행)
앵커 없음 → stderr에 경고 메시지 출력 + exit 2
    ↓
exit 2: Claude Code가 현재 도구 호출을 일단 중단하고
        stderr 메시지를 Claude에게 피드백으로 전달
        → Claude가 앵커 추가 후 재작성 시도 (한 번 막고 다시 쓰게 유도)
```

**설계 결정:**
- `vib pre-check` 새 명령어 추가 — stdin에서 Claude hook JSON 파싱 (filepath 인자 없음)
- 소스 파일만 검사, 비소스 파일은 항상 exit 0
- exit 2 → 현재 도구 호출 중단 + stderr 피드백 → Claude 재작성 (hard fail이 아니라 한 번 막고 다시 쓰게 유도)
- exit 0 시 stdout JSON으로 `permissionDecision: "allow"` 반환 가능 (선택)
- `.claude/settings.json`의 `hooks.PreToolUse`는 VibeLign이 자동 설치/복구 가능해야 함
- 사용자는 Claude PreToolUse 기능을 on/off로 제어할 수 있어야 함
- 예: `vib claude-hook enable`, `vib claude-hook disable`, `vib claude-hook status`
- `disable`는 hook 엔트리를 제거하는 것이 아니라, 설치된 hook의 enforcement 로직을 비활성화하는 의미로 사용
  - 구현: `.vibelign/config.json`의 `claude_hook_enabled: false` 플래그 설정
  - 훅 스크립트는 실행 시 이 값을 읽어 skip 처리 → 재활성화 시 별도 설치 불필요
- 자동 설치 시점: `vib start` 실행 시 hook 설치를 자동 제안 (prompt), `--no-hook`으로 스킵 가능
  - read-only 명령(`vib doctor`, `vib guard` 등)에서는 자동 설치하지 않음
  - `vib claude-hook enable`로 나중에 수동 설치도 지원
- 수동 JSON 편집은 고급 사용자용 fallback으로만 남김
- Claude 전용 통합이므로 전체 설계의 필수 전제가 아니라 선택적 강화 계층으로 취급

**통합 훅 설계 (앵커 집행 + 구조 계획 시스템 공유):**

`vib claude-hook`은 앵커 집행과 구조 계획 시스템 둘 다를 하나의 PreToolUse 훅으로 관리한다.
Write 도구 호출 시 훅이 순서대로 두 가지를 검사:

```
Write 도구 호출
    ↓
VibeLign PreToolUse 훅 (하나)
    ① plan-structure 세션 있는가? (구조 계획 시스템)
    ② 앵커 있는가? (앵커 집행 시스템)
    ↓
planning 검사는 Claude 컨텍스트에서 strict + enable 상태일 때만 gating,
앵커 검사는 경고를 보여주고 현재 Write를 한 번 막은 뒤 다시 쓰게 유도함
```

> 훅을 두 개로 분리하면 중복 실행·설치 복잡성·사용자 혼란이 생기므로 하나로 통합한다.
> 즉, Claude shared hook 안에서 **planning은 차단 가능**, **앵커는 한 번 막고 다시 쓰게 유도**로 역할을 나눈다.

**컨텍스트별 집행 강도:**

| 컨텍스트 | planning 강도 | 앵커 강도 |
|---|---|---|
| Claude Code PreToolUse | gating (차단) | 한 번 막고 다시 쓰게 유도 (exit 2 + stderr) |
| git pre-commit | strict (차단) | strict (차단) |
| vib guard (수동 실행) | non-strict 기본 (경고) | non-strict 기본 (경고) |

> `vib guard --strict`로 수동 실행 시 수동 guard 컨텍스트도 차단 동작으로 전환 가능.

**컨텍스트별 strict 해석 원칙:**

- strict는 전역 불리언 하나로 해석하지 않고, **실행 컨텍스트별로 따로 계산**한다
- 각 컨텍스트의 strict 여부 판단 위치:

| 컨텍스트 | strict 판단 근거 | 저장 위치 |
|---|---|---|
| git pre-commit | 기존 pre-commit hook 확장 경로 설치 여부 | `.git/hooks/pre-commit` 존재 여부 |
| Claude PreToolUse | `claude_hook_enabled` 값 | `.vibelign/config.json` |
| 수동 `vib guard` | `--strict` 플래그 유무 | CLI 인자 (저장 없음) |

- 따라서 git hook이 설치되어 있어도 Claude hook이 disable 상태면 Claude 컨텍스트는 non-strict로 동작할 수 있다

**Claude PreToolUse 결정표 (Phase 1 고정):**

| planning 상태 | 앵커 상태 | Claude hook enabled | exit code | 사용자/Claude가 받는 의미 |
|---|---|---|---|---|
| `planning_exempt` 또는 `pass` | 앵커 존재 | true | `0` | 그대로 진행 |
| `planning_exempt` 또는 `pass` | 앵커 없음 | true | `2` | 한 번 막고 다시 쓰게 유도 |
| `planning_required` | 앵커 존재/없음 | true | `2` | 먼저 `vib plan-structure` 하라고 차단 |
| `plan_exists_but_deviated` | 앵커 존재/없음 | true | `2` | plan 이탈을 알려주고 차단 |
| `fail` | 앵커 존재/없음 | true | `2` | 금지 규칙/상태 파손으로 차단 |
| 아무 상태든 | 아무 상태든 | false | `0` | hook은 설치돼 있어도 enforcement skip |

> Phase 1에서 Claude 경로는 `0` 또는 `2`만 사용한다. `1`은 의도된 정책 결과가 아니라 스크립트 오류로 간주한다.

**stderr 메시지 계약 (Claude hook):**

- planning 필요 시: `vib plan-structure를 먼저 실행하세요`
- plan 이탈 시: `현재 변경이 활성 구조 계획 범위를 벗어났습니다`
- 앵커 누락 시: `앵커가 없습니다. 앵커를 추가한 뒤 다시 시도하세요`
- 시스템 오류 시: stderr에 원인 출력 후 비정상 종료 (`1`) — Phase 1 정책 범위 밖

**`.claude/settings.json` merge 규칙 (Phase 1 고정):**

- 기존 파일이 있으면 **전체 덮어쓰기 금지**
- `hooks.PreToolUse` 배열만 merge 대상
- VibeLign이 관리하는 엔트리는 식별 가능한 marker 문자열을 포함해야 함
- 같은 marker의 엔트리가 이미 있으면 중복 추가하지 않고 update-in-place
- VibeLign 외 다른 hook 엔트리는 보존
- malformed JSON이면 자동 수정하지 않고 사용자에게 경고 후 수동 복구 경로 안내

**`.vibelign/config.json` 관련 필드 (Phase 1):**

```json
{
  "claude_hook_enabled": true,
  "small_fix_line_threshold": 30
}
```

- `claude_hook_enabled`: Claude PreToolUse enforcement on/off
- `small_fix_line_threshold`: 구조 계획 쪽 소규모 수정 보조 신호
- 필드 누락 시 기본값은 각각 `true`, `30`

---

## 5. 필요한 변경 파일

| 파일 | 변경 유형 | 내용 |
|---|---|---|
| `vibelign/core/watch_engine.py` | 수정 | `auto_fix` 플래그, `_handle_auto_fix()` 함수 추가 |
| `vibelign/commands/watch_cmd.py` | 수정 | `--auto-fix` CLI 옵션 추가 |
| `vibelign/core/git_hooks.py` | 수정 | 기존 pre-commit hook 흐름에 guard 검사 통합 |
| `vibelign/commands/vib_secrets_cmd.py` | 수정 | 기존 pre-commit hook 설치 UX에 앵커 검사 반영 |
| `vibelign/commands/vib_precheck_cmd.py` | 신규 | `vib pre-check` 명령어 |
| `vibelign/core/hook_setup.py` | 수정 | 실제 로직: settings.json 읽기/쓰기, 훅 설치/제거/상태 확인 |
| `vibelign/commands/vib_claude_hook_cmd.py` | 신규 | CLI 래퍼: enable/disable/status → hook_setup.py 호출 |
| `vibelign/commands/vib_guard_cmd.py` | 수정 | 앵커 위반 fail/warn 규칙 추가 |
| `vibelign/cli/vib_cli.py` | 수정 | 새 명령어 등록 |

---

## 6. 한계 (솔직하게)

| 계층 | 한계 |
|---|---|
| watch --auto-fix | 파일 저장 후 삽입 (수백 ms 지연) — 엄밀히 사전은 아님 |
| watch --auto-fix | watch를 켜지 않으면 동작하지 않음 |
| 기존 pre-commit hook 확장 | git을 쓰지 않는 사용자에게는 무효 |
| PreToolUse 훅 | Claude Code 전용 — Cursor, Codex, Gemini 미적용 |

**완전한 범용 사전 강제는 현재 기술로 불가능.**
세 계층의 조합이 현실적 최선.

---

## 7. 미해결 과제

1. **vib guard 앵커 검사 범위 — Phase 1 결정됨**
   - **Phase 1: 신규 파일만 대상** — 새로 생성된 소스 파일에 앵커가 없으면 fail/warn
   - 기존 파일의 앵커 손실은 Phase 1에서 차단하지 않는다.
     - 이유: 함수/클래스 의도적 삭제 시 앵커도 사라지는 게 정상 → false positive 과다 → git commit마다 차단되는 불편함 발생
     - AST diff 기반 손실 감지는 Phase 2 이후 과제
   - **fail 승격 기준 (Phase 1):** 신규 소스 파일 생성 + 앵커 0개 → strict 모드에서 fail, non-strict에서 warn

2. **Claude Code PreToolUse 입력 방식 — 확인 완료**
   - 환경변수 방식 없음. 훅 스크립트는 **stdin으로 Claude hook JSON을 수신**한다.
   - 파일 경로: `jq -r '.tool_input.file_path'`
   - 파일 내용: `jq -r '.tool_input.content'`
   - exit 0 = 진행, exit 2 = 차단 + stderr → Claude 피드백, exit 1 = 차단 안 됨(비의도적 동작)
   - `vib pre-check`는 filepath 인자 없이 stdin JSON을 직접 파싱하도록 설계

3. **watch auto-fix의 재진입/부분 저장 처리 — 해결됨**
   - **재진입 루프 방지**: `_handle_auto_fix()` 진입 시 `extract_anchors(path)`로 앵커 존재 여부를 먼저 확인한다. 앵커가 이미 있으면 즉시 skip — `insert_module_anchors()`를 호출하지 않으므로 파일이 수정되지 않고, 추가 watchdog 이벤트도 발생하지 않는다.
   - **빈 파일/부분 저장**: AST 파싱 실패(빈 파일, 문법 오류) 시 skip하고 다음 저장 이벤트를 기다린다. 강제 재시도 로직은 두지 않는다.

*이 기획안은 구현 전 검토용입니다. 확정 후 구현 계획(implementation plan)으로 전환.*
