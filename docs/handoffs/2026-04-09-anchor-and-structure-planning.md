# 핸드오프: 앵커 집행 + 구조 계획 시스템 기획안 완료

**날짜:** 2026-04-09  
**브랜치:** feat/vibelign-2.0-gui  
**상태:** 기획안 완료 — 구현 계획(implementation plan) 작성 단계로 이동 가능

---

## 이번 세션에서 한 일

두 개의 기획안을 작성하고 비판적 검토 후 전면 보강했습니다.

### 생성/수정된 파일

| 파일 | 상태 |
|---|---|
| `docs/superpowers/plans/2026-04-09-anchor-enforcement-system.md` | 기획 완료 |
| `docs/superpowers/plans/2026-04-09-structure-planning-system.md` | 기획 완료 |

---

## 기획안 핵심 내용

### 앵커 집행 시스템

**목적:** AI가 새 소스 파일 작성 시 앵커를 빠뜨리는 문제를 3단계 방어로 자동 교정

**3계층:**
1. `vib watch --auto-fix` — 파일 저장 직후 `insert_module_anchors()` 자동 호출
2. git pre-commit hook — `vib guard --strict` 연동, 앵커 없는 신규 파일 커밋 차단
3. Claude Code PreToolUse — `vib pre-check`가 stdin JSON 파싱, exit 2로 재작성 유도

**핵심 결정:**
- PreToolUse 입력: 환경변수 없음, **stdin JSON 파싱** (`jq -r '.tool_input.file_path'`)
- exit 2 = 도구 호출 차단 + stderr → Claude 피드백 → 재작성 유도 (hard fail 아님)
- auto-fix 재진입 루프 방지: `extract_anchors()` 선체크, 있으면 skip
- Phase 1 guard 범위: **신규 파일만** (기존 파일 앵커 손실은 false positive 너무 많아서 Phase 2로)
- strict는 컨텍스트별 독립 계산 (git=hook 설치 여부, Claude=config.json, guard=--strict 플래그)

### 구조 계획 시스템

**목적:** AI가 코딩 전에 `vib plan-structure`로 파일 배치 위치를 VibeLign으로부터 확정받는 시스템. 파일 비대화 방지.

**핵심 흐름:**
```
vib plan-structure "기능 설명"
→ 규칙 기반 4단계 알고리즘으로 위치 결정
→ .vibelign/plans/<id>.json 저장 + state.json에 active plan_id 기록
→ AI가 계획대로만 코딩
→ vib guard가 plan 준수 여부 검증
```

**위치 결정 4단계:**
1. 파일 크기 체크 (150줄 초과 → 신규 파일 필수)
2. project_map 메타데이터 (없으면 경고 후 3단계로 폴백)
3. 경로/폴더 패턴 매칭 (auth→core/auth*, cli→commands/ 등)
4. 앵커 가용성 (없음 또는 매칭 앵커 없음 → 신규 파일로 보수적 전환)

**vib guard 5가지 판정 상태:**
- `pass` — plan 있고 준수
- `planning_exempt` — 문서/테스트/config/소규모 단일파일 수정
- `planning_required` — 신규 production 파일 or multi-file 수정인데 plan 없음
- `plan_exists_but_deviated` — plan 있으나 실제 변경이 범위 이탈
- `fail` — forbidden 직접 위반 또는 plan 파손

**세션 잠금 만료:** 이벤트 기반 (커밋 완료 or 새 plan-structure 실행). 단일 활성 plan 정책.

**`vib plan-override "<이유>"`:** 계획이 틀렸을 때 탈출구. override 플래그 state.json에 기록, 다음 커밋 or 새 plan에서 자동 해제.

**컨텍스트별 집행 강도:**

| 컨텍스트 | planning | 앵커 |
|---|---|---|
| Claude Code PreToolUse | gating (차단) | 한 번 막고 재작성 유도 |
| git pre-commit | strict (차단) | strict (차단) |
| vib guard 수동 | non-strict (경고) | non-strict (경고) |

---

## 구현 대상 파일 목록

### 앵커 집행 시스템

| 파일 | 유형 |
|---|---|
| `vibelign/core/watch_engine.py` | 수정 — auto_fix 플래그, `_handle_auto_fix()` |
| `vibelign/commands/watch_cmd.py` | 수정 — `--auto-fix` CLI |
| `vibelign/core/git_hooks.py` | 수정 — guard 검사 통합 |
| `vibelign/commands/vib_precheck_cmd.py` | **신규** — `vib pre-check` (stdin JSON 파싱) |
| `vibelign/core/hook_setup.py` | 수정 — settings.json 읽기/쓰기, 훅 설치/복구 |
| `vibelign/commands/vib_claude_hook_cmd.py` | **신규** — enable/disable/status CLI 래퍼 |
| `vibelign/commands/vib_guard_cmd.py` | 수정 — 앵커 위반 fail/warn 규칙 |
| `vibelign/cli/vib_cli.py` | 수정 — 새 명령어 등록 |

### 구조 계획 시스템 (앵커와 공유 파일 포함)

| 파일 | 유형 |
|---|---|
| `vibelign/commands/vib_plan_structure_cmd.py` | **신규** |
| `vibelign/core/structure_planner.py` | **신규** — 4단계 위치 결정 알고리즘 |
| `vibelign/core/meta_paths.py` | 수정 — plans 경로 추가 |
| `vibelign/mcp/mcp_state_store.py` | 수정 — planning state 저장/조회 |
| `vibelign/commands/vib_guard_cmd.py` | 수정 — planning 판정 추가 (앵커와 동일 파일) |
| `vibelign/core/hook_setup.py` | 수정 — 통합 PreToolUse 훅 (앵커와 공유) |
| `vibelign/commands/vib_claude_hook_cmd.py` | 신규 (앵커와 공유) |
| `vibelign/cli/vib_cli.py` | 수정 — 새 명령어 등록 |
| `AGENTS.md` | 수정 — 구조 계획 필수 규칙 추가 |

**권장 구현 순서 (구조 계획):** Ticket 1→2→3→4→5→6→7→10→8→9

---

## 다음 세션에서 할 일

두 기획안을 바탕으로 **구현 계획(implementation plan)** 작성.
- 기획안을 읽고 Ticket 단위로 TDD 기반 상세 구현 스텝 작성
- 두 시스템이 공유하는 파일(`hook_setup.py`, `vib_claude_hook_cmd.py`, `vib_guard_cmd.py`)의 인터페이스를 먼저 확정
- `superpowers:writing-plans` 스킬 사용 권장

기획안 파일 경로:
- `docs/superpowers/plans/2026-04-09-anchor-enforcement-system.md`
- `docs/superpowers/plans/2026-04-09-structure-planning-system.md`
