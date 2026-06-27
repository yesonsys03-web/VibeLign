# 베이비 모드 스크립트형 튜토리얼 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 완전 초보자를 손잡고 끌어 진짜 작동하는 앱 1개를 완성시키면서 VibeLign 안전 루프(기획→체크포인트→AI작업→검사→저장/되돌리기) 사용법을 체득시키는 스포트라이트 튜토리얼을 추가한다.

**Architecture:** 기존 반응형 가이드(`lib/nav/guide.ts`/`useGuide.ts`)와 **병렬로** 스크립트형 튜토리얼 레이어를 얹는다. 대본은 데이터(`lib/tutorial/scripts.ts`), 진행 상태는 훅(`useTutorial.ts`, `useGuide` 패턴 복제), 단계 완료 자동 감지는 기존 `GuideSignals`를 재활용하는 순수 함수(`completion.ts`), UI는 화면을 어둡게 하고 대상 하나만 비추는 오버레이(`SpotlightTour.tsx`). 튜토리얼 활성 중엔 `GuideStrip`을 숨기고, 완주 시 반응형 가이드로 졸업 인계한다.

**Tech Stack:** React + TypeScript, Vitest + React Testing Library (jsdom), Tauri GUI(`vibelign-gui/`), 기존 `brutalism.css`.

## Global Constraints

- **VibeLign 패치 규칙** (CLAUDE.md): 가능한 가장 작은 패치. 요청한 파일만 수정. 파일 전체 재작성 금지. **앵커 경계** 안에서만 수정. 임포트 구조 임의 변경 금지. 아래 "신규 파일"로 명시된 것 외에 새 파일 생성 금지.
- **테스트 러너:** Vitest. 실행 명령 `npm run test` (working dir: `vibelign-gui/`). 단일 파일: `npm run test -- <path>` (또는 `npx vitest run <path>`).
- **모든 작업은 `vibelign-gui/` 안에서.** 경로는 그 기준 상대경로로 표기.
- **신규 파일(이번 계획에서 생성 허가된 것 전부):**
  - `src/lib/tutorial/types.ts`
  - `src/lib/tutorial/scripts.ts`
  - `src/lib/tutorial/completion.ts`
  - `src/lib/tutorial/useTutorial.ts`
  - `src/lib/tutorial/spotlight.ts`
  - `src/components/tutorial/SpotlightTour.tsx`
  - `src/components/tutorial/TutorialPicker.tsx`
  - 각각의 `__tests__`/인접 `*.test.ts(x)` 테스트 파일
- **재활용(신규 작성 금지, import만):** `GuideSignals`(`src/lib/nav/guide.ts`), `Page`(`src/lib/nav/stages.ts`), `useGuide` localStorage 패턴, `.guide-mascot`/`.guide-bubble`(`src/styles/brutalism.css`).
- **spec의 `done` enum 확장 명시:** spec §3은 `done: 'changedFiles' | 'planResponded' | 'checkpoint' | 'runVerified' | 'manual'`. 구현에선 여기에 **`'copy'`**(복사 클릭 시 컴포넌트가 즉시 완료 처리)와 **`'guardChecked'`**(spec §5 안전 절반의 guard 확인 단계)를 추가한다. 이 둘은 설계 의도(§5) 안의 보강이다.
- **목표 동급 원칙(spec §1):** ① 진짜 작동 앱 완성 경험 ② VibeLign 사용법 체득 — 둘 다 필수. 대본은 §5 "안전 절반"(체크포인트 먼저 / guard 검사 / 되돌리기 인지)을 반드시 포함.
- **GuideSignals 실제 정의(재확인용, `src/lib/nav/guide.ts`):**
  ```ts
  export interface GuideSignals {
    hasPlanDoc: boolean;
    planningPending: boolean;
    hasCheckpoint: boolean;
    changedFileCount: number | null;
    guardStatus: "ok" | "issue" | null;
    runVerified: boolean;
  }
  ```

---

### Task 1: 튜토리얼 타입 + "할 일 목록" 대본 + 대본 형식 검증

**Files:**
- Create: `src/lib/tutorial/types.ts`
- Create: `src/lib/tutorial/scripts.ts`
- Test: `src/lib/tutorial/__tests__/scripts.test.ts`

**Interfaces:**
- Consumes: `Page` from `src/lib/nav/stages.ts`.
- Produces:
  - `type TutorialId = "todo" | "guestbook" | "quiz"`
  - `type TutorialStepKind = "copy" | "pasteSend" | "click" | "confirm"`
  - `type StepDone = "copy" | "planResponded" | "changedFiles" | "checkpoint" | "guardChecked" | "runVerified" | "manual"`
  - `interface TutorialStep { id; kind; say; why?; target?; copyText?; done; goPage? }`
  - `interface Tutorial { id; title; emoji; goal; steps: TutorialStep[] }`
  - `const TUTORIALS: Tutorial[]` and `function getTutorial(id: TutorialId): Tutorial | undefined`

- [ ] **Step 1: 타입 파일 작성** — Create `src/lib/tutorial/types.ts`:

```ts
// ANCHOR: TUTORIAL_TYPES_START
import type { Page } from "../nav/stages";

export type TutorialId = "todo" | "guestbook" | "quiz";

export type TutorialStepKind = "copy" | "pasteSend" | "click" | "confirm";

// spec §3 enum + 'copy'(복사 클릭 즉시 완료) + 'guardChecked'(§5 안전검사 단계)
export type StepDone =
  | "copy"
  | "planResponded"
  | "changedFiles"
  | "checkpoint"
  | "guardChecked"
  | "runVerified"
  | "manual";

export interface TutorialStep {
  id: string;
  kind: TutorialStepKind;
  /** 시킬 행동 한 문장 (항상 1개) */
  say: string;
  /** (선택) "왜 이걸 하나요?" 한 줄 — 행동/판단은 안 늘림 */
  why?: string;
  /** 스포트라이트할 요소의 data-tour 값 (click/pasteSend/confirm) */
  target?: string;
  /** kind==='copy'일 때 복사시킬 지시문 */
  copyText?: string;
  done: StepDone;
  /** 이 단계 전에 데려다 놓을 화면 */
  goPage?: Page;
}

export interface Tutorial {
  id: TutorialId;
  title: string;
  emoji: string;
  /** 완성하면 뭐가 되는지 한 줄 */
  goal: string;
  steps: TutorialStep[];
}
// ANCHOR: TUTORIAL_TYPES_END
```

- [ ] **Step 2: 검증 테스트 작성(실패 확인용)** — Create `src/lib/tutorial/__tests__/scripts.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { TUTORIALS, getTutorial } from "../scripts";

describe("tutorial scripts", () => {
  it("todo 대본이 존재하고 단계가 있다", () => {
    const todo = getTutorial("todo");
    expect(todo).toBeDefined();
    expect(todo!.steps.length).toBeGreaterThan(0);
  });

  it("모든 단계 id가 대본 안에서 유일하다", () => {
    for (const t of TUTORIALS) {
      const ids = t.steps.map((s) => s.id);
      expect(new Set(ids).size).toBe(ids.length);
    }
  });

  it("copy 단계는 copyText를, click/pasteSend/confirm 단계는 target을 가진다", () => {
    for (const t of TUTORIALS) {
      for (const s of t.steps) {
        if (s.kind === "copy") expect(s.copyText, `${t.id}/${s.id}`).toBeTruthy();
        else expect(s.target, `${t.id}/${s.id}`).toBeTruthy();
      }
    }
  });

  it("todo 대본은 안전 절반(체크포인트·guard검사·되돌리기 인지)을 포함한다", () => {
    const todo = getTutorial("todo")!;
    const dones = todo.steps.map((s) => s.done);
    expect(dones).toContain("checkpoint");
    expect(dones).toContain("guardChecked");
    // 되돌리기 인지: restore 버튼을 가리키는 단계가 있다
    expect(todo.steps.some((s) => s.target === "checkpoint-restore")).toBe(true);
  });
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/scripts.test.ts`
Expected: FAIL — `Cannot find module '../scripts'`.

- [ ] **Step 4: "할 일 목록" 대본 작성** — Create `src/lib/tutorial/scripts.ts`:

```ts
// ANCHOR: TUTORIAL_SCRIPTS_START
import type { Tutorial, TutorialId } from "./types";

const TODO: Tutorial = {
  id: "todo",
  title: "나만의 할 일 목록 앱 만들기",
  emoji: "✅",
  goal: "할 일을 적고, 다 하면 체크해서 지우는 나만의 웹앱",
  steps: [
    {
      id: "todo-1-copy",
      kind: "copy",
      say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.",
      why: "기획방은 AI에게 '무엇을 만들지' 설명하는 곳이에요.",
      goPage: "planning",
      done: "copy",
      copyText:
        "할 일을 입력해 추가하고, 목록으로 보여주고, 체크하면 지워지는 간단한 '할 일 목록' 웹앱을 HTML 파일 하나로 만들어줘.",
    },
    {
      id: "todo-2-send",
      kind: "pasteSend",
      say: "기획방 입력칸에 붙여넣고 보내보세요.",
      why: "AI가 무엇을 만들지 계획을 먼저 세워줘요.",
      target: "planning-send",
      goPage: "planning",
      done: "planResponded",
    },
    {
      id: "todo-3-checkpoint",
      kind: "click",
      say: "작업을 시키기 전에, 먼저 현재 상태를 저장해요. [체크포인트 저장]을 누르세요.",
      why: "AI에게 시키기 전에 저장해두면, 마음에 안 들 때 한 번에 되돌릴 수 있어요. VibeLign의 핵심 안전장치예요.",
      target: "checkpoint-save",
      goPage: "backups",
      done: "checkpoint",
    },
    {
      id: "todo-4-work",
      kind: "click",
      say: "이제 [AI에게 작업 시키기]를 누르세요.",
      why: "AI가 방금 세운 계획대로 실제 코드를 만들어요.",
      target: "work-run-ai",
      goPage: "work",
      done: "changedFiles",
    },
    {
      id: "todo-5-guard",
      kind: "click",
      say: "AI가 만든 게 안전한지 검사해요. [상태 확인]을 누르세요.",
      why: "VibeLign이 AI가 건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.",
      target: "home-guard-check",
      goPage: "home",
      done: "guardChecked",
    },
    {
      id: "todo-6-run",
      kind: "click",
      say: "이제 진짜 실행해볼 차례! [실행해보기]를 누르세요.",
      why: "방금 만든 앱이 실제로 돌아가는지 직접 봐요.",
      target: "run-app",
      goPage: "run",
      done: "runVerified",
    },
    {
      id: "todo-7-try",
      kind: "confirm",
      say: "할 일을 직접 하나 추가해보세요. 목록에 떴나요?",
      why: "이게 바로 당신이 만든 앱이에요. 직접 써보는 게 완성의 증거예요.",
      target: "run-app",
      goPage: "run",
      done: "manual",
    },
    {
      id: "todo-8-save",
      kind: "click",
      say: "마음에 들면 저장! [체크포인트 저장]을 다시 누르세요.",
      why: "좋은 상태를 저장해두면 다음에 또 여기서 시작할 수 있어요.",
      target: "checkpoint-save",
      goPage: "backups",
      done: "checkpoint",
    },
    {
      id: "todo-9-undo",
      kind: "confirm",
      say: "혹시 잘못 만들어도 괜찮아요. 여기 [되돌리기]를 누르면 저장 시점으로 언제든 돌아가요. 확인했으면 [알겠어요].",
      why: "되돌릴 수 있다는 안심 — 이게 VibeLign으로 겁 없이 AI 코딩하는 비결이에요.",
      target: "checkpoint-restore",
      goPage: "backups",
      done: "manual",
    },
  ],
};

export const TUTORIALS: Tutorial[] = [TODO];

export function getTutorial(id: TutorialId): Tutorial | undefined {
  return TUTORIALS.find((t) => t.id === id);
}
// ANCHOR: TUTORIAL_SCRIPTS_END
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/scripts.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add src/lib/tutorial/types.ts src/lib/tutorial/scripts.ts src/lib/tutorial/__tests__/scripts.test.ts
git commit -m "feat(tutorial): 베이비 모드 타입 + 할 일 목록 대본 + 형식 검증"
```

---

### Task 2: 단계 완료 자동 감지 (순수 함수, 기존 신호 재활용)

**Files:**
- Create: `src/lib/tutorial/completion.ts`
- Test: `src/lib/tutorial/__tests__/completion.test.ts`

**Interfaces:**
- Consumes: `GuideSignals` from `src/lib/nav/guide.ts`; `StepDone` from `./types`.
- Produces: `function isStepComplete(done: StepDone, s: GuideSignals): boolean`. `'copy'`와 `'manual'`은 항상 `false`(컴포넌트가 사용자 행동으로 직접 진행). 나머지는 신호 기반.

- [ ] **Step 1: 테스트 작성(실패 확인용)** — Create `src/lib/tutorial/__tests__/completion.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { isStepComplete } from "../completion";
import type { GuideSignals } from "../../nav/guide";

const base: GuideSignals = {
  hasPlanDoc: false,
  planningPending: false,
  hasCheckpoint: false,
  changedFileCount: null,
  guardStatus: null,
  runVerified: false,
};

describe("isStepComplete", () => {
  it("planResponded: 기획안이 생기면 완료", () => {
    expect(isStepComplete("planResponded", base)).toBe(false);
    expect(isStepComplete("planResponded", { ...base, hasPlanDoc: true })).toBe(true);
  });

  it("changedFiles: 변경 파일이 1개 이상이면 완료", () => {
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: 0 })).toBe(false);
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: null })).toBe(false);
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: 2 })).toBe(true);
  });

  it("checkpoint: 체크포인트가 있으면 완료", () => {
    expect(isStepComplete("checkpoint", { ...base, hasCheckpoint: true })).toBe(true);
  });

  it("guardChecked: guard 결과가 나오면(ok든 issue든) 완료", () => {
    expect(isStepComplete("guardChecked", base)).toBe(false);
    expect(isStepComplete("guardChecked", { ...base, guardStatus: "ok" })).toBe(true);
    expect(isStepComplete("guardChecked", { ...base, guardStatus: "issue" })).toBe(true);
  });

  it("runVerified: 실행 검증되면 완료", () => {
    expect(isStepComplete("runVerified", { ...base, runVerified: true })).toBe(true);
  });

  it("copy/manual: 신호로는 절대 자동 완료되지 않는다", () => {
    const full: GuideSignals = {
      hasPlanDoc: true, planningPending: false, hasCheckpoint: true,
      changedFileCount: 5, guardStatus: "ok", runVerified: true,
    };
    expect(isStepComplete("copy", full)).toBe(false);
    expect(isStepComplete("manual", full)).toBe(false);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/completion.test.ts`
Expected: FAIL — `Cannot find module '../completion'`.

- [ ] **Step 3: 구현** — Create `src/lib/tutorial/completion.ts`:

```ts
// ANCHOR: TUTORIAL_COMPLETION_START
import type { GuideSignals } from "../nav/guide";
import type { StepDone } from "./types";

/**
 * 한 단계의 done 신호가 충족됐는지 판정. 기존 GuideSignals를 재활용한다.
 * 'copy'/'manual'은 신호로 완료되지 않고 컴포넌트가 사용자 행동으로 진행한다.
 */
export function isStepComplete(done: StepDone, s: GuideSignals): boolean {
  switch (done) {
    case "planResponded":
      return s.hasPlanDoc;
    case "changedFiles":
      return (s.changedFileCount ?? 0) > 0;
    case "checkpoint":
      return s.hasCheckpoint;
    case "guardChecked":
      return s.guardStatus !== null;
    case "runVerified":
      return s.runVerified;
    case "copy":
    case "manual":
    default:
      return false;
  }
}
// ANCHOR: TUTORIAL_COMPLETION_END
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/completion.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/tutorial/completion.ts src/lib/tutorial/__tests__/completion.test.ts
git commit -m "feat(tutorial): 단계 완료 자동 감지(기존 GuideSignals 재활용)"
```

---

### Task 3: 진행 상태 훅 `useTutorial` (localStorage 영속)

**Files:**
- Create: `src/lib/tutorial/useTutorial.ts`
- Test: `src/lib/tutorial/__tests__/useTutorial.test.ts`

**Interfaces:**
- Consumes: `getTutorial`, `TUTORIALS` from `./scripts`; `Tutorial`, `TutorialStep`, `TutorialId` from `./types`.
- Produces:
  - `const TUTORIAL_ACTIVE_KEY = "vibelign.tutorial.active"`
  - `function tutorialProgressKey(id: TutorialId): string`
  - `interface TutorialState { active: Tutorial | null; stepIndex: number; step: TutorialStep | null; isComplete: boolean; start(id: TutorialId): void; advance(): void; exit(): void }`
  - `function useTutorial(): TutorialState`
  - `isComplete` is true when `stepIndex >= active.steps.length`. `step` is `null` when no active tutorial or when complete.

- [ ] **Step 1: 테스트 작성(실패 확인용)** — Create `src/lib/tutorial/__tests__/useTutorial.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTutorial, TUTORIAL_ACTIVE_KEY, tutorialProgressKey } from "../useTutorial";

beforeEach(() => localStorage.clear());

describe("useTutorial", () => {
  it("처음엔 활성 튜토리얼이 없다", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.active).toBeNull();
    expect(result.current.step).toBeNull();
  });

  it("start하면 첫 단계가 활성화되고 localStorage에 기록된다", () => {
    const { result } = renderHook(() => useTutorial());
    act(() => result.current.start("todo"));
    expect(result.current.active?.id).toBe("todo");
    expect(result.current.stepIndex).toBe(0);
    expect(result.current.step?.id).toBe("todo-1-copy");
    expect(localStorage.getItem(TUTORIAL_ACTIVE_KEY)).toContain("todo");
  });

  it("advance하면 다음 단계로 가고 진행률이 영속된다", () => {
    const { result } = renderHook(() => useTutorial());
    act(() => result.current.start("todo"));
    act(() => result.current.advance());
    expect(result.current.stepIndex).toBe(1);
    expect(localStorage.getItem(tutorialProgressKey("todo"))).toBe("1");
  });

  it("마지막 단계를 넘기면 isComplete=true, step=null", () => {
    const { result } = renderHook(() => useTutorial());
    act(() => result.current.start("todo"));
    const total = result.current.active!.steps.length;
    for (let i = 0; i < total; i++) act(() => result.current.advance());
    expect(result.current.isComplete).toBe(true);
    expect(result.current.step).toBeNull();
  });

  it("exit하면 활성 키가 지워진다", () => {
    const { result } = renderHook(() => useTutorial());
    act(() => result.current.start("todo"));
    act(() => result.current.exit());
    expect(result.current.active).toBeNull();
    expect(localStorage.getItem(TUTORIAL_ACTIVE_KEY)).toBeNull();
  });

  it("저장된 진행 상태를 새 마운트에서 복원한다", () => {
    localStorage.setItem(TUTORIAL_ACTIVE_KEY, JSON.stringify("todo"));
    localStorage.setItem(tutorialProgressKey("todo"), "2");
    const { result } = renderHook(() => useTutorial());
    expect(result.current.active?.id).toBe("todo");
    expect(result.current.stepIndex).toBe(2);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/useTutorial.test.ts`
Expected: FAIL — `Cannot find module '../useTutorial'`.

- [ ] **Step 3: 구현** — Create `src/lib/tutorial/useTutorial.ts` (`useGuide`의 localStorage read/write 패턴을 복제):

```ts
// ANCHOR: TUTORIAL_USE_TUTORIAL_START
import { useCallback, useEffect, useState } from "react";
import type { Tutorial, TutorialId, TutorialStep } from "./types";
import { getTutorial } from "./scripts";

export const TUTORIAL_ACTIVE_KEY = "vibelign.tutorial.active";

export function tutorialProgressKey(id: TutorialId): string {
  return `vibelign.tutorial.progress.${id}`;
}

function readActiveId(): TutorialId | null {
  try {
    const raw = localStorage.getItem(TUTORIAL_ACTIVE_KEY);
    if (!raw) return null;
    const id = JSON.parse(raw) as TutorialId;
    return getTutorial(id) ? id : null;
  } catch {
    return null;
  }
}

function readProgress(id: TutorialId): number {
  try {
    const raw = localStorage.getItem(tutorialProgressKey(id));
    const n = raw == null ? 0 : Number(raw);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  } catch {
    return 0;
  }
}

export interface TutorialState {
  active: Tutorial | null;
  stepIndex: number;
  step: TutorialStep | null;
  isComplete: boolean;
  start: (id: TutorialId) => void;
  advance: () => void;
  exit: () => void;
}

export function useTutorial(): TutorialState {
  const [activeId, setActiveId] = useState<TutorialId | null>(() => readActiveId());
  const [stepIndex, setStepIndex] = useState<number>(() => {
    const id = readActiveId();
    return id ? readProgress(id) : 0;
  });

  // activeId 변동 시 진행률 영속
  useEffect(() => {
    if (activeId) localStorage.setItem(tutorialProgressKey(activeId), String(stepIndex));
  }, [activeId, stepIndex]);

  const start = useCallback((id: TutorialId) => {
    localStorage.setItem(TUTORIAL_ACTIVE_KEY, JSON.stringify(id));
    localStorage.setItem(tutorialProgressKey(id), "0");
    setActiveId(id);
    setStepIndex(0);
  }, []);

  const advance = useCallback(() => {
    setStepIndex((i) => i + 1);
  }, []);

  const exit = useCallback(() => {
    localStorage.removeItem(TUTORIAL_ACTIVE_KEY);
    setActiveId(null);
    setStepIndex(0);
  }, []);

  const active = activeId ? getTutorial(activeId) ?? null : null;
  const total = active ? active.steps.length : 0;
  const isComplete = active != null && stepIndex >= total;
  const step = active && !isComplete ? active.steps[stepIndex] : null;

  return { active, stepIndex, step, isComplete, start, advance, exit };
}
// ANCHOR: TUTORIAL_USE_TUTORIAL_END
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/useTutorial.test.ts`
Expected: PASS (6 tests). (`renderHook`/`act`는 `@testing-library/react`에서 import — 이미 RTL 사용 중. 만약 미설치면 `npm i -D @testing-library/react`로 추가.)

- [ ] **Step 5: Commit**

```bash
git add src/lib/tutorial/useTutorial.ts src/lib/tutorial/__tests__/useTutorial.test.ts
git commit -m "feat(tutorial): 진행 상태 훅 useTutorial(localStorage 영속)"
```

---

### Task 4: 스포트라이트 위치 계산 (순수 함수)

**Files:**
- Create: `src/lib/tutorial/spotlight.ts`
- Test: `src/lib/tutorial/__tests__/spotlight.test.ts`

**Interfaces:**
- Produces:
  - `interface SpotRect { top: number; left: number; width: number; height: number }`
  - `function spotlightStyle(rect: SpotRect | null, pad?: number): { display: string; top: number; left: number; width: number; height: number }` — `rect`이 `null`이면 `display:"none"`. 있으면 `pad`(기본 8)만큼 사방 여백을 더해 구멍 위치 반환.

- [ ] **Step 1: 테스트 작성(실패 확인용)** — Create `src/lib/tutorial/__tests__/spotlight.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { spotlightStyle } from "../spotlight";

describe("spotlightStyle", () => {
  it("rect이 없으면 숨긴다", () => {
    expect(spotlightStyle(null)).toEqual({ display: "none", top: 0, left: 0, width: 0, height: 0 });
  });

  it("rect에 패딩을 더해 구멍 위치를 만든다", () => {
    const s = spotlightStyle({ top: 100, left: 50, width: 200, height: 40 }, 8);
    expect(s.display).toBe("block");
    expect(s.top).toBe(92);
    expect(s.left).toBe(42);
    expect(s.width).toBe(216);
    expect(s.height).toBe(56);
  });

  it("기본 패딩은 8이다", () => {
    const s = spotlightStyle({ top: 0, left: 0, width: 10, height: 10 });
    expect(s.width).toBe(26);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/spotlight.test.ts`
Expected: FAIL — `Cannot find module '../spotlight'`.

- [ ] **Step 3: 구현** — Create `src/lib/tutorial/spotlight.ts`:

```ts
// ANCHOR: TUTORIAL_SPOTLIGHT_START
export interface SpotRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface SpotStyle {
  display: string;
  top: number;
  left: number;
  width: number;
  height: number;
}

/** 대상 요소의 사각형 + 패딩 → 스포트라이트 구멍 위치. rect 없으면 숨김. */
export function spotlightStyle(rect: SpotRect | null, pad = 8): SpotStyle {
  if (!rect) return { display: "none", top: 0, left: 0, width: 0, height: 0 };
  return {
    display: "block",
    top: rect.top - pad,
    left: rect.left - pad,
    width: rect.width + pad * 2,
    height: rect.height + pad * 2,
  };
}
// ANCHOR: TUTORIAL_SPOTLIGHT_END
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/spotlight.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/tutorial/spotlight.ts src/lib/tutorial/__tests__/spotlight.test.ts
git commit -m "feat(tutorial): 스포트라이트 위치 계산 순수 함수"
```

---

### Task 5: 스포트라이트 오버레이 컴포넌트 `SpotlightTour`

**Files:**
- Create: `src/components/tutorial/SpotlightTour.tsx`
- Test: `src/components/tutorial/__tests__/SpotlightTour.test.tsx`
- Modify: `src/styles/brutalism.css` (앵커 끝에 튜토리얼 오버레이 클래스 추가 — 아래 Step 6)

**Interfaces:**
- Consumes: `GuideSignals`(`src/lib/nav/guide.ts`), `Page`(`src/lib/nav/stages.ts`), `Tutorial`/`TutorialStep`(`../../lib/tutorial/types`), `isStepComplete`(`../../lib/tutorial/completion`), `spotlightStyle`/`SpotRect`(`../../lib/tutorial/spotlight`).
- Produces: default export `SpotlightTour` with props:
  ```ts
  interface SpotlightTourProps {
    tutorial: Tutorial;
    stepIndex: number;
    step: TutorialStep;
    signals: GuideSignals;
    onAdvance: () => void;
    onExit: () => void;
    onNavigate: (page: Page) => void;
  }
  ```
- Behavior contract (tested):
  - 말풍선에 `step.say`를 보여준다. `step.why`가 있으면 `〔왜?〕` 접두로 보여준다.
  - 진행률 `"{stepIndex+1} / {tutorial.steps.length}"`를 보여준다.
  - "건너뛰기" 버튼 → `onAdvance()`.
  - `kind==='copy'`: [복사] 버튼 → `navigator.clipboard.writeText(step.copyText)` 후 `onAdvance()`.
  - `kind==='confirm'`: [알겠어요] 버튼 → `onAdvance()`.
  - `kind==='click' | 'pasteSend'`: 신호 감지로 진행 — `isStepComplete(step.done, signals)`가 true가 되면 `onAdvance()` (effect).
  - mount/step 변경 시 `step.goPage`가 있으면 `onNavigate(step.goPage)`.

- [ ] **Step 1: 테스트 작성(실패 확인용)** — Create `src/components/tutorial/__tests__/SpotlightTour.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SpotlightTour from "../SpotlightTour";
import type { GuideSignals } from "../../../lib/nav/guide";
import type { Tutorial } from "../../../lib/tutorial/types";

const signals: GuideSignals = {
  hasPlanDoc: false, planningPending: false, hasCheckpoint: false,
  changedFileCount: null, guardStatus: null, runVerified: false,
};

const tut: Tutorial = {
  id: "todo", title: "T", emoji: "✅", goal: "g",
  steps: [
    { id: "s1", kind: "copy", say: "복사하세요", why: "이유", done: "copy", copyText: "HELLO" },
    { id: "s2", kind: "click", say: "버튼 누르세요", target: "x", done: "checkpoint" },
    { id: "s3", kind: "confirm", say: "확인했나요?", target: "x", done: "manual" },
  ],
};

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

function setup(stepIndex: number, s: GuideSignals = signals, extra = {}) {
  const onAdvance = vi.fn();
  const onExit = vi.fn();
  const onNavigate = vi.fn();
  render(
    <SpotlightTour
      tutorial={tut}
      stepIndex={stepIndex}
      step={tut.steps[stepIndex]}
      signals={s}
      onAdvance={onAdvance}
      onExit={onExit}
      onNavigate={onNavigate}
      {...extra}
    />,
  );
  return { onAdvance, onExit, onNavigate };
}

describe("SpotlightTour", () => {
  it("say와 why, 진행률을 보여준다", () => {
    setup(0);
    expect(screen.getByText("복사하세요")).toBeTruthy();
    expect(screen.getByText(/이유/)).toBeTruthy();
    expect(screen.getByText("1 / 3")).toBeTruthy();
  });

  it("copy 단계: 복사 버튼이 클립보드에 쓰고 advance한다", async () => {
    const { onAdvance } = setup(0);
    fireEvent.click(screen.getByRole("button", { name: /복사/ }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("HELLO");
    await Promise.resolve();
    expect(onAdvance).toHaveBeenCalled();
  });

  it("건너뛰기는 advance한다", () => {
    const { onAdvance } = setup(1);
    fireEvent.click(screen.getByRole("button", { name: /건너뛰기/ }));
    expect(onAdvance).toHaveBeenCalled();
  });

  it("click 단계: 신호가 충족되면 자동 advance한다", () => {
    const { onAdvance } = setup(1, { ...signals, hasCheckpoint: true });
    expect(onAdvance).toHaveBeenCalled();
  });

  it("click 단계: 신호 미충족이면 advance하지 않는다", () => {
    const { onAdvance } = setup(1, signals);
    expect(onAdvance).not.toHaveBeenCalled();
  });

  it("confirm 단계: 알겠어요가 advance한다", () => {
    const { onAdvance } = setup(2);
    fireEvent.click(screen.getByRole("button", { name: /알겠어요/ }));
    expect(onAdvance).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npm run test -- src/components/tutorial/__tests__/SpotlightTour.test.tsx`
Expected: FAIL — `Cannot find module '../SpotlightTour'`.

- [ ] **Step 3: 구현** — Create `src/components/tutorial/SpotlightTour.tsx`:

```tsx
// ANCHOR: SPOTLIGHT_TOUR_START
import { useEffect, useLayoutEffect, useState } from "react";
import type { GuideSignals } from "../../lib/nav/guide";
import type { Page } from "../../lib/nav/stages";
import type { Tutorial, TutorialStep } from "../../lib/tutorial/types";
import { isStepComplete } from "../../lib/tutorial/completion";
import { spotlightStyle, type SpotRect } from "../../lib/tutorial/spotlight";

interface SpotlightTourProps {
  tutorial: Tutorial;
  stepIndex: number;
  step: TutorialStep;
  signals: GuideSignals;
  onAdvance: () => void;
  onExit: () => void;
  onNavigate: (page: Page) => void;
}

function readRect(target?: string): SpotRect | null {
  if (!target) return null;
  const el = document.querySelector(`[data-tour="${target}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

export default function SpotlightTour({
  tutorial, stepIndex, step, signals, onAdvance, onExit, onNavigate,
}: SpotlightTourProps) {
  const [rect, setRect] = useState<SpotRect | null>(null);

  // 이 단계가 요구하는 화면으로 데려다 놓기
  useEffect(() => {
    if (step.goPage) onNavigate(step.goPage);
  }, [step.id, step.goPage, onNavigate]);

  // 대상 요소 위치 추적(레이아웃/리사이즈/스크롤 반영)
  useLayoutEffect(() => {
    const update = () => setRect(readRect(step.target));
    update();
    const t = window.setTimeout(update, 120); // 화면 전환 후 재측정
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [step.id, step.target]);

  // 신호 기반 자동 진행(click/pasteSend)
  useEffect(() => {
    if ((step.kind === "click" || step.kind === "pasteSend") && isStepComplete(step.done, signals)) {
      onAdvance();
    }
  }, [step.id, step.kind, step.done, signals, onAdvance]);

  const hole = spotlightStyle(rect);
  const total = tutorial.steps.length;

  function handleCopy() {
    if (step.copyText) navigator.clipboard.writeText(step.copyText).catch(() => {});
    onAdvance();
  }

  return (
    <div className="tour-root" role="dialog" aria-label="튜토리얼">
      {/* 어두운 마스크 + 구멍(box-shadow 트릭) */}
      <div className="tour-spotlight" style={hole} />
      <div className="tour-bubble-wrap">
        <span className="guide-mascot pop">🧭</span>
        <div className="guide-bubble pop tour-bubble">
          <div className="tour-progress">{stepIndex + 1} / {total}</div>
          <p className="tour-say">{step.say}</p>
          {step.why && <p className="tour-why">〔왜?〕 {step.why}</p>}
          <div className="tour-actions">
            {step.kind === "copy" && (
              <button className="btn" onClick={handleCopy}>📋 복사</button>
            )}
            {step.kind === "confirm" && (
              <button className="btn" onClick={onAdvance}>알겠어요</button>
            )}
            <button className="tour-skip" onClick={onAdvance}>건너뛰기</button>
            <button className="tour-quit" onClick={onExit}>그만하기</button>
          </div>
        </div>
      </div>
    </div>
  );
}
// ANCHOR: SPOTLIGHT_TOUR_END
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npm run test -- src/components/tutorial/__tests__/SpotlightTour.test.tsx`
Expected: PASS (6 tests).

- [ ] **Step 5: 오버레이 CSS 추가** — `src/styles/brutalism.css`의 `BRUTALISM_CSS` 앵커 **END 직전**에 추가(기존 규칙 수정 금지, 새 규칙만 append):

```css
/* tutorial spotlight overlay */
.tour-root { position: fixed; inset: 0; z-index: 9000; pointer-events: none; }
.tour-spotlight {
  position: fixed;
  border-radius: 6px;
  box-shadow: 0 0 0 9999px rgba(26, 26, 26, 0.55);
  transition: top 0.15s, left 0.15s, width 0.15s, height 0.15s;
  pointer-events: none;
}
.tour-bubble-wrap {
  position: fixed; left: 24px; bottom: 24px;
  display: flex; align-items: flex-end; gap: 8px;
  max-width: 420px; pointer-events: auto;
}
.tour-bubble { display: flex; flex-direction: column; gap: 6px; }
.tour-progress { font-size: 12px; font-weight: 700; color: var(--primary); }
.tour-say { margin: 0; font-weight: 700; }
.tour-why { margin: 0; font-size: 13px; color: #5a5a5a; }
.tour-actions { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.tour-skip, .tour-quit {
  background: none; border: none; font-size: 12px; text-decoration: underline; cursor: pointer;
}
.tour-skip { color: #777; }
.tour-quit { color: var(--red); }
```

- [ ] **Step 6: 전체 테스트로 회귀 없음 확인**

Run: `npm run test`
Expected: 기존 테스트 + 신규 테스트 모두 PASS.

- [ ] **Step 7: Commit**

```bash
git add src/components/tutorial/SpotlightTour.tsx src/components/tutorial/__tests__/SpotlightTour.test.tsx src/styles/brutalism.css
git commit -m "feat(tutorial): 스포트라이트 오버레이 컴포넌트 + CSS"
```

---

### Task 6: 튜토리얼 선택 카드 `TutorialPicker`

**Files:**
- Create: `src/components/tutorial/TutorialPicker.tsx`
- Test: `src/components/tutorial/__tests__/TutorialPicker.test.tsx`

**Interfaces:**
- Consumes: `TUTORIALS`(`../../lib/tutorial/scripts`), `TutorialId`(`../../lib/tutorial/types`).
- Produces: default export `TutorialPicker` with props:
  ```ts
  interface TutorialPickerProps { onPick: (id: TutorialId) => void; onClose: () => void }
  ```
- Behavior: `TUTORIALS`의 각 항목을 카드로 렌더(emoji + title + goal). 카드 클릭 → `onPick(id)`. "나중에 할게요" → `onClose()`.
- 주의: 현재 `TUTORIALS`엔 `todo` 1개만 있다(Task 9에서 2개 추가). 테스트는 "1개 이상"으로 검증해 Task 9와 충돌하지 않게 한다.

- [ ] **Step 1: 테스트 작성(실패 확인용)** — Create `src/components/tutorial/__tests__/TutorialPicker.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TutorialPicker from "../TutorialPicker";
import { TUTORIALS } from "../../../lib/tutorial/scripts";

describe("TutorialPicker", () => {
  it("등록된 튜토리얼들을 카드로 보여준다", () => {
    render(<TutorialPicker onPick={() => {}} onClose={() => {}} />);
    for (const t of TUTORIALS) {
      expect(screen.getByText(t.title)).toBeTruthy();
    }
  });

  it("카드를 누르면 해당 id로 onPick한다", () => {
    const onPick = vi.fn();
    render(<TutorialPicker onPick={onPick} onClose={() => {}} />);
    fireEvent.click(screen.getByText(TUTORIALS[0].title));
    expect(onPick).toHaveBeenCalledWith(TUTORIALS[0].id);
  });

  it("'나중에 할게요'는 onClose한다", () => {
    const onClose = vi.fn();
    render(<TutorialPicker onPick={() => {}} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /나중에/ }));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npm run test -- src/components/tutorial/__tests__/TutorialPicker.test.tsx`
Expected: FAIL — `Cannot find module '../TutorialPicker'`.

- [ ] **Step 3: 구현** — Create `src/components/tutorial/TutorialPicker.tsx`:

```tsx
// ANCHOR: TUTORIAL_PICKER_START
import { TUTORIALS } from "../../lib/tutorial/scripts";
import type { TutorialId } from "../../lib/tutorial/types";

interface TutorialPickerProps {
  onPick: (id: TutorialId) => void;
  onClose: () => void;
}

export default function TutorialPicker({ onPick, onClose }: TutorialPickerProps) {
  return (
    <div className="tutpick-backdrop" role="dialog" aria-label="따라하며 만들기">
      <div className="tutpick-panel">
        <h2 className="tutpick-title">🧭 따라하며 앱 하나 만들어볼까요?</h2>
        <p className="tutpick-sub">버튼을 하나하나 눌러주는 대로 따라하면, 끝에 진짜 작동하는 앱이 남아요.</p>
        <div className="tutpick-cards">
          {TUTORIALS.map((t) => (
            <button key={t.id} className="tutpick-card" onClick={() => onPick(t.id)}>
              <span className="tutpick-emoji">{t.emoji}</span>
              <span className="tutpick-cardtitle">{t.title}</span>
              <span className="tutpick-goal">{t.goal}</span>
            </button>
          ))}
        </div>
        <button className="tour-skip" onClick={onClose}>나중에 할게요</button>
      </div>
    </div>
  );
}
// ANCHOR: TUTORIAL_PICKER_END
```

- [ ] **Step 4: 카드 CSS 추가** — `src/styles/brutalism.css`의 `BRUTALISM_CSS` 앵커 END 직전에 append:

```css
/* tutorial picker */
.tutpick-backdrop {
  position: fixed; inset: 0; z-index: 9100;
  background: rgba(26, 26, 26, 0.55);
  display: flex; align-items: center; justify-content: center;
}
.tutpick-panel {
  background: var(--bg); border: 3px solid var(--black); border-radius: 8px;
  padding: 24px; max-width: 720px; width: 90%;
  display: flex; flex-direction: column; gap: 12px; align-items: center;
}
.tutpick-title { margin: 0; }
.tutpick-sub { margin: 0; color: #5a5a5a; font-size: 14px; text-align: center; }
.tutpick-cards { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
.tutpick-card {
  display: flex; flex-direction: column; gap: 6px; align-items: flex-start;
  width: 200px; padding: 16px; cursor: pointer; text-align: left;
  background: var(--white); border: 2px solid var(--black); border-radius: 6px;
}
.tutpick-card:hover { background: #FFF6DC; }
.tutpick-emoji { font-size: 28px; }
.tutpick-cardtitle { font-weight: 700; }
.tutpick-goal { font-size: 12px; color: #5a5a5a; }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `npm run test -- src/components/tutorial/__tests__/TutorialPicker.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/components/tutorial/TutorialPicker.tsx src/components/tutorial/__tests__/TutorialPicker.test.tsx src/styles/brutalism.css
git commit -m "feat(tutorial): 튜토리얼 선택 카드 TutorialPicker"
```

---

### Task 7: 스포트라이트 대상 버튼에 `data-tour` 속성 부착

각 파일의 **주요 액션 버튼**(아래 표의 의미에 해당하는 `<button>`)에 `data-tour="..."` 속성만 추가한다. 기존 로직/스타일/앵커 변경 금지 — 속성 한 개 추가뿐.

**Files (Modify, 속성 추가만):**
- `src/pages/planning/PlanningPersonaComposer.tsx` — 메시지 전송 버튼 → `data-tour="planning-send"`
- `src/pages/BackupDashboard.tsx` — "체크포인트 저장" 버튼 → `data-tour="checkpoint-save"`
- `src/pages/BackupDashboard.tsx` — "되돌리기" 버튼 → `data-tour="checkpoint-restore"`
- `src/pages/WorkRoom.tsx` — "AI에게 작업 시키기" 메인 버튼 → `data-tour="work-run-ai"`
- `src/pages/Home.tsx` — "상태 확인" 버튼(SimpleHome 내 `handleRunGuard`) → `data-tour="home-guard-check"`
- `src/pages/RunPanel.tsx` — "실행" 메인 버튼 → `data-tour="run-app"`

**Interfaces:**
- Produces: DOM에 `[data-tour="planning-send" | "checkpoint-save" | "checkpoint-restore" | "work-run-ai" | "home-guard-check" | "run-app"]` 선택자가 존재. `SpotlightTour.readRect`가 이 선택자로 위치를 찾는다.

- [ ] **Step 1: 각 버튼 찾아 속성 추가**

각 파일에서 해당 버튼 JSX를 찾아 속성을 추가한다. 예(BackupDashboard 저장 버튼):

```tsx
// 변경 전
<button className="btn" onClick={handleSave}>체크포인트 저장</button>
// 변경 후
<button className="btn" data-tour="checkpoint-save" onClick={handleSave}>체크포인트 저장</button>
```

같은 방식으로 6개 버튼 전부에 표의 `data-tour` 값을 부착. (버튼 텍스트/핸들러로 식별: 전송→`planning-send`, 저장→`checkpoint-save`, 되돌리기→`checkpoint-restore`, AI 작업→`work-run-ai`, 상태 확인→`home-guard-check`, 실행→`run-app`.)

- [ ] **Step 2: 부착 확인용 grep**

Run: `grep -rn "data-tour=" src/pages`
Expected: 6개 매치(planning-send, checkpoint-save, checkpoint-restore, work-run-ai, home-guard-check, run-app).

- [ ] **Step 3: 회귀 테스트**

Run: `npm run test`
Expected: 모두 PASS(속성 추가는 기존 테스트에 영향 없음).

- [ ] **Step 4: Commit**

```bash
git add src/pages/planning/PlanningPersonaComposer.tsx src/pages/BackupDashboard.tsx src/pages/WorkRoom.tsx src/pages/Home.tsx src/pages/RunPanel.tsx
git commit -m "feat(tutorial): 스포트라이트 대상 버튼에 data-tour 속성 부착"
```

---

### Task 8: App 배선 — 오버레이 마운트 · GuideStrip 숨김 · 진입점 · 졸업

**Files:**
- Modify: `src/App.tsx` (APP 앵커 내, 최소 추가)
- Modify: `src/pages/Onboarding.tsx` (마지막 섹션에 "따라하며 만들기" 진입 버튼)
- Modify: `src/pages/Home.tsx` (StageHubCards 위에 "🧭 따라하며 만들기" 버튼)

**Interfaces:**
- Consumes: `useTutorial`(`./lib/tutorial/useTutorial`), `SpotlightTour`(`./components/tutorial/SpotlightTour`), `TutorialPicker`(`./components/tutorial/TutorialPicker`). App에 이미 있는 `navigate(next: Page)`, `guide`(useGuide 반환), GuideSignals 객체(482줄에서 useGuide에 넘기는 그 객체), `page` 상태.
- Produces: 튜토리얼 활성 시 `SpotlightTour`가 렌더되고 `GuideStrip`은 숨는다. 완주(`isComplete`) 시 `guide.setEnabled(true)` + 졸업 축하 + `tutorial.exit()`.

- [ ] **Step 1: App에 훅/상태 추가** — `src/App.tsx`에서 `useGuide` 호출(482줄) 부근 아래에 추가:

```tsx
const tutorial = useTutorial();
const [showPicker, setShowPicker] = useState(false);
const [tutorialGraduated, setTutorialGraduated] = useState(false);

// 튜토리얼 신호 객체 (useGuide에 넘기는 것과 동일 — 재사용)
const tutorialSignals = {
  hasPlanDoc: Boolean(planningResult?.outputPath),
  planningPending: planningPendingNow,
  hasCheckpoint: hasUserCheckpoint,
  changedFileCount,
  guardStatus,
  runVerified,
};
```

(상단 import 추가: `import { useTutorial } from "./lib/tutorial/useTutorial";` / `import SpotlightTour from "./components/tutorial/SpotlightTour";` / `import TutorialPicker from "./components/tutorial/TutorialPicker";`. `useState`는 이미 import됨.)

- [ ] **Step 2: 졸업 처리 effect 추가** — 같은 컴포넌트 본문에:

```tsx
useEffect(() => {
  if (tutorial.isComplete && !tutorialGraduated) {
    setTutorialGraduated(true);
    guide.setEnabled(true);   // 반응형 가이드로 졸업 인계
    tutorial.exit();
  }
}, [tutorial.isComplete, tutorialGraduated, guide, tutorial]);
```

- [ ] **Step 3: GuideStrip를 튜토리얼 중엔 숨기기** — `<GuideStrip ... />`(586줄)을 조건부로 감싼다:

```tsx
{!tutorial.active && (
  <GuideStrip
    /* ...기존 props 그대로... */
  />
)}
```

- [ ] **Step 4: 오버레이 + 피커 + 졸업 축하 마운트** — App의 최상위 반환 JSX 끝부분(다른 전역 오버레이들과 같은 레벨)에 추가:

```tsx
{tutorial.active && tutorial.step && (
  <SpotlightTour
    tutorial={tutorial.active}
    stepIndex={tutorial.stepIndex}
    step={tutorial.step}
    signals={tutorialSignals}
    onAdvance={tutorial.advance}
    onExit={tutorial.exit}
    onNavigate={navigate}
  />
)}
{showPicker && (
  <TutorialPicker
    onPick={(id) => { setShowPicker(false); setTutorialGraduated(false); tutorial.start(id); }}
    onClose={() => setShowPicker(false)}
  />
)}
{tutorialGraduated && (
  <div className="tutpick-backdrop" role="dialog" aria-label="졸업">
    <div className="tutpick-panel">
      <h2 className="tutpick-title">🎉 축하합니다 — 당신이 첫 앱을 완성했어요!</h2>
      <p className="tutpick-sub">방금 이 순서로 만든 거예요: 기획 → 저장 → AI 작업 → 검사 → 저장/되돌리기.<br/>이제 혼자 같은 순서로 무엇이든 만들 수 있어요.</p>
      <button className="btn" onClick={() => setTutorialGraduated(false)}>좋아요!</button>
    </div>
  </div>
)}
```

- [ ] **Step 5: Home에 진입 버튼 추가** — `src/pages/Home.tsx`에서 `StageHubCards` 렌더 직전에, 진입 콜백을 prop으로 받아 버튼 추가. Home이 콜백 prop이 없으면 `onStartTutorial?: () => void`를 props에 추가하고 App에서 `onStartTutorial={() => setShowPicker(true)}`로 전달:

```tsx
{onStartTutorial && (
  <button className="btn" data-tour="start-tutorial" onClick={onStartTutorial}>
    🧭 따라하며 만들기
  </button>
)}
```

- [ ] **Step 6: Onboarding 끝에 진입 제안 추가** — `src/pages/Onboarding.tsx`의 마지막 섹션(폴더 선택 이후, `ONBOARDING` 앵커 내)에, 완료 콜백이 호출되는 흐름 뒤 "처음이신가요? 따라하며 만들어볼까요?" 버튼을 둔다. App은 온보딩 완료 직후 `setShowPicker(true)`를 호출하도록 `onComplete` 핸들러에 한 줄 추가:

```tsx
// App.tsx의 onComplete 핸들러 내부, 프로젝트 오픈 처리 직후
setShowPicker(true);
```

(Onboarding 컴포넌트 자체엔 새 버튼이 꼭 필요치 않다 — 완료 직후 피커가 뜨면 진입 보장. Home 버튼은 "언제든 다시" 재진입 경로.)

- [ ] **Step 7: 빌드/타입 체크 + 전체 테스트**

Run: `npm run build` (또는 `npx tsc --noEmit`) 그리고 `npm run test`
Expected: 타입 에러 없음, 모든 테스트 PASS.

- [ ] **Step 8: Commit**

```bash
git add src/App.tsx src/pages/Home.tsx src/pages/Onboarding.tsx
git commit -m "feat(tutorial): App 배선 — 오버레이/피커 마운트, GuideStrip 숨김, 졸업 인계"
```

---

### Task 9: 방명록 · 퀴즈 게임 대본 추가

**Files:**
- Modify: `src/lib/tutorial/scripts.ts` (TUTORIALS 배열에 2개 추가, 기존 todo 변경 금지)
- Test: `src/lib/tutorial/__tests__/scripts.test.ts` (이미 모든 대본을 순회 검증하므로 자동 커버; 보강 1개 추가)

**Interfaces:**
- Consumes/Produces: 기존 `Tutorial` 타입. `TUTORIALS`가 `todo`, `guestbook`, `quiz` 3개를 포함.

- [ ] **Step 1: 두 대본을 todo와 같은 틀로 작성** — `scripts.ts`에 추가하고 `TUTORIALS` 배열에 포함. 각 대본도 §5 안전 절반(checkpoint·guardChecked·되돌리기 인지)을 포함:

```ts
const GUESTBOOK: Tutorial = {
  id: "guestbook",
  title: "방명록 웹페이지 만들기",
  emoji: "📖",
  goal: "누가 와서 이름과 한마디를 남길 수 있는 나만의 방명록 페이지",
  steps: [
    { id: "gb-1-copy", kind: "copy", say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.", why: "기획방은 AI에게 무엇을 만들지 설명하는 곳이에요.", goPage: "planning", done: "copy",
      copyText: "이름과 한마디를 입력해 남기면 아래 목록에 계속 쌓이는 간단한 '방명록' 웹페이지를 HTML 파일 하나로 만들어줘." },
    { id: "gb-2-send", kind: "pasteSend", say: "기획방 입력칸에 붙여넣고 보내보세요.", why: "AI가 무엇을 만들지 계획을 세워줘요.", target: "planning-send", goPage: "planning", done: "planResponded" },
    { id: "gb-3-checkpoint", kind: "click", say: "작업 전에 먼저 저장! [체크포인트 저장]을 누르세요.", why: "시키기 전에 저장해두면 언제든 되돌릴 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "gb-4-work", kind: "click", say: "[AI에게 작업 시키기]를 누르세요.", why: "AI가 계획대로 방명록을 만들어요.", target: "work-run-ai", goPage: "work", done: "changedFiles" },
    { id: "gb-5-guard", kind: "click", say: "안전한지 검사해요. [상태 확인]을 누르세요.", why: "건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.", target: "home-guard-check", goPage: "home", done: "guardChecked" },
    { id: "gb-6-run", kind: "click", say: "[실행해보기]를 눌러 직접 봐요.", why: "방명록이 실제로 뜨는지 확인해요.", target: "run-app", goPage: "run", done: "runVerified" },
    { id: "gb-7-try", kind: "confirm", say: "이름과 한마디를 직접 남겨보세요. 목록에 떴나요?", why: "직접 써보는 게 완성의 증거예요.", target: "run-app", goPage: "run", done: "manual" },
    { id: "gb-8-save", kind: "click", say: "마음에 들면 [체크포인트 저장]을 다시 누르세요.", why: "좋은 상태를 저장해두면 다음에 또 시작할 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "gb-9-undo", kind: "confirm", say: "잘못돼도 괜찮아요. [되돌리기]로 저장 시점으로 돌아갈 수 있어요. [알겠어요].", why: "되돌릴 수 있다는 안심이 겁 없이 만드는 비결이에요.", target: "checkpoint-restore", goPage: "backups", done: "manual" },
  ],
};

const QUIZ: Tutorial = {
  id: "quiz",
  title: "퀴즈 게임 만들기",
  emoji: "🎯",
  goal: "문제를 풀면 점수가 올라가는 나만의 퀴즈 게임",
  steps: [
    { id: "qz-1-copy", kind: "copy", say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.", why: "기획방은 AI에게 무엇을 만들지 설명하는 곳이에요.", goPage: "planning", done: "copy",
      copyText: "객관식 문제 3개를 풀면 맞힌 개수만큼 점수가 나오는 간단한 '퀴즈 게임'을 HTML 파일 하나로 만들어줘." },
    { id: "qz-2-send", kind: "pasteSend", say: "기획방 입력칸에 붙여넣고 보내보세요.", why: "AI가 무엇을 만들지 계획을 세워줘요.", target: "planning-send", goPage: "planning", done: "planResponded" },
    { id: "qz-3-checkpoint", kind: "click", say: "작업 전에 먼저 저장! [체크포인트 저장]을 누르세요.", why: "시키기 전에 저장해두면 언제든 되돌릴 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "qz-4-work", kind: "click", say: "[AI에게 작업 시키기]를 누르세요.", why: "AI가 계획대로 퀴즈를 만들어요.", target: "work-run-ai", goPage: "work", done: "changedFiles" },
    { id: "qz-5-guard", kind: "click", say: "안전한지 검사해요. [상태 확인]을 누르세요.", why: "건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.", target: "home-guard-check", goPage: "home", done: "guardChecked" },
    { id: "qz-6-run", kind: "click", say: "[실행해보기]를 눌러 직접 봐요.", why: "퀴즈가 실제로 도는지 확인해요.", target: "run-app", goPage: "run", done: "runVerified" },
    { id: "qz-7-try", kind: "confirm", say: "직접 퀴즈를 풀어보세요. 점수가 나왔나요?", why: "직접 해보는 게 완성의 증거예요.", target: "run-app", goPage: "run", done: "manual" },
    { id: "qz-8-save", kind: "click", say: "마음에 들면 [체크포인트 저장]을 다시 누르세요.", why: "좋은 상태를 저장해두면 다음에 또 시작할 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "qz-9-undo", kind: "confirm", say: "잘못돼도 괜찮아요. [되돌리기]로 저장 시점으로 돌아갈 수 있어요. [알겠어요].", why: "되돌릴 수 있다는 안심이 겁 없이 만드는 비결이에요.", target: "checkpoint-restore", goPage: "backups", done: "manual" },
  ],
};
```

그리고 배열 갱신:

```ts
export const TUTORIALS: Tutorial[] = [TODO, GUESTBOOK, QUIZ];
```

- [ ] **Step 2: 검증 테스트 보강** — `scripts.test.ts`에 추가:

```ts
it("3종 대본이 모두 등록돼 있다", () => {
  expect(TUTORIALS.map((t) => t.id).sort()).toEqual(["guestbook", "quiz", "todo"]);
});

it("모든 대본이 안전 절반을 포함한다", () => {
  for (const t of TUTORIALS) {
    const dones = t.steps.map((s) => s.done);
    expect(dones, t.id).toContain("checkpoint");
    expect(dones, t.id).toContain("guardChecked");
    expect(t.steps.some((s) => s.target === "checkpoint-restore"), t.id).toBe(true);
  }
});
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `npm run test -- src/lib/tutorial/__tests__/scripts.test.ts`
Expected: PASS (6 tests; 기존 4 + 신규 2).

- [ ] **Step 4: Commit**

```bash
git add src/lib/tutorial/scripts.ts src/lib/tutorial/__tests__/scripts.test.ts
git commit -m "feat(tutorial): 방명록·퀴즈 게임 대본 추가(안전 절반 포함)"
```

---

## 최종 검증 (전체 구현 후)

- [ ] `npm run test` 전체 PASS, `npm run build` (또는 `npx tsc --noEmit`) 타입 에러 없음.
- [ ] **실사용 육안 검증(spec §10):** 앱을 띄워 온보딩 → 피커 → "할 일 목록"을 *처음 보는 사람 입장*에서 끝까지 따라가, (a) 막힘 없이 진행되고 (b) 끝에 폴더에 진짜 작동하는 할 일 앱이 남고 (c) 졸업 축하가 뜨고 (d) 이후 반응형 GuideStrip이 다시 보이는지 확인. 화면 녹화 권장.
- [ ] **탈출구 확인:** 아무 단계에서나 "건너뛰기"가 다음으로 넘기고, "그만하기"가 튜토리얼을 종료하는지(절대 못 막히는지) 확인.
- [ ] **단계 원자성 리뷰:** 모든 단계가 행동 1개·판단 0개 원칙을 지키는지 대본 통독.

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지:** §3 단계 4종(Task 5), §4 스포트라이트(Task 5), §5 포맷+안전절반(Task 1·9), §6 시작 지점(Task 8), §7 졸업 두 박자(Task 8 — 완성경험은 todo-6/7 실행+직접써보기 단계 + 졸업 축하, 배운것 되짚기는 졸업 패널 문구), §8 재활용 지도(전 Task에서 import), §9 위험완화(탈출구=SpotlightTour 건너뛰기/그만하기, data-tour 누락 시 readRect null→spotlightStyle 숨김으로 폴백) 전부 대응됨.
- **Placeholder 스캔:** 모든 코드 스텝에 실제 코드 포함. Task 7의 버튼 위치는 "의미로 식별 + 정확한 data-tour 값"으로 지정(라인 번호는 리팩터링에 취약해 의미 식별이 더 안전).
- **타입 일관성:** `StepDone`(types.ts) ↔ `isStepComplete`(completion.ts) ↔ 대본 `done` 값 일치. `GuideSignals` 필드명은 실제 guide.ts와 일치. `useTutorial` 반환 타입 ↔ App/SpotlightTour 소비 일치.
