# 기획방 "카드 버튼" (A2) — 설계 명세

> 작성일: 2026-06-07
> 대상: VibeLign 기획방 — 카드 흐름(A)의 후속 refinement.
> 선행: A(카드 흐름) 구현 완료.

## 배경 — 왜

A를 라이브로 돌리고 기획방으로 A 자신을 검토하자, 클로이·미나가 독립적으로 같은 약점에
수렴했다(그리고 그 결정이 실제 카드로 잡혔다):

> **"이어가는 말 = confirm"은 가장 위험한 가정.** 사용자가 대화를 이어간다고 앞 카드에
> *동의*한 건 아니다. 부연일 수도, 화제 전환일 수도 있다. 그런데 LLM이 "이어감"을 confirm으로
> 추측하면 **동의한 적 없는 카드가 또렷하게 굳는 오분류**가 일상적으로 난다. 카드는 "내가
> 결정했다"는 신뢰의 표식인데, 멋대로 굳으면 신뢰가 깨진다.

모든 오분류의 뿌리는 **LLM이 상태 전환(confirm/reject/hold)을 추측**하는 것이다. 사용자가
직접 버튼을 누르면 그 추측이 사라진다 — 클릭은 0% 모호함.

## 한 줄 정의 — 역할을 가른다

**AI는 "감지"만, 사람은 "전환"을.** 추출 LLM은 결정을 보면 흐릿한 draft 카드를 **생성(add)만**
한다. **또렷해질지/비켜둘지/사라질지는 항상 사용자가 카드의 버튼**(동의·보류·빼기)으로 정한다.

## A로부터 바뀌는 것 (이 문서가 A를 supersede하는 지점)

| | A (현재) | A2 (이 문서) |
|---|---|---|
| confirm/reject/hold | LLM이 대화에서 추론 | **사람이 버튼으로** (LLM은 안 함) |
| 추출 루브릭 | add + confirm/reject/hold 규칙 | **add 전용** |
| "이어가면 자동 확정" | 채택(원본 카드 기획안) | **폐기** (오분류의 뿌리) |

> 원본 카드 기획안의 "사용자가 다음 입력으로 이어가면 또렷하게 확정"을 **의도적으로 폐기**한다.
> 클로이·미나·사용자 모두 자동 confirm이 위험하다는 데 합의했고, 그 대가로 동의 클릭 한 번을
> 치른다.

## 1. 상태 전환 명령 — `update_card` (Rust)

새 Tauri 명령. 카드 하나의 상태를 사용자 버튼 클릭으로 결정적으로 바꾼다.

```rust
// 요청 (camelCase)
UpdateCardRequest { project_dir, session_id, card_id, action }   // action: "confirm" | "hold" | "reject"

// 응답 (camelCase)
CardUpdateResponse { ok: bool, cards: Vec<Card>, error: Option<String> }
```

동작: `session_dir = planning_dir(project_dir)/session_id` → `read_cards` → action을 `CardOp`로
매핑(confirm→Confirm, hold→Hold, reject→Reject) → **기존 `apply_card_ops(cards, &[op], now)` 재사용**
→ `write_cards` → 갱신된 cards 반환. 알 수 없는 action·없는 card_id는 안전 처리(에러 또는 무변화).

`planning_chat_cards.rs`에 두고 `lib.rs`의 `invoke_handler` 목록(line 120 뒤)에 등록.

## 2. 추출 루브릭 단순화 — add 전용 (Rust)

`CARD_RUBRIC`에서 confirm/reject/hold 규칙과 JSON 예시를 제거하고 **add만** 남긴다:

- 결정에만 반응(인사·잡담·질문이면 빈 배열).
- 새 결정이 생기면 add.
- **이미 '현재 카드'에 있는 결정은 다시 add하지 않는다**(중복 방지 — 그래서 현재 카드는
  프롬프트에 계속 보여줌).
- **확정/거절/보류는 사용자가 버튼으로 하므로 추출기는 절대 내지 않는다.**

`parse_card_ops`/`apply_card_ops`는 그대로(전 연산 지원, 무해). 프롬프트만 add로 좁힌다.

## 3. 프론트엔드 — 카드 버튼

- **`PlanningCardsPanel`** — `draft`/`held` 카드 하단에 버튼: **[✓ 동의]**(→confirm) · **[⏸ 보류]**(→hold) · **[✕ 빼기]**(→reject). `confirmed` 카드는 버튼 없음(또렷, 완결).
  - 버튼 클릭 → `updateCard({projectDir, sessionId, cardId, action})` → 응답의 `cards`로 갱신.
  - 패널은 이제 `projectDir`, `sessionId`, `onCardsChange(cards)`를 props로 받는다.
- **`PlanningRoom`** — 패널에 `projectDir`, `result.sessionId`, `onCardsChange = (cards) => onResultChange({ ...result, cards })` 전달.
- **`lib/vib/planning.ts`** — `updateCard` invoke 래퍼. **`types.ts`** — `UpdateCardRequest`/`CardUpdateResponse`.

## 4. 데이터 흐름

```
[감지] 매 턴 → 추출 LLM(add 전용) → draft 카드가 cards.json·패널에 뜸
[전환] 사용자가 카드 버튼 클릭 → update_card → apply_card_ops 1연산 → cards.json → 패널 갱신
```

## 5. 컴포넌트 경계

- `update_card`(명령: 검증·읽기·apply·쓰기) · `apply_card_ops`(순수, 재사용) ·
  `PlanningCardsPanel`(렌더 + 버튼→명령) · `planning.ts updateCard`(invoke 래퍼).

## 6. 테스트

- **순수(기존):** `apply_card_ops`는 이미 confirm/hold/reject 단위테스트 보유 — `update_card`는
  그 위에 얹히므로 핵심 로직은 검증됨.
- **명령(선택):** `update_card`의 action→CardOp 매핑이 잘못된 action을 거부하는지 단위테스트.
- **라이브 수동:** ① 결정 턴 → draft 카드가 뜨고 **자동 confirm 안 됨**(단순 이어감엔 그대로),
  ② [동의] 클릭 → confirmed, ③ [빼기] 클릭 → 사라짐, ④ [보류] → held.

## 7. 안 만드는 것 (YAGNI)

순서/이름으로 카드 지목("두 번째 거 빼줘", 미나1) · draft 쌓임 정렬·오래된 draft 접힘(클로이2) ·
대화로 거절/확정(말 경로) — 전부 다음 조각. 이번엔 **버튼 일원화**만.

## 8. 메타 — 게이트 통과 자가점검

- **발동🟢** 버튼 클릭 → update_card / 매 턴 → 추출(add). **데이터🟢** cards.json(A) 재사용.
- **판정🟢** 전환은 사용자 클릭(모호함 0), 감지는 add 전용. **수용🟢** 라이브 4단계(§6).
- **엣지🟢** 없는 card_id/잘못된 action 안전 처리. **플랫폼⚪** 데스크톱.
