# 작업방 "실행해보기" CTA 강조 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 작업방 완료 후 "실행해보기"로 가는 원클릭 CTA를 ① 완료 상태창에서 1차 버튼으로 승격하고 ② 패널 하단에 sticky 고정 바로 추가해, 사용자가 보는 위치 어디서든 한 번에 닿게 한다.

**Architecture:** 두 배치의 노출 조건을 단일 순수 헬퍼 `runCtaVisible(phase, verdict)` 로 통일(테스트 가능). `WorkRoom.tsx` 는 이 헬퍼로 sticky 바를 게이팅하고, 기존 완료 패널 버튼은 스타일만 승격한다. 실행 액션은 기존 `onNavigate("run")` 재사용 — RunPanel/백엔드 무변경.

**Tech Stack:** React 19 + TypeScript, Vitest 4 + @testing-library/react(jsdom), Tauri. 스타일은 인라인 + 기존 브루탈리즘 톤(`#1A1A1A`/`#F5F1E3`).

**Spec:** `docs/superpowers/specs/2026-06-14-workroom-run-cta-design.md`

> 스펙은 "신규 파일 없음"이었으나, 테스트 가능한 경계를 위해 **순수 헬퍼 1개**(`src/pages/workRoomCta.ts`)만 추가한다. `src/pages/planning/PlanningPersonaStatusLabel.ts` 선례(페이지 옆 콜로케이트 헬퍼)를 따른다. 이 외 구조 변경 없음.

---

## File Structure

- **Create:** `src/pages/workRoomCta.ts` — CTA 노출 게이팅 순수 함수. WorkRoom 의존(tauri 등) 없이 import 가능해야 단위 테스트가 가볍다.
- **Create:** `src/pages/__tests__/workRoomCta.test.ts` — 게이팅 단위 테스트.
- **Modify:** `src/pages/WorkRoom.tsx`
  - 헬퍼 import.
  - 완료 패널 버튼(현 `:688` 근처) 승격 + 행 맨 앞 이동.
  - 콘텐츠 그리드 끝(현 `:746` `</div>` 직전)에 sticky CTA 바 추가.

---

## Task 1: CTA 게이팅 순수 헬퍼 (TDD)

**Files:**
- Create: `src/pages/workRoomCta.ts`
- Test: `src/pages/__tests__/workRoomCta.test.ts`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/pages/__tests__/workRoomCta.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { runCtaVisible } from "../workRoomCta";

describe("runCtaVisible", () => {
  test("finished + pass → 표시", () => {
    expect(runCtaVisible("finished", "pass")).toBe(true);
  });

  test("finished + prepare → 표시 (prepare 도 safe)", () => {
    expect(runCtaVisible("finished", "prepare")).toBe(true);
  });

  test("finished + stop → 숨김 (안전 우선)", () => {
    expect(runCtaVisible("finished", "stop")).toBe(false);
  });

  test("finished + verdict 없음(null/undefined) → 숨김", () => {
    expect(runCtaVisible("finished", null)).toBe(false);
    expect(runCtaVisible("finished", undefined)).toBe(false);
  });

  test("아직 안 끝남(running/idle/verifying) → 숨김", () => {
    expect(runCtaVisible("running", "pass")).toBe(false);
    expect(runCtaVisible("idle", "pass")).toBe(false);
    expect(runCtaVisible("verifying", "pass")).toBe(false);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/pages/__tests__/workRoomCta.test.ts`
Expected: FAIL — `Failed to resolve import "../workRoomCta"` (모듈 없음).

- [ ] **Step 3: 최소 구현 작성**

`src/pages/workRoomCta.ts`:

```ts
// === ANCHOR: WORKROOM_CTA_START ===
// 작업방 "실행해보기" CTA 노출 조건 — 완료 상태창 버튼과 하단 sticky 바의 단일 진실원.
// guard 가 안전(pass/prepare)일 때만 실행을 권한다. stop/미실행은 숨겨 안전 우선.
export function runCtaVisible(phase: string, verdict: string | null | undefined): boolean {
  return phase === "finished" && (verdict === "pass" || verdict === "prepare");
}
// === ANCHOR: WORKROOM_CTA_END ===
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/pages/__tests__/workRoomCta.test.ts`
Expected: PASS (5 passed).

- [ ] **Step 5: 커밋**

```bash
git add src/pages/workRoomCta.ts src/pages/__tests__/workRoomCta.test.ts
git commit -m "feat(workroom): runCtaVisible 게이팅 헬퍼 — 실행 CTA 단일 진실원"
```

---

## Task 2: 완료 상태창 버튼 승격 + 행 맨 앞 이동

**Files:**
- Modify: `src/pages/WorkRoom.tsx` (완료 패널 버튼 행 — 현재 `:656`–`:699` 의 `<div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>` 블록)

> 참고: 줄 번호는 편집에 따라 밀린다. **앵커 문자열로 위치를 잡아라**. 대상은 `phase === "finished"` 완료 패널 안, 버튼들을 담은 `flexWrap: "wrap"` flex 컨테이너.

- [ ] **Step 1: 기존 실행해보기 버튼을 행 맨 앞으로 옮기고 1차 버튼으로 승격**

현재 그 flex 컨테이너 **끝부분**의 이 블록을 제거한다:

```jsx
              {guardSafe && (
                <button className="btn btn-sm" onClick={() => onNavigate("run")}>
                  ▶ 실행해보기 →
                </button>
              )}
```

그리고 flex 컨테이너 **여는 태그 바로 다음(맨 앞)** 에 승격된 버전으로 다시 넣는다:

```jsx
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {guardSafe && (
                <button
                  className="btn"
                  onClick={() => onNavigate("run")}
                  style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}
                >
                  ▶ 실행해보기 →
                </button>
              )}
              {guardVerdict === "prepare" &&
                /* …기존 앵커 자동추가 버튼 블록 그대로 이어짐… */
```

(나머지 버튼 블록 — 앵커 자동추가/체크포인트 저장/저장 메시지/stop 되돌리기/홈/다시실행 — 은 순서·내용 그대로 둔다. `guardSafe` 게이팅도 기존과 동일.)

- [ ] **Step 2: 타입체크 + 빌드 확인**

Run: `npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 3: 수동 시각 확인 (알람앱을 테스트 프로젝트로)**

1. `npm run dev` 로 GUI 실행 → 알람앱(`~/Documents/coding/알람앱`, guard pass 상태) 프로젝트 열기.
2. 작업방에서 AI 작업을 한 사이클 돌려 `phase==="finished"` + guard `pass` 도달(또는 기존 "지난 실행"으로 finished 패널 재현).
3. 완료 패널 버튼 행에서 **`▶ 실행해보기 →` 가 맨 앞 + 다크 1차 버튼**으로 두드러지는지 확인.
4. 클릭 → 실행해보기 탭으로 이동하는지 확인.

- [ ] **Step 4: 커밋**

```bash
git add src/pages/WorkRoom.tsx
git commit -m "feat(workroom): 완료 상태창 '실행해보기' 1차 버튼으로 승격 + 행 맨 앞"
```

---

## Task 3: 패널 하단 sticky CTA 바 추가

**Files:**
- Modify: `src/pages/WorkRoom.tsx` (헬퍼 import + 콘텐츠 그리드 끝에 sticky 바)

- [ ] **Step 1: 헬퍼 import 추가**

`WorkRoom.tsx` 상단 import 블록에 추가:

```ts
import { runCtaVisible } from "./workRoomCta";
```

- [ ] **Step 2: 콘텐츠 그리드 마지막 자식으로 sticky 바 추가**

`WORKROOM_END` 앵커 위쪽, 콘텐츠 그리드(`<div style={{ display: "grid", gap: 12, maxWidth: 860 }}>`)를 닫는 `</div>` **직전**(스트리밍 로그 섹션 `)}` 다음 줄)에 삽입한다:

```jsx
      {runCtaVisible(phase, guardVerdict) && (
        <div
          style={{
            position: "sticky",
            bottom: 0,
            zIndex: 5,
            // .page-content 의 padding:20px 를 음수 마진으로 상쇄해 컨테이너 가장자리에 밀착.
            margin: "0 -20px -20px",
            padding: "12px 20px",
            background: "#F5F1E3",
            borderTop: "2px solid #1A1A1A",
            boxShadow: "0 -4px 12px rgba(0,0,0,0.12)",
          }}
        >
          <button
            className="btn"
            onClick={() => onNavigate("run")}
            style={{ width: "100%", background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}
          >
            ▶ 이대로 실행해보기 →
          </button>
        </div>
      )}
```

- [ ] **Step 3: 타입체크 확인**

Run: `npx tsc --noEmit`
Expected: 에러 없음 (`guardVerdict` 는 `:402` 에서 이미 선언됨, `phase`/`onNavigate` 도 스코프 내).

- [ ] **Step 4: 수동 시각 확인 (sticky 동작 — 핵심)**

1. `npm run dev` → 알람앱 열기 → `phase==="finished"` + guard `pass` 도달.
2. "진행 내용" 로그가 길게 쌓인 상태에서 **끝까지 스크롤**.
3. 확인 사항:
   - sticky 바가 **뷰포트 하단에 계속 고정**되어, 로그를 스크롤해도 `▶ 이대로 실행해보기 →` 가 항상 보인다.
   - 바 배경이 **불투명**이라 아래 로그 줄이 비쳐 보이지 않는다.
   - 바가 컨테이너 좌우/하단 **가장자리에 밀착**(음수 마진 정상)되어 떠 보이지 않는다. 떠 보이면 `margin` 값 미세조정.
   - 클릭 → 실행해보기 탭 이동.
4. guard 가 `stop` 인 시나리오(또는 일부러 verdict 변경)에서 **sticky 바와 상태창 버튼 둘 다 사라지는지** 확인(안전 게이팅).
5. 로그가 짧아 스크롤이 없을 때 바가 자연 위치(맨 아래)에 무난히 놓이는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add src/pages/WorkRoom.tsx
git commit -m "feat(workroom): 패널 하단 sticky '실행해보기' 고정 CTA 바"
```

---

## Task 4: 전체 검증

**Files:** (없음 — 검증만)

- [ ] **Step 1: 전체 타입체크**

Run: `npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 2: 전체 테스트**

Run: `npm test`
Expected: 신규 `workRoomCta.test.ts` 포함 전부 PASS, 기존 테스트 회귀 없음.

- [ ] **Step 3: 프로덕션 빌드**

Run: `npm run build`
Expected: `built in …`, error 없음.

- [ ] **Step 4: 수동 회귀 체크**

완료 패널의 나머지 버튼(체크포인트 저장/홈에서 상태확인/다시 실행 준비)과 stop 시 "백업에서 되돌리기" 안내가 기존대로 표시·동작하는지 확인.

---

## Self-Review (작성자 점검 완료)

- **스펙 커버리지**: §3-1 승격→Task 2, §3-2 sticky 바→Task 3, §4 게이팅 표→Task 1 헬퍼 + Task 2/3 적용, §7 테스트→Task 1(자동)·Task 2/3/4(수동/빌드). 전 항목 매핑됨.
- **플레이스홀더**: 없음. 모든 코드 단계에 실제 코드/명령/기대출력 명시.
- **타입 일관성**: `runCtaVisible(phase, verdict)` 시그니처가 정의(Task 1)와 호출(Task 3)에서 일치. `guardVerdict`/`guardSafe`/`onNavigate`/`phase` 는 WorkRoom 기존 스코프 변수 재사용.
- **스펙 일탈**: 헤더에 명시 — 테스트용 순수 헬퍼 파일 1개 추가(선례 있음). 그 외 스펙 준수.
