# 기획방 "마감 게이트 (Readiness Gate)" — 설계 명세

> 작성일: 2026-06-07
> 대상: VibeLign 기획방(Planning Room)
> 목적: 기획방이 **자기 출력의 구현 가능성을 스스로 책임지게** 만든다.

## 배경 — 왜 만드나

기획방의 가치 제안은 **"기획안 → VibeLign MCP → LLM이 바로 구현"**이다. 그런데 현재
구조에는 산출물이 *실제로 구현 가능한지*를 판정하는 단계가 없다. 한 검증 사례
(`plans/기힉방을-조금-더-흥미로운-요소를-추가하고-싶은데-어떤게-좋을까.md`)에서 이 공백이
드러났다:

- 대화는 **행동(behavior)에는 빈틈이 없었으나** — 그 행동을 굴릴 **메커니즘·데이터 모델이
  통째로 비어 있었다.** ("결정이 생기면 카드가 뜬다"는 있지만 *무엇이 '결정'을 감지하나*,
  *카드는 어디에 저장되나*, *입력을 어떻게 이어감/거절/보류로 가르나*가 전부 미정.)
- 저장된 `.md`는 전사(transcript) + 결정적 템플릿 폴백이라, 상단·하단에
  `아직 명시적으로 결정되지 않았습니다` 같은 문구가 **닫힌 대화와 모순**된 채 박혔다.
- 검토자 페르소나(지오)는 제공자(codex) 미설치로 죽어 있었고, 살아있었어도 현재 구조로는
  "이거 어떻게 만들지"를 겨냥하지 않았을 것이다.

게이트가 있었다면 "발동·데이터·판정 셋이 비었으니 못 넘겨요"를 정직하게 잡았을 것이다.
그 정직함이 곧 사용자 신뢰다 — 도구가 "준비됐어요!"라고 거짓 안심을 주지 않는 것.

## 한 줄 정의

저장하는 순간, 합의된 기획을 **루브릭으로 훑어 요구사항별 🟢/🔴를 매기고**, 그 판정을
**문서 맨 위와 GUI에 정직하게** 박는다. 핵심 항목에 🔴가 있으면 "작업 시작"에서 한 번
확인을 거는 **약한 블록**을 둔다.

## 핵심 결정 (확정됨)

| 축 | 결정 |
|---|---|
| **언제** | 저장 직전 게이트가 뼈대. 대화 중 라이브 점검은 가볍게(프롬프트 한 줄). |
| **강도** | 정직한 도장이 기본(저장은 항상 됨). 핵심 🔴가 있으면 "작업 시작"에 확인 1회. |
| **무엇** | 보편 루브릭 5개 + 조건부 1개. 조건부는 무관하면 🔴이 아니라 회색 N/A. |
| **누가 판정** | 사용자가 켜둔 활성 AI로. 제공자 중립. 아무것도 없으면 "판정 못 함"(가짜 초록 금지). |

## 1. 루브릭 (기능의 심장)

판정 LLM은 합의된 기획을 **개별 요구사항으로 분해**한 뒤, 각 요구사항을 다음으로 채점한다.

| # | 항목 | 묻는 것 | 종류 |
|---|---|---|---|
| 1 | 발동 Trigger | 무엇이 이 동작을 시작시키나? (감지/판정이 정의됐나) | 보편 |
| 2 | 데이터 Data | 무엇이 저장되고 어디에? (필드·상태값·저장 위치) | 보편 |
| 3 | 판정 Logic | 입력/상황을 무엇이 어떻게 가르나? | 보편 |
| 4 | 수용 Acceptance | "됐다"를 어떻게 확인하나? | 보편 |
| 5 | 엣지·실패 Edge | 잘못될 수 있는 순간 (끊김·빈 상태·동시 입력 등) | 보편 |
| 6 | 플랫폼 Platform | 다중 타깃 차이 (데스크톱 맥/윈, iOS/안드 등) | **조건부** |

**조건부 항목 원칙:** 판정 LLM은 *먼저 "이 항목이 이 프로젝트에 해당되나"를 판단*한다.
무관하면(예: 단일 타깃 웹앱에 플랫폼 차이) 🔴이 아니라 **회색 N/A**로 끄고 넘어간다.
→ 기획방은 범용 도구이므로 VibeLign 고유 관심사(맥/윈)를 모든 기획에 강요하지 않는다.

**각 체크의 판정값:** `🟢 충족` / `🔴 구멍` / `⚪ 해당 없음`. 🔴에는 **한 줄 이유**가 붙는다.

**핵심(core) 요구사항:** 판정 LLM이 각 요구사항을 core/non-core로 표시한다. 약한 블록은
**core 요구사항의 🔴**에만 발동한다(사소한 항목의 🔴로 작업 시작을 막지 않는다).

## 2. 흐름 (data flow)

```
대화 → [저장 클릭]
  → judge_readiness(대화 전체)        # 활성 AI 1회 호출: 요구사항 분해 + 루브릭 채점
  → ReadinessReport (구조화 JSON)
  → 마크다운 합성 (판정을 문서 맨 위에)  # 기존 template 모순 자리를 대체
  → .md 저장 + report를 세션에 보관
  → GUI: ReadinessPanel 렌더
  → [작업 시작] → core 🔴 있으면 "N개는 구현 도구가 임의로 채워요. 넘기시겠어요?" 확인 1회
```

## 3. 판정 실행 — 제공자 중립

페르소나는 제공자별로 하드와이어돼 있다(클로이=`claude -p`, 지오=`codex exec`,
미나=`agy -p`). 사용자마다 켜둔 도구가 다르므로(클로드코드만, 코덱스만 …), 판정은 한
제공자에 묶지 않는다.

- 판정 LLM은 페르소나의 **CLI 해석 메커니즘(`find_executable` + `augmented_vib_path`)을
  그대로 재사용**해, claude / codex / agy 중 **실제로 해석되는(설치·활성) 도구**로 돌린다.
- **우선순위:** 이 세션에서 실제로 응답에 성공한 페르소나의 도구 → 없으면 사용 가능한 첫 도구.
- 루브릭 프롬프트는 **제공자 중립**(특정 CLI 가정 없음). 출력은 구조화 JSON을 요구한다.

### AI가 하나도 없을 때 (지오처럼)

claude/codex/agy 중 하나도 해석되지 않으면 → **가짜 초록 대신 "판정 못 함"** 상태.
- 저장 자체는 정상 진행된다.
- ReadinessReport는 `status: "unavailable"`로 표기되고, 문서/패널에 "구현 준비 상태:
  확인 못 함 (활성 AI 없음)"으로 정직하게 표시된다.
- 약한 블록은 발동하지 않는다(판정이 없으므로 막을 근거도 없음).

## 4. 판정 LLM 입출력 계약

**입력:** 전체 대화(`PlanningChatMessage[]`) + 루브릭 지시 프롬프트.

**출력:** LLM이 아래 JSON을 반환하도록 프롬프트로 강제. Rust가 파싱한다.

```jsonc
{
  "requirements": [
    {
      "title": "카드 발동",
      "summary": "결정이 생기면 카드가 흐릿하게 뜬다",
      "core": true,
      "checks": {
        "trigger":    { "verdict": "red",  "note": "'결정 감지'의 방법이 미정" },
        "data":       { "verdict": "red",  "note": "카드 필드·저장 위치 미정" },
        "logic":      { "verdict": "red",  "note": "이어감/거절/보류 분류 방법 미정" },
        "acceptance": { "verdict": "green", "note": "" },
        "edge":       { "verdict": "green", "note": "" },
        "platform":   { "verdict": "na",   "note": "단일 타깃 데스크톱 내부 기능" }
      }
    }
  ]
}
```

**파싱 견고성:** LLM 출력에서 JSON 블록을 추출(코드펜스 허용)하고, 파싱 실패 시 →
`status: "unavailable"` 폴백(가짜 초록 금지). verdict 허용값은 `green|red|na`만,
그 외 값은 보수적으로 `red`로 강등(불확실하면 통과시키지 않는다).

## 5. 데이터 모델

```rust
struct ReadinessReport {
    status: ReadinessStatus,          // judged | unavailable
    requirements: Vec<RequirementReadiness>,
}
struct RequirementReadiness {
    title: String,
    summary: String,
    core: bool,
    checks: ReadinessChecks,          // 6개 항목: trigger,data,logic,acceptance,edge,platform
}
struct ReadinessCheck { verdict: Verdict, note: String }  // Verdict = Green|Red|Na
```

- 세션 저장소(`StoredPlanningChatSession`)에 `readiness: Option<ReadinessReport>` 추가.
- 응답 타입(`PlanningChatSessionResponse`)에 `readiness` 직렬화(camelCase)로 노출.

### 파생 지표 (순수 함수, TS·Rust 양쪽에서 동일 규칙)

- `greenCount` / `redCount` / `naCount`
- `coreRedCount` = core 요구사항 중 🔴가 하나라도 있는 항목 수
- `canStartWork` = `status == judged && coreRedCount == 0` (false면 약한 블록)

## 6. 산출물 문서 개편 (모순 제거)

현재 `synthesize_planning_markdown`은 결정적 템플릿 폴백을 찍는다(상단 `대상 사용자`/`핵심 문제`,
하단 `제외할 것: 아직 결정되지 않았습니다`/`아직 결정이 필요한 질문`). report가 있을 때 이
모순 자리를 **판정 헤더**로 교체한다.

```
# <제목>

## 구현 준비 상태: 🟢 7 / 🔴 2  (핵심 구멍 2개)
> 이 기획안은 구현 도구가 그대로 읽는 지시서입니다.
> 🔴 항목은 명세에 없어 구현 도구가 임의로 채웁니다.
- 🔴 [핵심] 카드 발동 — '결정 감지'의 방법이 미정
- 🔴 [핵심] 카드 저장 — 필드·저장 위치 미정

## 요구사항별 명세
### 카드 발동  (발동🔴 데이터🔴 판정🔴 수용🟢 엣지🟢 플랫폼⚪)
...

## 기획방 대화 정리
<기존 전사 유지>
```

- `status == unavailable`이면 헤더는 `## 구현 준비 상태: 확인 못 함 (활성 AI 없음)`.
- report가 없을 때(기존 경로)는 **현재 동작 유지**(하위 호환).

## 7. 라이브(A) 가벼운 터치 — 코드 거의 없음

새 페르소나/새 단계를 만들지 않는다. **클로이(설계자) 시스템 프롬프트에 습관 한 줄만 추가**:

> "결정이 설 때, 가끔 *'이건 뭐가 발동시키고 어디에 저장되죠?'* 를 한 번 되물어라
> (매 턴마다 X — 대화 흐름을 깨지 않게)."

→ 대화의 "쓰는 맛"을 유지하면서, 막판 게이트가 잡을 구멍을 미리 줄인다.
(`build_persona_prompt`의 chloe 규칙 문자열에만 추가.)

## 8. 코드가 앉을 자리 (기존 패턴 준수)

| 레이어 | 위치 | 책임 |
|---|---|---|
| Rust 신설 | `commands/planning_chat_readiness.rs` | 루브릭 프롬프트 상수, 활성 AI 판정 호출, JSON 파싱 → `ReadinessReport` |
| Rust 수정 | `planning_chat_synthesis.rs` (저장 경로) | 저장 직전 `judge_readiness` 호출, report를 세션에 보관 |
| Rust 수정 | `planning_chat_markdown.rs` | report 있으면 판정 헤더 출력 (순수 함수) |
| Rust 수정 | `planning_chat_types.rs` / `planning_chat_store.rs` | `readiness` 필드 추가 |
| Rust 재사용 | `planning_persona.rs`의 `find_executable`/`augmented_vib_path` | 판정용 CLI 해석 |
| TS 신설 | `pages/planning/PlanningReadinessPanel.tsx` | report → 🟢/🔴 패널 (순수 렌더) |
| TS 신설 | `pages/planning/PlanningReadiness.ts` | 파생 지표 순수 함수(`canStartWork` 등) |
| TS 수정 | `PlanningRoom.tsx` | `ReadinessPanel` 렌더, `onStartWork`에 약한 블록 |
| TS 수정 | `lib/vib.ts` | `readiness` 타입 노출 |

## 9. 컴포넌트 경계 (독립 테스트 가능)

각 단위는 하나의 책임만 가지며 인터페이스로 소통한다.

- **루브릭 프롬프트** (순수 상수) — 입력 대화, 출력 JSON 지시.
- **judge** (LLM 호출 → report) — 부수효과는 CLI 호출 하나. fixture로 검증.
- **readiness 파서** (텍스트 → `ReadinessReport`, 순수) — JSON 추출·강등 규칙.
- **readiness markdown** (report → 헤더 문자열, 순수).
- **파생 지표** (report → 카운트/`canStartWork`, 순수, TS·Rust 동일).
- **ReadinessPanel** (report → UI, 순수 렌더).

## 10. 검증 — 닫는 고리

judge는 LLM이라 결정적 단위테스트가 어렵다. 대신 **이 카드 대화를 fixture로** 써서
"발동·데이터·판정이 🔴, 수용이 🟢, 플랫폼이 ⚪로 잡히나"를 통합 검증한다 — 카드 기획방이
*스스로 제안했던 첫 검증 시나리오*("이 대화 자체")가 그대로 이 게이트의 합격 기준이 된다.

순수 조각은 일반 단위테스트:
- 파서: 정상 JSON / 코드펜스 감싼 JSON / 깨진 JSON→unavailable / 미지 verdict→red 강등.
- 파생 지표: coreRedCount, canStartWork 경계.
- markdown 헤더: judged / unavailable / report 없음(하위 호환).

## 11. 안 만드는 것 (YAGNI)

- 구멍 **자동 수정** ✗ (게이트는 진단만; 채우는 건 사용자/대화).
- 카드 6단계 흐름·내보내기·직접 편집 ✗ (별도 트랙).
- 판정 결과 **히스토리/추적** ✗ (최신 report 1개만 보관).
- 루브릭 사용자 커스터마이즈 ✗ (고정 6항목으로 시작).

## 12. 위험과 완화

| 위험 | 완화 |
|---|---|
| LLM 판정이 멀쩡한 항목을 🔴(false-red) | 기본이 "정직한 도장"(하드 블록 아님) → 사용자가 무시하고 진행 가능. 약한 블록은 core 🔴에만. |
| 판정 호출 지연(저장이 느려짐) | 저장과 판정을 분리 표기 가능(우선 동기 호출로 시작, 느리면 비동기 후속 과제). |
| JSON 파싱 실패 | unavailable 폴백(가짜 초록 금지) + verdict 보수적 강등. |
| 제공자별 출력 편차 | 프롬프트에 JSON 스키마 명시 + 코드펜스 허용 파싱 + 강등 규칙. |

## 13. 메타 — 이 명세 자체가 게이트를 통과하는가

이 기능은 "behavior만 적히고 mechanism이 빈" 명세를 막으려는 것이므로, 이 명세 스스로가
루브릭을 통과해야 한다:

- **발동🟢** — 저장 클릭이 판정을 트리거(§2).
- **데이터🟢** — `ReadinessReport` 스키마 정의(§5).
- **판정🟢** — verdict green/red/na 규칙 + 강등(§4).
- **수용🟢** — 카드 대화 fixture 합격 기준(§10).
- **엣지🟢** — AI 없음·파싱 실패·하위 호환(§3·§4·§6).
- **플랫폼⚪** — Tauri 데스크톱 단일 흐름, find_executable이 win 확장자 이미 처리.

## 14. 후속 트랙 — 이 게이트가 받쳐줄 다음 개선

기획방 개선은 두 갈래이며, **B(이 게이트) → A(카드 흐름)** 순서로 간다.

| | 개선 | 목적 |
|---|---|---|
| **B (이 명세)** | 마감 게이트 — 저장 시 구현 가능성 판정 | **신뢰** (산출물이 진짜 구현 가능) |
| **A (후속)** | 카드 흐름 — 대화 중 결정이 카드로 떴다 확정 | **몰입** (눈에 보이는 진척) |

A의 원본 기획(`plans/기힉방을-조금-더-흥미로운-요소를-추가하고-싶은데-어떤게-좋을까.md`)은
행동은 완성됐으나 발동·데이터·판정이 비어 있다. **B를 먼저 세우면, A를 만들 때 그 게이트가
바로 그 구멍을 🔴로 잡아준다** — 즉 B는 A의 검증 도구이자 첫 실사용 대상이 된다(§10의
fixture가 곧 A의 기획안). A는 B 완료 후 별도 spec → plan 사이클로 진행한다.
