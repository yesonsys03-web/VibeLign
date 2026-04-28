<!-- VibeLign Rules (vib export claude) -->
# VibeLign 규칙 (Claude Code용)

> 전체 규칙은 프로젝트 루트의 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 읽으세요.

> **반드시 맨 먼저**: 어떤 코드 탐색/수정 도구(Read·Grep·Glob)를 호출하기 전에 `.vibelign/project_map.json` 을 먼저 Read 하세요. 파일 구조·앵커 위치·카테고리를 머리에 올린 뒤 작업 시작. (규칙 8번의 운용 강제)

## 핵심 원칙

1. **가능한 가장 작은 패치를 적용하세요**
2. **요청한 파일만 수정하세요** — 연관 없는 파일은 절대 건드리지 마세요
3. **파일 전체를 재작성하지 마세요** — 명시적 요청이 없는 한 금지
4. **앵커 경계를 지키세요** — `ANCHOR: NAME_START` ~ `ANCHOR: NAME_END` 사이만 수정
5. **진입 파일을 작게 유지하세요** — main.py, index.js 등에 비즈니스 로직을 넣지 마세요
6. **새 파일을 임의로 생성하지 마세요** — 명시적 요청이 있을 때만 생성
7. **임포트 구조를 바꾸지 마세요** — 명시적 허락 없이 변경 금지
8. **코드맵을 먼저 읽으세요** — `.vibelign/project_map.json`에서 파일 구조와 앵커 위치를 확인

## 작업 흐름

```
vib doctor --strict        # 상태 확인
vib anchor                 # 안전 구역 설정
vib checkpoint "설명"      # 현재 상태 저장
# AI 작업 수행
vib guard --strict         # 결과 검증
vib checkpoint "완료"      # 또는 vib undo
```

## Handoff Narrative Discipline

work_memory.json 의 의미 칸은 *3 가지 경로* 로 채워집니다:

| 필드 | 자동 캡처 (보강) | 명시 호출 (핵심) |
|---|---|---|
| `decisions[]` | (없음 — 자동 캡처 안 함) | `transfer_set_decision(text)` |
| `verification[]` | guard_check 결과 | `transfer_set_verification(text)` |
| `relevant_files[]` | patch_apply target | `transfer_set_relevant(path, why)` |
| `recent_events[]` (kind=commit/checkpoint) | git post-commit / checkpoint_create | (호출 없음) |

`decisions[-1]` 이 PROJECT_CONTEXT.md 의 **active_intent** 가 됩니다. 그러므로
`transfer_set_decision` 은 **세션의 진짜 의사결정** 일 때만 호출하세요:

- 두 옵션 사이에서 하나를 선택했을 때 (이유 포함, 1줄)
- 의도가 바뀌었을 때 ("이제는 X 가 아니라 Y 를 추구")
- 작업의 핵심 목표가 정해졌을 때

**호출하지 말 것**:
- 단순 진행 보고 ("이제 Task 3 시작")
- commit 정렬 / 버전 bump 같은 메커니컬 작업
- 검증 결과 (그건 `transfer_set_verification`)

