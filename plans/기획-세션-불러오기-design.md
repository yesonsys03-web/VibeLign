# 기획 세션 "불러와서 이어가기" — 설계 명세

> 작성일: 2026-06-07
> 대상: VibeLign 기획방(Planning Room)

## 배경 — 왜

저장한 기획안을 다시 꺼내 이어서 수정할 길이 빈약하다. 현재는 코드 탐색기에서 `.md`를
우클릭 → "기획방에서 검토"로 **문서를 새 대화로 다시 읽는** 우회로뿐이고, 그건 그 기획을
만든 **원래 대화·카드를 복원하지 않는다.** 또 임의의 과거 세션을 고르는 UI가 없다
(`load_latest_planning_chat_session`은 가장 최근 1개만 복원).

토대는 이미 있다 — 세션은 `.vibelign/planning/chat_<id>/`에 `messages.json`(대화) +
`cards.json`(카드) + `session.json`(여기에 `output_path` = 저장된 `plans/*.md` 경로)으로
**통째로 영속**된다. 그래서 이 작업은 새 저장 포맷·마이그레이션 없이 **"이미 저장되는 걸
고를 수 있게 노출"** 만 한다.

## 한 줄 정의

이전 기획 세션(대화 + 카드)을 목록 모달에서 골라 **그대로 복원**해 이어서 수정한다.

## 확정된 결정 (브레인스토밍)

| 축 | 결정 |
|---|---|
| 목록 범위 | **모든 세션** (저장됨 + 진행 중 초안). 저장 여부는 배지로 구분. |
| 진입 | 홈의 **"이전 기획 불러오기" 버튼 → 피커 모달**. |

## 1. Rust — 두 명령 (`commands/planning_chat.rs`)

### `list_planning_chat_sessions(project_dir) -> Vec<PlanningSessionSummary>`
`.vibelign/planning/chat_*/`를 훑어 요약을 **최신순(messages.json mtime 내림차순)**으로 반환.

```rust
// 응답 항목 (camelCase 직렬화)
PlanningSessionSummary {
    session_id: String,
    title: String,            // session.idea 첫 줄, 공백 trim, 최대 60자
    output_path: Option<String>,
    saved: bool,              // output_path.is_some()
    created_at: String,       // session.created_at
    message_count: usize,     // messages.json 길이
    card_count: usize,        // cards.json 길이
}
```
- `chat_*` 디렉터리 중 `session.json` + `messages.json`이 모두 있는 것만 포함(기존
  `latest_chat_session_file`과 동일 기준). 깨진 디렉터리는 skip.
- 정렬: `messages.json`의 modified time 내림차순(최신 위). 기존 `latest_chat_session_file`의
  mtime 수집 로직을 일반화해 재사용.

### `load_planning_chat_session(project_dir, session_id) -> PlanningChatSessionResponse`
특정 세션을 id로 로드. 응답엔 이미 messages·cards·output_path·markdown이 실린다(기존 응답 타입).

**리팩터:** 현재 `load_latest_planning_chat_session`은 (디렉터리 찾기 → session/messages 읽기 →
markdown → cards → success)를 인라인으로 한다. 그 "**세션 디렉터리 → 응답**" 코어를 헬퍼
`load_session_from_dir(project_dir, session_dir) -> PlanningChatSessionResponse`로 빼서,
`load_latest`(디렉터리=최신)와 `load_by_id`(디렉터리=`planning_dir/session_id`) 둘 다 호출.
**동작 동일** — 회귀 테스트로 보장.

두 명령 모두 `lib.rs`의 `invoke_handler`에 등록.

## 2. 프론트 — 피커 모달

- **신설 `pages/planning/PlanningSessionPicker.tsx`** — 모달. 열리면
  `listPlanningChatSessions(projectDir)` 호출 → 행 렌더. 각 행:
  - 제목(큰 글씨) / 둘째 줄에 `output_path` 파일명(있으면) · `대화 N · 카드 M`
  - 우측 배지: `✓ 저장됨`(초록 칩) / `작성중`(회색 칩)
  - 행 클릭 → `onSelect(sessionId)`.
  - 빈 목록 → "아직 저장된 기획이 없어요" 안내. 로딩 중 → 간단한 표시.
  - 닫기: 배경 클릭 / 취소 버튼. (기존 `PlanSaveDialog` 모달 스타일 재사용 — 검은 테두리·하드 섀도우.)
- **`lib/vib/types.ts`** — `PlanningSessionSummary` 타입.
- **`lib/vib/planning.ts` + `index.ts`** — `listPlanningChatSessions(projectDir)`,
  `loadPlanningChatSession(projectDir, sessionId)` invoke 래퍼.

## 3. 배선

- **`App.tsx`** — 상태 `showSessionPicker`. 함수 `resumeSession(sessionId)`:
  `loadPlanningChatSession(projectDir, sessionId)` → `setReviewSourcePath(null)` →
  `setPlanningPrompt(result.prompt || ...)` → `setPlanningResult(result)` → `setPage("planning")`.
  (기존 `loadProjectPlanning`의 성공 분기와 동일 패턴.) 모달은 App 렌더에서
  `{showSessionPicker && <PlanningSessionPicker projectDir={projectDir} onSelect={...} onClose={...} />}`.
- **`Home.tsx`** — 기획 시작 근처에 **"이전 기획 불러오기"** 버튼. 새 prop
  `onOpenPlanningHistory?: () => void` → App에서 `() => setShowSessionPicker(true)` 전달.

## 4. 데이터 흐름

```
[목록] "이전 기획 불러오기" → 피커 → list_planning_chat_sessions → 행들(최신순)
[복원] 행 클릭 → load_planning_chat_session(id) → 응답(대화+카드+output_path)
       → setPlanningResult → 기획방 진입(대화·카드 복원)
[저장] 기존 그대로 — output_path 있으면 그 경로로 재저장(덮어쓰기)
```

## 5. 컴포넌트 경계 (독립 테스트)

- `list_planning_chat_sessions`(스캔 → 요약) · `load_session_from_dir`(디렉터리 → 응답, 공유) ·
  `PlanningSessionPicker`(fetch + 렌더 + 선택) · 래퍼.

## 6. 테스트

- **Rust:** tempdir에 세션 디렉터리 2개(하나는 output_path 있음, 하나는 없음, mtime 차이) →
  `list`가 **최신순 + saved 플래그 + message/card 카운트**를 맞게 내는지. `load_session_from_dir`
  추출 후 **기존 load_latest 테스트(있으면) + planning_chat 전체 통과**(회귀).
- **프론트:** 피커 행 렌더(제목·배지·카운트), 빈 상태 안내.
- **수동:** 저장한 기획 → 불러오기 → 대화·카드 복원 → 수정 → 덮어쓰기 저장.

## 7. 안 만드는 것 (YAGNI)

세션 삭제 · 이름 변경 · 검색/필터 · 페이지네이션 — 다음 조각. 이번엔 **목록 + 복원**만.

## 8. 메타 — 게이트 통과 자가점검

- **발동🟢** 버튼/행 클릭. **데이터🟢** `PlanningSessionSummary` 스키마 + 기존 세션 저장 재사용.
- **판정🟢** id로 로드(모호함 없음). **수용🟢** §6 수동 검증.
- **엣지🟢** 빈 목록·삭제된 output_path(세션은 그래도 로드)·messages 없는 디렉터리 skip.
- **플랫폼🟢** 아래 §9.

## 9. 크로스플랫폼 (mac/Windows)

이 기능은 **AI 서브프로세스가 없는 순수 파일 IO + UI**라 윈도 추가 위험이 거의 없다.

- **경로·FS:** `planning_dir().join()`(PathBuf), `read_dir`, `metadata().modified()` 모두
  크로스플랫폼. 이미 윈도에서 동작하는 `latest_chat_session_file`의 디렉터리·mtime 로직을
  일반화해 재사용하므로 새 OS 의존성이 없다.
- **유일한 뉘앙스 — 표시용 파일명:** `output_path`는 OS에 따라 `\` 또는 `/`를 포함할 수 있다.
  피커에서 파일명만 떼어 보여줄 때 **`\`와 `/` 둘 다로 분리**한다(기존 `PlanningRoom`의
  `splitSourcePath`가 `replace(/\\/g, "/")`로 정규화하는 방식과 동일하게). 경로 자체는
  저장·재저장 시 기존 흐름이 그대로 처리한다.
