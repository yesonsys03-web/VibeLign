# 기획방 "카드 흐름" (A, 첫 조각) — 설계 명세

> 작성일: 2026-06-07
> 대상: VibeLign 기획방(Planning Room)
> 선행: 마감 게이트(B)는 구현 완료. 이 문서는 후속 트랙 A의 첫 조각.

## 배경 — 왜, 그리고 게이트가 짚어준 구멍

원본 기획(`plans/기힉방을-조금-더-흥미로운-요소를-추가하고-싶은데-어떤게-좋을까.md`)은
"대화 중 결정이 카드로 쌓이는" 기능을 그렸지만, **행동만 적히고 메커니즘이 비어** 그대로는
구현 불가였다. 완성된 마감 게이트(B)를 이 기획에 실제로 돌린 결과(2026-06-07), 핵심 3개
요구사항이 전부 🔴로, 구멍은 **딱 두 종류**로 좁혀졌다:

- **데이터🔴** — 카드 스키마·저장 주체/위치 미정.
- **판정🔴** — (a) 무엇을 '결정'으로 감지하나, (b) 사용자 입력을 이어감/거절/보류로 분류, (c) 여러 카드 중 타깃 매핑.

이 문서는 그 구멍을 메운다.

## 한 줄 정의

기획 대화 중 **결정이 생기면 카드가 흐릿하게(draft) 뜨고**, 사용자가 다음 입력으로
이어가면 **또렷하게(confirmed)** 굳는다. 거절하면 사라지고, 보류하면 비켜둔다. 카드 추출은
**매 턴 뒤 전용 LLM 호출**이 **델타 연산**으로 수행한다.

## 확정된 핵심 결정 (브레인스토밍)

| 축 | 결정 |
|---|---|
| **추출 방식** | 매 턴 뒤 **전용 LLM 호출 1회**(게이트 패턴 재사용: LLM→JSON→파싱). 페르소나 응답에 섞지 않음. |
| **상태 모델** | **델타(stateful)** — LLM이 현재 카드(+ID)를 보고 이번 턴 *연산*만 출력. 확정된 카드는 사용자가 건드리기 전엔 안 바뀜. |
| **스코프** | 분류 코어: 생성/확정/거절/보류 + 멀티카드(한 장씩) + 기본 표시. |
| **애매 처리** | **no-op**(아무것도 안 함). 능동적 "이거 카드로 둘까요?" 묻기는 다음 조각. |

## 1. 카드 데이터 모델 — `데이터🔴` 메움

저장: `.vibelign/planning/<session>/cards.json` (`messages.json` 옆, 기존 저장 패턴 그대로).

```jsonc
// cards.json = { "cards": Card[] }
Card {
  id:        "card_<ms>_<n>",   // 안정적 ID — 델타가 참조
  title:     string,            // 제목
  summary:   string,            // 한 줄 설명
  reason:    string,            // 이유 (눌러서 펼침; 빈 문자열 허용)
  state:     "draft" | "held" | "confirmed",   // 흐릿 | 비켜둠 | 또렷
  created_at: string,           // ms 타임스탬프 문자열 (기존 메시지와 동일 규칙)
  updated_at: string
}
```

- **거절** = 목록에서 제거(영속 삭제).
- **접힘(서랍)** 상태는 이번 조각 제외(다음 조각).
- Rust 저장 구조체는 `#[serde(rename_all = "camelCase")]`로 TS에 노출(기존 응답 타입과 동일).

## 2. 추출 호출의 입출력 계약 — `판정🔴` 메움

**입력 (프롬프트):**
1. 추출 루브릭(아래 규칙).
2. **현재 카드 목록** — `id / title / state`만 (LLM이 기존 카드를 ID로 참조하도록).
3. **이번 턴에 추가된 메시지** — 사용자 입력 + 이번 턴 페르소나 응답(status=ok만).

**출력 (LLM→JSON, 게이트와 같은 추출/파싱 방식):**

```jsonc
{ "ops": [
  { "op": "add",     "title": "...", "summary": "...", "reason": "..." },  // 새 흐릿(draft) 카드
  { "op": "confirm", "id": "card_..." },   // draft|held → confirmed
  { "op": "reject",  "id": "card_..." },   // 제거
  { "op": "hold",    "id": "card_..." }    // → held
] }
```

**추출 루브릭에 박는 규칙:**
- **결정에만 반응** — 인사·잡담·질문엔 `ops` 빈 배열.
- **분류** — 사용자 입력이:
  - *이어가는 말* → 가장 최근 draft에 `confirm`
  - *거절*("빼줘","아니야") → 해당 draft `reject`
  - *보류*("잠깐","아직") → 해당 draft `hold`
  - *애매* → **아무 op 안 냄**(보수적: "명확히 앞으로 가겠다고 한 것만").
- **한 장씩** — 사용자 한마디는 **가장 최근 draft 한 장**에만 confirm/reject/hold. (멀티카드 타깃 `엣지🔴` 메움)
- **여러 결정** — 한 페르소나 응답에 결정이 여럿이면 `add`를 여럿.

**파싱 견고성(게이트와 동일):** 코드펜스 허용, JSON 추출 실패 → 빈 ops(카드 변화 없음, 가짜 생성 금지). 알 수 없는 `op`·존재하지 않는 `id`는 **무시**.

## 3. 적용 로직 (순수 함수)

`apply_card_ops(cards, ops) -> cards'`:
- `add` → 새 `Card{state: draft}` 추가(새 id 발급).
- `confirm` → 해당 id의 state를 `confirmed`로(draft|held에서만; 그 외 무시).
- `reject` → 해당 id 제거.
- `hold` → 해당 id의 state를 `held`로.
- 알 수 없는 op·없는 id → 무시. 결정적 → 단위테스트로 전부 커버.

> id 발급은 결정성을 위해 `apply` 바깥(호출부)에서 타임스탬프+인덱스로 생성해 `add` op에
> 주입한다. `apply_card_ops` 자체는 순수(외부 시계 의존 없음)로 유지해 테스트 가능하게 한다.

## 4. 어디서 도나 — 기존 패턴 재사용 + 공유 리팩터

`append_planning_chat_turn`(이미 페르소나를 돌리고 messages를 반환하는 Tauri 명령) 안,
페르소나 응답 **뒤에** 끼운다:

```
페르소나 응답 완료(messages 갱신)
 → cards.json 읽기 (없으면 빈 목록)
 → 추출 LLM 호출 (현재 카드 요약 + 이번 턴 메시지)    # 제공자 중립
 → ops JSON 파싱 → id 주입 → apply_card_ops → cards.json 저장
 → 응답에 cards 실어 반환
 → PlanningCardsPanel 렌더
```

**공유 리팩터 (DRY):** 게이트의 `judge_readiness`와 카드 추출은 둘 다 "활성 CLI를 골라
프롬프트 1회 실행 → stdout 텍스트"를 한다. 그 공통부를 헬퍼로 추출한다:

```rust
// planning_persona.rs (또는 새 planning_ai.rs)
pub(crate) fn run_active_ai(
    project_dir: &Path, messages: &[PlanningChatMessage], prompt: &str,
) -> Option<String>;   // CLI 선택(pick_judge_cli) + Command 실행 + stdout. 실패 시 None.
```

- `pick_judge_cli`를 `pub(crate)`로 승격(현재 readiness 모듈 내부 private).
- `judge_readiness`를 이 헬퍼 위로 재작성(동작 동일, 회귀 테스트로 보장).
- 카드 추출 모듈 `planning_chat_cards.rs`(신설)이 같은 헬퍼 사용.

## 5. 프론트엔드

- **신설 `PlanningCardsPanel.tsx`** — 카드를 상태별로 렌더:
  - `draft`(흐릿): 점선 테두리 + 반투명.
  - `confirmed`(또렷): 실선.
  - `held`(비켜둠): 흐릿 + 옆으로 치우침(예: 들여쓰기/저채도).
  - 제목·설명 표시, 이유는 클릭 시 펼침. 전환은 부드럽게(번쩍이지 않게 — 원 기획안 연출 약속).
- **수정 `PlanningRoom.tsx`** — 패널을 메시지 영역 옆/아래에 추가, 응답의 `cards`를 표시.
- **수정 `lib/vib/types.ts`** — `Card` 타입 + 응답(`PlanningChatSessionResponse`)에 `cards?` 필드.

## 6. 데이터 흐름 (요약)

```
사용자 입력 + 페르소나 응답
  → 카드 추출 LLM (현재 카드 + 이번 턴 메시지)
  → ops → apply_card_ops → cards.json
  → 응답.cards → PlanningCardsPanel (흐릿/또렷/비켜둠)
```

## 7. 컴포넌트 경계 (독립 테스트)

- **추출 루브릭**(상수) · **ops 파서**(텍스트→ops, 순수) · **`apply_card_ops`**(순수) ·
  **`run_active_ai`**(공유 LLM 헬퍼) · **카드 추출 오케스트레이션**(읽기·호출·적용·저장) ·
  **`PlanningCardsPanel`**(순수 렌더).
- 각 단위는 하나의 책임. 추출 LLM 호출만 부수효과(CLI), 나머지는 순수.

## 8. 코드가 앉을 자리

| 레이어 | 위치 | 책임 |
|---|---|---|
| Rust 신설 | `commands/planning_chat_cards.rs` | Card 타입, 추출 루브릭, ops 파서, `apply_card_ops`, 오케스트레이션 |
| Rust 수정 | `planning_persona.rs` (또는 `planning_ai.rs` 신설) | `run_active_ai` 헬퍼, `pick_judge_cli` pub 승격 |
| Rust 수정 | `planning_chat_readiness.rs` | `judge_readiness`를 `run_active_ai` 위로 재작성 |
| Rust 수정 | `planning_chat.rs` | `append_planning_chat_turn`에서 추출 호출 |
| Rust 수정 | `planning_chat_types.rs` / `planning_chat_store.rs` | 응답에 `cards` 필드(세션 저장은 cards.json 별도) |
| TS 신설 | `pages/planning/PlanningCardsPanel.tsx` | 카드 렌더 |
| TS 수정 | `PlanningRoom.tsx`, `lib/vib/types.ts` | 패널 배선 + 타입 |

## 9. 테스트

- **순수(단위):** `apply_card_ops`(add/confirm/reject/hold/없는id/미지op), ops 파서(정상·코드펜스·깨진JSON→빈ops·미지op무시).
- **프론트:** 카드 상태별 렌더 스타일, 이유 펼침.
- **LLM 추출:** fixture/수동 — 카드 대화를 넣어 카드가 결정 지점에 맺히는지(게이트 Task 13 방식).
- **회귀:** `run_active_ai` 리팩터 후 게이트 테스트(115개) 전부 통과 유지.

## 10. 수용 기준 — 게이트로 자기 검증 (닫는 고리)

구현 후 **이 카드 대화를 마감 게이트에 다시 통과**시킨다. 기대: 아까 🔴였던
**데이터·판정이 🟢로** 바뀐다(스키마·저장·분류가 이제 정의됐으므로). 더해, 원 기획안의
합격 기준 — *"이 대화를 흘려보냈을 때 카드가 몇 장·어느 타이밍에 맺히나"* — 를 사람이 눈으로
확인: "딱 그 순간에 떴네"면 통과, "왜 여기서 떴지?"가 나오면 추출 루브릭 재조정.

## 11. 안 만드는 것 (YAGNI — 다음 조각)

끊김 복구 UX(데이터는 cards.json로 이미 보존됨) · 첫 진입 예시카드·숙련자 구분 ·
접기(서랍) · 미완성 기능 안내 · **"애매하면 클로가 먼저 묻기"**(지금은 애매=no-op) ·
내보내기·직접편집·마감 게이트(B에서 별도).

## 12. 메타 — 이 명세가 게이트를 통과하는가

이 기능은 "행동만 적힌 명세"를 막으려고 만든 게이트가 🔴 줬던 바로 그 기획이다. 그래서 이
명세 스스로가 루브릭을 통과해야 한다:

- **발동🟢** — 매 턴 뒤 추출 호출이 트리거(§4).
- **데이터🟢** — `cards.json` Card 스키마·상태·위치(§1).
- **판정🟢** — 추출 루브릭의 결정 감지 + 4갈래 분류 + 한 장씩 규칙(§2).
- **수용🟢** — 게이트 재통과 + "몇 장·어느 타이밍" 검증(§10).
- **엣지🟢** — 파싱 실패→빈ops, 미지op/없는id 무시, 애매=no-op(§2·§3).
- **플랫폼⚪** — 데스크톱 Tauri 단일 흐름.
