# Deep Interview Spec: 기획방 저장 — 결정적 이중 입구 + 사용 빈도 로깅

> 개정 이력: 딥 인터뷰(4라운드, 모호도 10%)로 "단일 통제 저장" 불변식 도출 →
> 이후 UX 논의에서 **자연어 의도 감지(휴리스틱)를 폐기**하고 **결정적 이중 입구(버튼 + `/저장`) + 로깅**으로 메커니즘 교체.
> (구 파일명: 기획방-저장-의도라우팅-spec.md)

## Metadata
- Rounds: 4 (+ post-interview UX revision)
- Final Ambiguity Score: 10%
- Type: brownfield (VibeLign 기획방)
- Generated: 2026-06-09 / Revised: 2026-06-09
- Threshold: 20%
- Status: PASSED (revised)

## Goal
기획안 저장은 **단 하나의 통제 경로**(`save_planning_chat_as_markdown` → `synthesize_planning_markdown`: 고정 템플릿 + 확정카드 주입 + readiness 헤더)로만 일어나며, 결과물은 항상 마찰(확정/미결정)+readiness를 싣고 `session.json.output_path`에 등록된다. 사용자는 이 단일 저장에 **두 개의 결정적 입구**로 접근한다:
1. **눈에 띄는 저장 버튼** (마우스파 · 신중한 마무리 순간용)
2. **명시적 `/저장` 슬래시 커맨드** (키보드 흐름을 안 깨고 싶은 사람용)

자연어 의도 감지("저장해줘"를 휴리스틱으로 추론)는 **쓰지 않는다.** 두 입구의 사용 빈도를 로깅해 "타이핑 입구가 실제로 필요한가"를 데이터로 판단한다.

## 왜 자연어 감지를 버렸나 (설계 근거)
- 이 문제를 시작한 사달이 "타이핑한 의도 ≠ 실제 동작"인데, 해결책으로 또 자연어 휴리스틱을 쓰면 같은 종류의 **오발동/미발동**이 생긴다.
- UX상 "버튼 vs 타이핑"은 *순간의 편함(타이핑)* 과 *신뢰성(버튼)* 의 충돌이고, 채팅 UI에서 둘 다 잡는 업계 수렴 패턴은 **슬래시 커맨드**(키보드 흐름 유지 + 결정적)다.
- 저장은 세션당 1회의 신중한 행동 → 눈에 띄는 버튼도 충분히 적합. 두 결정적 입구를 다 주고 **데이터로 검증**한다.

## Constraints
- 단일 저장 경로(기존 `save_planning_chat_as_markdown` 재사용, 백엔드 변경 최소).
- 두 입구 모두 **결정적**(클릭 / 명시적 `/` 프리픽스). NL 추론 금지.
- `/저장`은 입력란에서 정확한 프리픽스 매칭으로만 발동(오발동 0).
- 사용 빈도 로깅은 가볍게(카운트만, 개인정보 없음).

## Non-Goals
- 자연어 "저장해줘" 감지/라우팅 (**폐기**).
- AI 자유 파일쓰기 전면 차단.
- 미결정카드 기능 자체 신규 구축(별개 과제) — 단 통제경로가 확정/미결정 싣는 구조와 호환 유지.

## Acceptance Criteria
- [ ] 저장 버튼과 `/저장` 커맨드가 **동일한 백엔드**(`save_planning_chat_as_markdown`)를 호출하고, 동일 산출물 + `output_path` 등록을 만든다.
- [ ] 저장 버튼이 항상 접근 가능/눈에 띈다(스크롤로 사라져 못 찾는 일 없게 — 가시성/위치 점검).
- [ ] 입력란에서 `/저장` 입력 시 **페르소나 호출 없이** 즉시 통제 저장 실행.
- [ ] 유사/오타 입력(`/저자`, 일반 문장 "이거 저장하면 좋겠다")은 저장을 트리거하지 않는다.
- [ ] 각 저장이 어느 입구(`button` | `slash`)에서 왔는지 로깅된다(누적 카운트).
- [ ] 자연어 "저장해줘"는 여전히 페르소나에게 가는 일반 대화로 처리된다(저장 트리거 X).

## 남은 결정 (이번 스펙 밖 · 데이터 후 판단)
- **AI 자유 파일쓰기 우회로**: 페르소나 CLI가 "기획안 같은" 파일을 임의 작성하는 건 여전히 가능. 닫으려면 페르소나 프롬프트에 *"기획안 파일을 직접 쓰지 말고 저장 입구로 안내"* 한 줄 추가(가벼움). **이번 범위엔 안 넣되**, 로깅 데이터 + 실사용 행태를 보고 추가 여부 결정 권장. (안 닫으면 단일-저장 불변식이 문구에 따라 새는 구멍이 남음을 인지할 것.)

## Logging Design (가벼움) — 결정됨: 백엔드 파일
- 저장 호출 시 `source: "button" | "slash"` 를 기록.
- **sink (확정)**: `save_planning_chat_as_markdown`에 `source` 인자 추가 → `.vibelign/planning/save-sources.json`에 `{button: n, slash: n}` 누적.
  - 백엔드 누적 이유: 재시작·세션 교체·기기에도 카운트 보존돼 "N주 후 비율 판단" 목적에 정확 (localStorage 는 초기화·기기별 분산 위험으로 폐기).
- 개인정보 없음(횟수만). 목적: N주 후 `button : slash` 비율로 "타이핑 입구가 가치 있나" 판단 → `/저장` 유지/제거 결정.

## Technical Context (brownfield)
- **단일 저장 백엔드(재사용)**: `PlanningRoom.tsx::handleSavePlan` → `savePlanningChatAsMarkdown` → `planning_chat.rs::save_planning_chat_as_markdown` → `synthesize_planning_markdown`(확정카드 주입 완료, 7f58caa). `output_path` 기록.
- **입구 1 — 버튼**: `PlanningActionBar`의 저장 버튼(현존). 가시성/위치만 점검(항상 보이게).
- **입구 2 — `/저장`**: `PlanningPersonaComposer.handleSubmit`에서 입력이 정확히 `/저장`(등록 커맨드)으로 시작하면 `appendPlanningChatTurn` 대신 저장 경로 호출. 명시적 프리픽스라 오발동 없음. (확장 여지: `/` 입력 시 커맨드 힌트 표시.)
- **로깅**: 저장 호출 지점에 `source` 인자 전달 → 카운터 증가. 두 입구 모두 같은 저장 함수를 부르되 source만 다르게.
- **자유쓰기**: 막지 않음(범용). 단 위 "남은 결정"의 우회로는 별도.

## Windows 호환성 점검 (2026-06-09, 코드 대조 완료)
> 결론: **스펙대로 구현해도 Windows에서 깨질 곳 없음.** 신규 추가분(`/저장` 입구 + 출처 로깅) 중 Windows에서 실제로 갈리는 지점은 `/저장` 한글 매칭의 NFC 정규화 **단 하나**. 나머지는 OS 무관.

### ⚠️ 유일한 Windows-민감 지점 — `/저장` 한글 매칭
- **IME 자체는 안전**: `PlanningPersonaComposer.tsx`가 이미 `!event.nativeEvent.isComposing`로 조합 중 Enter를 막음. Windows 한글 IME도 "조합 중 Enter = 음절 확정" 동작이 동일 → `/저장` 입력 후 첫 Enter는 마지막 음절 확정, 두 번째 Enter에 submit. 이 시점 `message` state엔 확정된 `/저장`이 들어있어 매칭 OK.
- **NFC 정규화 필요**: 소스의 `"/저장"` 리터럴은 NFC 조합형(U+AC00~). 정상 타이핑이면 Win/macOS 모두 NFC라 `===` 일치하지만, **붙여넣기**(특히 macOS産 텍스트는 NFD 분해형 가능)로 들어오면 매칭이 빗나감.
  → **비교 전 `message.trim().normalize("NFC")` 적용**. 싸고, 오발동 0 불변식 유지.

### ✅ 저장 경로/파일명 — 이미 Windows 대응 완료 (재사용 부분, 신규 위험 없음)
- `plan_slug`(`planning_chat_synthesis.rs`): Windows 금지문자 `< > : " / \ | ? *`·제어문자 제거, 예약명(con/prn/nul/com1…lpt9) 회피, 후행 `.` strip, 한글 보존.
- `safe_relative_target`: 절대경로·`..` 거부.
- `absolute_output_path` 저장 → 프론트 `getSavedPlanOpenPath`가 OS 네이티브 절대경로 우선 반환, `isAbsolutePath`가 `C:\` 드라이브레터·`[\\/]` 양쪽 구분자 처리.
- *Cosmetic only*: Windows에선 `output_path`가 백슬래시(`plans\xxx.md`)로 저장·표시됨. 기능 영향 없음(열기는 absolute 경로 사용). 표시 통일을 원하면 저장 시 `.replace('\\', "/")` — 선택사항.

### ✅ 출처 로깅 — OS 무관
- (a) `localStorage`: 브라우저 API, OS 무관. (b) `.vibelign/planning/` 파일: 백엔드 `write_json`/`std::fs` + `PathBuf::join`이라 크로스플랫폼 안전. 둘 다 Windows 문제 없음.

### 구현 시 함정 (Windows 무관, 그러나 짚어둘 것)
- `canSubmit`이 `selectedPersonaIds.length > 0`을 요구 → `/저장`은 "페르소나 호출 없이" 발동해야 하므로(AC) **슬래시 분기를 canSubmit/페르소나 루프보다 앞**에 배치. 페르소나 버튼이 `@멘션`을 prepend하니 `@치로 /저장` 혼합 입력도 고려.
- 매칭 규칙: `trimmed === "/저장"` (또는 `startsWith("/저장 ")`)로 엄격히 — AC의 `/저자`·일반문장 비트리거 보장.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| SavedPlanFile (저장파일) | core domain | path, content, output_path 등록 | 구현AI가 소비 |
| ConfirmedCard (확정카드) | core domain | title, summary, state=Confirmed | 저장파일에 주입 |
| UndecidedCard (미결정카드) | core domain (신규개념) | 마찰/충돌 | 저장파일에 함께 실려야 |
| ReadinessReport | supporting | 🟢/🔴 checks | 저장파일 헤더 |
| ControlledSave (통제저장경로) | core process | save_planning_chat_as_markdown | 정본 산출 (단일) |
| SaveButton (저장버튼) | input affordance | 가시성 | → ControlledSave |
| SlashCommand (`/저장`) | input affordance (신규) | 명시적 프리픽스 | → ControlledSave |
| SaveSource (저장출처 로깅) | supporting (신규) | button \| slash, count | 입구 사용 빈도 |
| AIFreeWrite (자유경로) | external/agent | 페르소나 CLI 임의 작성 | 막지 않음 (우회로는 남은 결정) |
| ImplementationAgent (구현AI) | external | — | SavedPlanFile를 작업재료로 받음 |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 7 | 7 | - | - | N/A |
| 2 | 8 | 1 (SaveIntent) | 0 | 7 | 0.875 |
| 3 | 8 | 0 | 1 (통제버튼→통제저장경로) | 7 | ~1.0 |
| 4 | 9 | 1 (IntentRouter) | 0 | 8 | ~1.0 |
| post-rev | 10 | 2 (SlashCommand, SaveSource) | 1 (IntentRouter→폐기, SaveButton 분리) | 7 | 메커니즘 교체 |

> post-rev 주: 자연어 IntentRouter를 폐기하고 결정적 SlashCommand + SaveSource(로깅)로 교체. 불변식(단일 통제 저장)은 불변.

## Interview Transcript
<details>
<summary>Full Q&A (4 rounds) + UX revision</summary>

### Round 1 — Goal
**Q:** 저장된 파일이 반드시 보장해야 하는 단 하나는?
**A:** 구현으로 넘길 '작업 재료' (확정·미결정 마찰 + readiness 필수) · **Ambiguity 49%**

### Round 2 — Constraints
**Q:** 목적이 '작업 재료'인데도 자유경로를 살려둘 이유?
**A:** 있다 — 속도·자연스러움 · **Ambiguity 37%**

### Round 3 — Success Criteria
**Q:** 타이핑 저장이 완벽하면 결정적 증거 하나는?
**A:** 버튼 저장과 100% 동일 + 세션 등록 · **Ambiguity 14%**

### Round 4 — Contrarian
**Q:** AI 자유쓰기를 막을지 vs 의도만 라우팅할지?
**A:** 두고 의도만 라우팅 · **Ambiguity 10%**

### Post-interview UX revision
**논점:** 버튼 클릭 vs 타이핑 — 어느 게 더 편한가.
**결론:** 순간 편함은 타이핑, 신뢰성은 버튼. 채팅 UI의 수렴 패턴은 슬래시 커맨드(흐름+결정성). 저장은 세션당 1회 신중 행동이라 버튼도 적합. → **자연어 감지 폐기, 결정적 이중 입구(버튼 + `/저장`) + 사용 빈도 로깅으로 데이터 기반 검증.**
</details>
