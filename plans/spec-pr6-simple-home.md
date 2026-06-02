# PR 6 Spec: Simple Home

작성일: 2026-06-02
브랜치: `feat/vibelign-product-renew`
상위 문서: `VibeLign-코알못UX-통합기획안.md` §4-2, §12 PR 6

## 목적

기존 Home을 기능 카드 그리드가 아니라 초보자가 지금 안전한지와 다음 행동만 이해하는 상태 화면으로 바꾼다.

PR 6은 Home 표면 재구성만 담당한다. `patch`, `CodeSpeak`, `plan-structure` 실제 deprecation/hidden 처리는 PR 7에서 한다.

## 상위 결정

Home의 기본 표면은 3개 블록만 둔다.

```text
프로젝트 안전 상태
지금 할 일
되돌리기
```

기존 기능 카드는 삭제하지 않고 `고급 기능 보기` 뒤로 이동한다.

## 현재 코드 기준

| 사실 | 위치 |
|---|---|
| Home은 drag-sortable 카드 그리드 중심 | `vibelign-gui/src/pages/Home.tsx` |
| 기존 카드 렌더링 switch | `Home.tsx` `renderCard()` |
| PatchCard가 import/렌더 가능 | `Home.tsx` `PatchCard`, `case "patch"` |
| command manual은 `COMMANDS` 기반 | `vibelign-gui/src/lib/commands.ts` |
| command data는 `commandData.ts`, `commandData2.ts` | `vibelign-gui/src/lib/commandData*.ts` |

## 범위

### 포함

- Home 기본 화면을 3개 블록 중심으로 재구성
- 기존 drag-sortable 카드 그리드는 `고급 기능 보기` 뒤로 이동
- 초보 기본 화면에서 `PatchCard`, `AnchorCard`, `GuardCard`, `CodemapCard` 같은 기능별 카드 직접 노출 제거
- `guardResult`, `watchOn`, `checkpoint/history` 정보를 쉬운 말 상태로 요약
- Claude Code 준비 상태가 있으면 프로젝트 안전 상태에 작게 표시
- 기존 manual/detail view는 보존

### 제외

- `vib patch` CLI deprecation 문구 추가(PR 7)
- `plan-structure` hidden/deprecated 처리(PR 7)
- commandData에서 legacy 항목 문구 변경(PR 7)
- 자동 watch/anchor/guard 동작 변경(PR 8)
- 백업/복원 엔진 변경

## 화면 구조

```text
프로젝트 안전 상태
안전장치가 켜져 있어요
마지막 확인: 방금 전
Claude Code: 준비됨
[문제 확인하기]

지금 할 일
바로 AI 코딩해도 괜찮아요
또는
확인이 필요한 일이 1개 있어요
[확인하기]

되돌리기
최근 저장 지점: 5분 전 · 자동 저장됨
[이전 상태로 돌아가기]

고급 기능 보기
```

## 블록별 계약

### 프로젝트 안전 상태

표시할 수 있는 상태:

| 상태 | 문구 |
|---|---|
| 모두 정상 | `안전장치가 켜져 있어요` |
| 일부 실패 | `자동 안전장치 일부가 꺼져 있어요` |
| 확인 중 | `프로젝트 상태 확인 중...` |
| 알 수 없음 | `상태를 아직 확인하지 못했어요` |

내부 용어는 기본 화면에 노출하지 않는다.

- `watch` → `파일 변경 감시`
- `guard` → `안전 검사`
- `anchor` → `코드 북마크`
- `checkpoint` → `저장 지점`

### 지금 할 일

우선순위:

1. guard fail/warn이 있으면 그 1개만 표시
2. start/watch 일부 실패가 있으면 `다시 켜기`
3. 문제 없으면 `바로 AI 코딩해도 괜찮아요`

여러 문제가 있어도 초보 기본 화면에는 하나만 추천한다.

### 되돌리기

- 최근 checkpoint/history 정보를 쉬운 말로 표시
- 복원 action은 기존 backup/checkpoint flow로 연결
- 실제 복원 UX 변경은 하지 않는다

### 고급 기능 보기

열었을 때 기존 카드 그리드를 보여준다.

단, PR 6에서도 고급 영역의 `patch`는 "legacy/실험적" 배지 없이 그대로 두지 않는다. PR 7에서 문구를 최종화하므로, PR 6에서는 최소한 초보 기본 화면에서 제외한다.

## 금지어 계약

Home 기본 화면에는 다음이 보이면 실패다.

- `PatchCard`
- `vib patch`
- `CodeSpeak`
- `plan-structure`
- `target_anchor`
- `MCP`
- `rules`

예외:

- 사용자가 `고급 기능 보기`를 펼친 뒤
- manual detail 화면
- 개발자용 로그/상세

## 구현 메모

- 전체 `Home.tsx`를 재작성하지 않는다.
- 권장: 새 컴포넌트를 `vibelign-gui/src/components/home/`에 분리한다.

후보:

```text
SimpleHome.tsx
SafetyStatusPanel.tsx
NextActionPanel.tsx
RollbackPanel.tsx
AdvancedFeaturePanel.tsx
```

- `Home.tsx`는 state와 wiring을 유지하고, 기본 view에서 `SimpleHome`을 렌더한다.
- 기존 sortable grid는 `AdvancedFeaturePanel` 내부로 이동하거나 기존 렌더 블록을 조건부로 감싼다.
- `renderCard()`와 기존 card imports는 PR 6에서 삭제하지 않는다.
- "Claude Code: 준비됨" 표시는 온보딩 snapshot 등 **기존 Claude 상태 데이터 소스를 재사용**한다. 소스가 없으면 이 줄을 생략한다(없는 상태를 추측해 표시하지 않음).

## 자동 테스트

테스트 파일 후보:

```text
vibelign-gui/src/pages/__tests__/Home.simple.test.tsx
```

필수 테스트:

1. 기본 Home에 `프로젝트 안전 상태`, `지금 할 일`, `되돌리기`가 보인다.
2. 기본 Home에 `vib patch`, `CodeSpeak`, `plan-structure`, `target_anchor`가 보이지 않는다.
3. 기본 Home에 기능 카드 그리드가 먼저 렌더되지 않는다.
4. `고급 기능 보기` 클릭 후 기존 카드 영역에 접근 가능하다.
5. guard warn/fail이 있으면 `지금 할 일`에 1개 액션만 표시된다.
6. 최근 checkpoint가 없으면 되돌리기 블록이 `아직 저장 지점이 없어요`처럼 빈 상태를 표시한다.
7. 모바일 폭에서도 3개 블록이 겹치지 않는다.

## 수동 QA

### 시나리오 1: 정상 프로젝트

```text
프로젝트 열기 → Home 진입
```

통과 기준:

- 3개 블록만 먼저 보인다.
- 내부 명령어/카드 이름이 먼저 보이지 않는다.
- 다음 행동이 하나로 보인다.

### 시나리오 2: 고급 기능 열기

```text
고급 기능 보기 클릭
```

통과 기준:

- 기존 기능 접근이 사라지지 않는다.
- 기존 카드들이 초보 기본 화면보다 아래/뒤에 있다.

### 시나리오 3: guard warning 상태

```text
guardResult warn/fail 상태로 Home 렌더
```

통과 기준:

- `지금 할 일`에 가장 중요한 1개만 표시된다.
- raw error code보다 쉬운 설명이 먼저 보인다.

## 완료 정의

1. Home 기본 화면이 3개 블록 중심으로 재구성되었다.
2. 기존 카드 그리드는 고급 기능 뒤에서 접근 가능하다.
3. 초보 기본 화면에서 patch/CodeSpeak/plan-structure가 보이지 않는다.
4. 기존 manual/detail 기능은 유지된다.
5. 자동 테스트와 수동 QA가 통과한다.
