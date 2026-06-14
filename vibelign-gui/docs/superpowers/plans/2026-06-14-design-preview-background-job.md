# 디자인 미리보기 백그라운드 생성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 디자인 목업 생성 작업 상태를 App 레벨 훅으로 끌어올려 탭 이동에도 살아남게 하고(결과 보존·앱 사용 가능), 다른 탭에선 상단 진행 칩으로 알리고 복귀하게 한다.

**Architecture:** 새 훅 `useDesignJob`이 생성 잡(status/phaseMsg/html/synth/error + run/recolor/reset)을 소유하고 App.tsx에서 인스턴스화된다. `DesignPreview`는 그 잡의 뷰가 되어 로컬 잡 상태를 버리고 폼 입력만 로컬로 유지한다. 셸엔 순수 함수 `designChipState`에 기반한 `DesignJobChip`이 렌더된다. Rust·invoke 래퍼 무변경.

**Tech Stack:** React + TypeScript, Vitest + @testing-library/react(renderHook 포함). 기존 모듈 재사용: `synthesizeStyle`/`generateDesignMockup`/`saveDesignMockup`(`src/lib/vib/design.ts`), `tokensToCssVars`/`replaceRootBlock`/`mergeStyleLists`/`EXAMPLE_CHIPS`(`src/lib/design-preview/customStyles.ts`), `StyleSpec`/`MotionSpec`/`DESIGN_STYLES`(`src/lib/design-preview/styles.ts`), `Page`(`src/lib/nav/stages.ts`).

**Spec:** `docs/superpowers/specs/2026-06-14-design-preview-background-job-design.md`

작업 디렉터리: 모든 명령은 `/Users/topsphinx/Documents/coding/VibeLign/vibelign-gui` 기준.

---

## File Structure
- Create `src/lib/design-preview/useDesignJob.ts` — 잡 훅 + `DesignJob`/`DesignRunParams`/`DesignJobStatus` 타입.
- Create `src/lib/design-preview/__tests__/useDesignJob.test.ts` — 훅 테스트.
- Create `src/lib/nav/designChip.ts` — `designChipState` 순수 함수 + `DesignChipState` 타입.
- Create `src/lib/nav/__tests__/designChip.test.ts` — 순수 함수 테스트.
- Create `src/components/nav/DesignJobChip.tsx` — 칩 컴포넌트.
- Modify `src/pages/DesignPreview.tsx` — `job` props 화, 로컬 잡 상태 제거(의도된 컴포넌트 리팩터).
- Modify `src/pages/__tests__/DesignPreview.test.tsx` — `useDesignJob` 하네스로 렌더 이전.
- Modify `src/App.tsx` — `useDesignJob` 인스턴스화, DesignPreview에 `job` 주입, 셸에 `DesignJobChip` 렌더.

---

## Task 1: `useDesignJob` 훅 (TDD)

**Files:**
- Create: `src/lib/design-preview/useDesignJob.ts`
- Test: `src/lib/design-preview/__tests__/useDesignJob.test.ts`

- [ ] **Step 1: 실패 테스트 작성** — `src/lib/design-preview/__tests__/useDesignJob.test.ts`:

```ts
import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach } from "vitest";

const mocks = vi.hoisted(() => ({ synth: vi.fn(), gen: vi.fn() }));
vi.mock("../../vib/design", () => ({
  synthesizeStyle: mocks.synth,
  generateDesignMockup: mocks.gen,
}));

import { useDesignJob } from "../useDesignJob";
import { DESIGN_STYLES } from "../styles";

const STYLE = DESIGN_STYLES[0];

beforeEach(() => {
  mocks.synth.mockReset();
  mocks.gen.mockReset();
});

describe("useDesignJob", () => {
  test("describe 흐름: idle→running→done, synth·html 세팅, gen은 synth 스타일로 호출", async () => {
    mocks.synth.mockResolvedValue({ ...STYLE, id: "synth1", name: "합성" });
    mocks.gen.mockResolvedValue({ html: "<h1>MOCK</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    expect(result.current.status).toBe("idle");
    act(() => result.current.run({ kind: "describe", description: "귀엽게" }, "plans/x.md"));
    expect(result.current.status).toBe("running");
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.html).toContain("MOCK");
    expect(result.current.synth?.id).toBe("synth1");
    expect(mocks.synth).toHaveBeenCalledWith(
      expect.objectContaining({ projectDir: "/tmp/p", planPath: "plans/x.md", description: "귀엽게" }),
    );
    expect(mocks.gen).toHaveBeenCalledWith(
      expect.objectContaining({ projectDir: "/tmp/p", planPath: "plans/x.md", style: expect.objectContaining({ id: "synth1" }) }),
    );
  });

  test("style 흐름: feedback·previousHtml 전달, synth 미설정", async () => {
    mocks.gen.mockResolvedValue({ html: "<h1>V2</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "style", style: STYLE, feedback: "버튼 크게", previousHtml: "<h1>V1</h1>" }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.html).toContain("V2");
    expect(result.current.synth).toBeNull();
    expect(mocks.gen).toHaveBeenCalledWith(
      expect.objectContaining({ style: STYLE, feedback: "버튼 크게", previousHtml: "<h1>V1</h1>" }),
    );
  });

  test("에러: gen 실패 시 status=error, error 메시지", async () => {
    mocks.gen.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "style", style: STYLE }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toContain("boom");
  });

  test("projectDir 변경 시 reset(idle)", async () => {
    mocks.gen.mockResolvedValue({ html: "<h1>X</h1>", cached: false });
    const { result, rerender } = renderHook(({ dir }) => useDesignJob(dir), { initialProps: { dir: "/tmp/a" } });
    act(() => result.current.run({ kind: "style", style: STYLE }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    rerender({ dir: "/tmp/b" });
    expect(result.current.status).toBe("idle");
    expect(result.current.html).toBeNull();
  });

  test("recolor: synth 토큰 변경 + html 갱신(gen 재호출 없음)", async () => {
    mocks.synth.mockResolvedValue({ ...STYLE, id: "s", name: "s" });
    mocks.gen.mockResolvedValue({ html: ":root{--x:1}\n<h1>M</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "describe", description: "x" }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    const before = result.current.html;
    act(() => result.current.recolor("primary", "#abcdef"));
    expect(result.current.synth?.tokens.primary).toBe("#abcdef");
    expect(result.current.html).not.toBe(before);
    expect(mocks.gen).toHaveBeenCalledTimes(1); // 재호출 없음
  });
});
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/lib/design-preview/__tests__/useDesignJob.test.ts`
  Expected: FAIL — "Cannot find module '../useDesignJob'" 또는 export 없음.

- [ ] **Step 3: 구현** — `src/lib/design-preview/useDesignJob.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from "react";
import type { StyleSpec } from "./styles";
import { synthesizeStyle, generateDesignMockup } from "../vib/design";
import { tokensToCssVars, replaceRootBlock } from "./customStyles";

export type DesignJobStatus = "idle" | "running" | "done" | "error";

export type RecolorKey = "bg" | "surface" | "primary" | "accent" | "text";

export type DesignRunParams =
  | { kind: "describe"; description: string; baseStyle?: StyleSpec }
  | { kind: "style"; style: StyleSpec; feedback?: string; previousHtml?: string };

export interface DesignJob {
  status: DesignJobStatus;
  phaseMsg: string;
  html: string | null;
  synth: StyleSpec | null;
  error: string | null;
  run: (params: DesignRunParams, planPath: string) => void;
  recolor: (key: RecolorKey, value: string) => void;
  reset: () => void;
}

export function useDesignJob(projectDir: string): DesignJob {
  const [status, setStatus] = useState<DesignJobStatus>("idle");
  const [phaseMsg, setPhaseMsg] = useState("");
  const [html, setHtml] = useState<string | null>(null);
  const [synth, setSynth] = useState<StyleSpec | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seqRef = useRef(0);

  const reset = useCallback(() => {
    seqRef.current += 1; // 진행 중 잡 결과 무효화
    setStatus("idle");
    setPhaseMsg("");
    setHtml(null);
    setSynth(null);
    setError(null);
  }, []);

  // 프로젝트 전환/종료 시 이전 잡 잔여 제거
  useEffect(() => {
    reset();
  }, [projectDir, reset]);

  const run = useCallback(
    (params: DesignRunParams, planPath: string) => {
      const runSeq = ++seqRef.current;
      const fresh = () => seqRef.current === runSeq;
      setStatus("running");
      setError(null);
      void (async () => {
        try {
          if (params.kind === "describe") {
            setPhaseMsg("① 클로드가 스타일을 구상하는 중…");
            const spec = await synthesizeStyle({
              projectDir,
              planPath,
              description: params.description,
              baseStyle: params.baseStyle,
            });
            if (!fresh()) return;
            setSynth(spec);
            setPhaseMsg("② 화면 목업을 그리는 중… (최대 1~2분 걸려요)");
            const res = await generateDesignMockup({ projectDir, planPath, style: spec });
            if (!fresh()) return;
            setHtml(res.html);
          } else {
            setPhaseMsg("디자인을 그리는 중… (최대 1~2분 걸려요)");
            const res = await generateDesignMockup({
              projectDir,
              planPath,
              style: params.style,
              feedback: params.feedback,
              previousHtml: params.previousHtml,
            });
            if (!fresh()) return;
            setHtml(res.html);
          }
          if (!fresh()) return;
          setStatus("done");
        } catch (e) {
          if (!fresh()) return;
          setError(String(e));
          setStatus("error");
        }
      })();
    },
    [projectDir],
  );

  const recolor = useCallback(
    (key: RecolorKey, value: string) => {
      if (!synth) return;
      const tokens = { ...synth.tokens, [key]: value };
      const updated = { ...synth, tokens };
      setSynth(updated);
      if (html) setHtml(replaceRootBlock(html, tokensToCssVars(tokens, updated.motion)));
    },
    [synth, html],
  );

  return { status, phaseMsg, html, synth, error, run, recolor, reset };
}
```

- [ ] **Step 4: 통과 확인** — `npx vitest run src/lib/design-preview/__tests__/useDesignJob.test.ts`
  Expected: PASS (5 tests).

- [ ] **Step 5: 커밋**
```bash
cd /Users/topsphinx/Documents/coding/VibeLign && git add vibelign-gui/src/lib/design-preview/useDesignJob.ts vibelign-gui/src/lib/design-preview/__tests__/useDesignJob.test.ts
git commit -m "feat(design-preview): useDesignJob 훅 — 생성 잡 상태(앱 수명) 분리

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `designChipState` 순수 함수 (TDD)

**Files:**
- Create: `src/lib/nav/designChip.ts`
- Test: `src/lib/nav/__tests__/designChip.test.ts`

- [ ] **Step 1: 실패 테스트 작성** — `src/lib/nav/__tests__/designChip.test.ts`:

```ts
import { describe, test, expect } from "vitest";
import { designChipState } from "../designChip";

describe("designChipState", () => {
  test("running·타페이지 → busy 칩", () => {
    const s = designChipState("running", "home");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("busy");
    expect(s.label).toContain("생성 중");
  });
  test("done·타페이지 → done 칩", () => {
    const s = designChipState("done", "work");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("done");
    expect(s.label).toContain("완성");
  });
  test("error·타페이지 → error 칩", () => {
    const s = designChipState("error", "work");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("error");
    expect(s.label).toContain("실패");
  });
  test("design-preview 페이지에선 어떤 상태든 숨김", () => {
    expect(designChipState("running", "design-preview").visible).toBe(false);
    expect(designChipState("done", "design-preview").visible).toBe(false);
    expect(designChipState("error", "design-preview").visible).toBe(false);
  });
  test("idle → 숨김", () => {
    expect(designChipState("idle", "home").visible).toBe(false);
  });
});
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/lib/nav/__tests__/designChip.test.ts`
  Expected: FAIL — module 없음.

- [ ] **Step 3: 구현** — `src/lib/nav/designChip.ts`:

```ts
import type { Page } from "./stages";
import type { DesignJobStatus } from "../design-preview/useDesignJob";

export interface DesignChipState {
  visible: boolean;
  tone?: "busy" | "done" | "error";
  label?: string;
}

/** 디자인 생성 잡의 상태/현재 페이지로 상단 칩 표시를 결정. design-preview 페이지에선 페이지 내 패널이 보이므로 칩 숨김. */
export function designChipState(status: DesignJobStatus, page: Page): DesignChipState {
  if (page === "design-preview") return { visible: false };
  if (status === "running") return { visible: true, tone: "busy", label: "🎨 디자인 생성 중…" };
  if (status === "done") return { visible: true, tone: "done", label: "✓ 디자인 완성 — 보기" };
  if (status === "error") return { visible: true, tone: "error", label: "⚠ 디자인 생성 실패 — 보기" };
  return { visible: false };
}
```

- [ ] **Step 4: 통과 확인** — `npx vitest run src/lib/nav/__tests__/designChip.test.ts`
  Expected: PASS (5 tests).

- [ ] **Step 5: 커밋**
```bash
cd /Users/topsphinx/Documents/coding/VibeLign && git add vibelign-gui/src/lib/nav/designChip.ts vibelign-gui/src/lib/nav/__tests__/designChip.test.ts
git commit -m "feat(design-preview): designChipState — 진행 칩 표시 결정 순수 함수

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `DesignJobChip` 컴포넌트 (TDD)

**Files:**
- Create: `src/components/nav/DesignJobChip.tsx`
- Test: `src/components/nav/__tests__/DesignJobChip.test.tsx`

- [ ] **Step 1: 실패 테스트 작성** — `src/components/nav/__tests__/DesignJobChip.test.tsx`:

```tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, test, expect, vi } from "vitest";
import { DesignJobChip } from "../DesignJobChip";

afterEach(cleanup);

describe("DesignJobChip", () => {
  test("running·타페이지면 칩이 보이고 클릭 시 onOpen", () => {
    const onOpen = vi.fn();
    render(<DesignJobChip status="running" page="home" onOpen={onOpen} />);
    const btn = screen.getByRole("button", { name: /생성 중/ });
    fireEvent.click(btn);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  test("design-preview 페이지면 렌더 안 함", () => {
    const { container } = render(<DesignJobChip status="running" page="design-preview" onOpen={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  test("idle이면 렌더 안 함", () => {
    const { container } = render(<DesignJobChip status="idle" page="home" onOpen={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/components/nav/__tests__/DesignJobChip.test.tsx`
  Expected: FAIL — module 없음.

- [ ] **Step 3: 구현** — `src/components/nav/DesignJobChip.tsx`:

```tsx
import { designChipState } from "../../lib/nav/designChip";
import type { DesignJobStatus } from "../../lib/design-preview/useDesignJob";
import type { Page } from "../../lib/nav/stages";

interface Props {
  readonly status: DesignJobStatus;
  readonly page: Page;
  readonly onOpen: () => void;
}

export function DesignJobChip({ status, page, onOpen }: Props) {
  const s = designChipState(status, page);
  if (!s.visible) return null;
  const bg = s.tone === "error" ? "#FEE2E2" : s.tone === "done" ? "#DCFCE7" : "#F5F1E3";
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        margin: "0 12px 8px",
        padding: "6px 12px",
        border: "2px solid #1A1A1A",
        background: bg,
        fontSize: 13,
        fontWeight: 800,
        cursor: "pointer",
        alignSelf: "flex-start",
      }}
    >
      {s.tone === "busy" && <span className="spinner" />}
      {s.label}
    </button>
  );
}
```

- [ ] **Step 4: 통과 확인** — `npx vitest run src/components/nav/__tests__/DesignJobChip.test.tsx`
  Expected: PASS (3 tests).

- [ ] **Step 5: 커밋**
```bash
cd /Users/topsphinx/Documents/coding/VibeLign && git add vibelign-gui/src/components/nav/DesignJobChip.tsx vibelign-gui/src/components/nav/__tests__/DesignJobChip.test.tsx
git commit -m "feat(design-preview): DesignJobChip — 셸 상단 진행/완료 칩

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `DesignPreview`를 잡 뷰로 리팩터 + 기존 테스트 이전

**Files:**
- Modify: `src/pages/DesignPreview.tsx` (전체 교체 — 의도된 컴포넌트 리팩터)
- Modify: `src/pages/__tests__/DesignPreview.test.tsx`

- [ ] **Step 1: 테스트를 하네스 렌더로 이전** — `src/pages/__tests__/DesignPreview.test.tsx` 상단 import와 4개 `render(...)` 호출을 수정.

(a) import 블록 바로 아래(`vi.mock(...)` 다음, `afterEach` 위)에 하네스 추가. 기존 import에 다음을 더한다:
```tsx
import { useDesignJob } from "../../lib/design-preview/useDesignJob";
import type { ComponentProps } from "react";

function Harness(props: Omit<ComponentProps<typeof DesignPreview>, "job">) {
  const job = useDesignJob(props.projectDir);
  return <DesignPreview {...props} job={job} />;
}
```
(b) 4개 테스트의 `render(<DesignPreview ... />)` 를 모두 `render(<Harness ... />)` 로 바꾼다(같은 props, `job` 은 하네스가 주입). 즉:
- `render(<DesignPreview projectDir="/tmp/demo" planPath="plans/x.md" isLikelyWeb onBack={vi.fn()} onConfirm={vi.fn()} />)` → `render(<Harness projectDir="/tmp/demo" planPath="plans/x.md" isLikelyWeb onBack={vi.fn()} onConfirm={vi.fn()} />)`
- 비웹 테스트: `isLikelyWeb={false}` 도 동일하게 `Harness` 로.
- 확정 테스트: `onConfirm={onConfirm}` 도 동일하게 `Harness` 로.

> 근거: `vi.mock("../../lib/vib/design", ...)` 은 해석된 모듈을 모킹하므로, 훅이 `../vib/design`(=동일 모듈)을 import해도 동일 모킹이 적용된다. 따라서 하네스를 통해도 generate/synthesize/save 흐름이 그대로 모킹됨.

- [ ] **Step 2: 실패 확인** — `npx vitest run src/pages/__tests__/DesignPreview.test.tsx`
  Expected: FAIL — `DesignPreview` 가 아직 `job` prop을 받지 않음(타입/런타임 에러) 또는 `loading` 기반 동작 불일치.

- [ ] **Step 3: 구현** — `src/pages/DesignPreview.tsx` 전체를 아래로 교체:

```tsx
import { useEffect, useState } from "react";
import { DESIGN_STYLES, type StyleSpec, type MotionSpec } from "../lib/design-preview/styles";
import { saveDesignMockup, listCustomStyles, saveCustomStyle, deleteCustomStyle } from "../lib/vib/design";
import { EXAMPLE_CHIPS, mergeStyleLists } from "../lib/design-preview/customStyles";
import type { DesignJob } from "../lib/design-preview/useDesignJob";

export interface DesignBinding {
  readonly mockupPath: string;
  readonly tokens: StyleSpec["tokens"];
  readonly motion?: MotionSpec;
}

interface Props {
  readonly projectDir: string;
  readonly planPath: string;
  /** 웹 UI로 보이는 프로젝트인지(웹 게이트). false면 경고 배너(비차단). */
  readonly isLikelyWeb: boolean;
  /** App 레벨 생성 잡(탭 이동에도 살아남음). */
  readonly job: DesignJob;
  readonly onBack: () => void;
  readonly onConfirm: (binding: DesignBinding) => void;
}

export default function DesignPreview({ projectDir, planPath, isLikelyWeb, job, onBack, onConfirm }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [describe, setDescribe] = useState("");
  const [custom, setCustom] = useState<StyleSpec[]>([]);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  useEffect(() => {
    listCustomStyles(projectDir).then(setCustom).catch(() => setCustom([]));
  }, [projectDir]);
  const allStyles = mergeStyleLists(DESIGN_STYLES, custom);
  const customIds = new Set(custom.map((s) => s.id));
  const selected = selectedId ? allStyles.find((s) => s.id === selectedId) : undefined;
  const running = job.status === "running";

  function createFromDescription(baseStyle?: StyleSpec) {
    const desc = describe.trim();
    if (!desc && !baseStyle) return;
    setSavedMsg(null);
    setConfirmError(null);
    job.run({ kind: "describe", description: desc, baseStyle }, planPath);
  }

  function generate(useFeedback: boolean) {
    const style = job.synth ?? selected;
    if (!style) return;
    setConfirmError(null);
    job.run(
      {
        kind: "style",
        style,
        feedback: useFeedback ? feedback.trim() : undefined,
        previousHtml: useFeedback ? (job.html ?? undefined) : undefined,
      },
      planPath,
    );
  }

  async function confirm() {
    const style = job.synth ?? selected;
    if (!style || !job.html) return;
    try {
      const mockupPath = await saveDesignMockup({ projectDir, styleId: style.id, html: job.html });
      onConfirm({ mockupPath, tokens: style.tokens, motion: style.motion });
      job.reset(); // 디자인 확정 후 잡 소비 — 잔여 "완성" 칩 방지
    } catch (e) {
      setConfirmError(String(e));
    }
  }

  return (
    <div className="page-content" style={{ height: "100%" }}>
      <button onClick={onBack}>← 뒤로</button>
      <h2>디자인 미리보기</h2>
      {!isLikelyWeb && (
        <p role="alert" style={{ background: "#FFF7E6", border: "1px solid #FFD591", padding: 8 }}>
          웹 UI 프로젝트가 아닐 수 있어요 — 디자인 미리보기는 웹 화면 기준입니다. 계속할 수 있어요.
        </p>
      )}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {allStyles.map((s) => (
          <button key={s.id} onClick={() => { setSelectedId(s.id); }} aria-pressed={selectedId === s.id}
            style={{ border: selectedId === s.id ? "2px solid #111" : "1px solid #ccc", padding: 12 }}>
            <strong>{s.name}</strong>
            <div>{s.description}</div>
            {customIds.has(s.id) && (
              <span
                role="button"
                aria-label={`${s.name} 삭제`}
                onClick={(e) => {
                  e.stopPropagation();
                  void deleteCustomStyle({ projectDir, styleId: s.id }).then(() =>
                    listCustomStyles(projectDir).then(setCustom),
                  );
                }}
                style={{ fontSize: 11, color: "#b42318", fontWeight: 800, cursor: "pointer" }}
              >
                ✕ 삭제
              </span>
            )}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A", display: "grid", gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 900 }}>✏️ 직접 만들기 — 원하는 느낌을 그냥 말로 적어보세요</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {EXAMPLE_CHIPS.map((chip) => (
            <button key={chip} type="button" onClick={() => setDescribe(chip)}
              style={{ fontSize: 12, padding: "4px 10px", border: "2px solid #1A1A1A", background: "#fff", borderRadius: 999 }}>
              {chip}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input aria-label="디자인 묘사" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder="예: 귀엽고 파스텔톤으로"
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || running} onClick={() => createFromDescription()}
            style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
            {running ? "클로드가 그리는 중…" : "✦ 클로드에게 그려달라기"}
          </button>
        </div>
      </div>
      <button disabled={(!selected && !job.synth) || running} onClick={() => generate(false)}>
        {running ? "그리는 중…" : "이 스타일로 그려보기"}
      </button>
      {selected && !job.synth && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input aria-label="스타일 변형" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder={`예: "${selected.name}" 에서 더 밝게 / 더 미니멀하게`}
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || running} onClick={() => createFromDescription(selected)}>
            ✦ 이 스타일 변형하기
          </button>
        </div>
      )}
      {(job.error || confirmError) && <p style={{ color: "crimson" }}>{job.error || confirmError}</p>}
      {running && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10, padding: "12px 14px", border: "2px solid #1A1A1A", background: "#F5F1E3" }}>
          <span className="spinner" />
          <div>
            <div style={{ fontSize: 13, fontWeight: 900 }}>{job.phaseMsg || "클로드가 작업 중…"}</div>
            <div style={{ fontSize: 12, color: "#666" }}>⏳ 멈춘 게 아니에요 — 다른 탭을 써도 돼요. 끝나면 알려드려요.</div>
          </div>
        </div>
      )}
      {job.html && (
        <>
          {job.synth && (
            <div style={{ border: "2px solid #1A1A1A", padding: "10px 12px", marginBottom: 8, background: "#F5F1E3", display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 900 }}>✦ 이런 스타일을 만들었어요 — {job.synth.name}</div>
              <div style={{ fontSize: 12, color: "#444" }}>{job.synth.description}</div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {([
                  { key: "bg", label: "배경" },
                  { key: "surface", label: "표면" },
                  { key: "primary", label: "주요" },
                  { key: "accent", label: "강조" },
                  { key: "text", label: "글자" },
                ] as const).map(({ key, label }) => {
                  const c = job.synth!.tokens[key];
                  const hex = /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#ffffff";
                  return (
                    <label key={key} title={`${label} — 클릭해 색 바꾸기 (${c})`}
                      style={{ position: "relative", width: 28, height: 28, display: "inline-block", cursor: "pointer" }}>
                      <span style={{ display: "block", width: 28, height: 28, background: c, border: "1px solid #1A1A1A", borderRadius: 4 }} />
                      <input type="color" aria-label={`${label} 색 바꾸기`} value={hex}
                        onChange={(e) => job.recolor(key, e.target.value)}
                        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0, border: 0, padding: 0, cursor: "pointer" }} />
                    </label>
                  );
                })}
                <span style={{ fontSize: 11, color: "#888" }}>✎ 색을 클릭해 바꿔보세요</span>
              </div>
              {job.synth.motion && <div style={{ fontSize: 11, color: "#666" }}>모션: {job.synth.motion.recipe}</div>}
            </div>
          )}
          <iframe title="디자인 목업" srcDoc={job.html} sandbox="" style={{ width: "100%", height: 600, border: "1px solid #ddd" }} />
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A" }}>
            <input aria-label="수정 요청" value={feedback} onChange={(e) => setFeedback(e.target.value)}
              placeholder="예: 여긴 빨강, 버튼 크게"
              style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
            <button className="btn" disabled={running || !feedback.trim()} onClick={() => generate(true)}
              style={{ fontWeight: 800 }}>
              ↻ 다시 그리기
            </button>
            <button className="btn" onClick={() => void confirm()}
              style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
              ✓ 이 디자인으로 만들기
            </button>
            {job.synth && (
              <button className="btn" disabled={running} onClick={() => {
                void saveCustomStyle({ projectDir, style: job.synth! })
                  .then(() => listCustomStyles(projectDir).then(setCustom))
                  .then(() => setSavedMsg("스타일을 저장했어요 — 목록에서 다시 쓸 수 있어요"))
                  .catch((e) => setConfirmError(String(e)));
              }}>
                ＋ 이 스타일 저장하기
              </button>
            )}
            {savedMsg && <span style={{ fontSize: 12, fontWeight: 800, color: "#166534", alignSelf: "center" }}>{savedMsg}</span>}
          </div>
        </>
      )}
    </div>
  );
}
```

> 주요 변경: 로컬 `loading`/`loadingMsg`/`error`/`synth`/`html` 제거 → `job.*` 사용. `selectedId` 선택 시 더 이상 `setSynth(null)` 안 함(synth는 job 소유; 프리셋 선택은 `job.synth ?? selected` 로 자연 우선순위). 색 클릭은 `job.recolor`. 확정 성공 시 `job.reset()`. 저장/확정 실패는 별도 `confirmError` 로 표시(생성 에러 `job.error` 와 같은 자리).

- [ ] **Step 4: 통과 확인** — `npx vitest run src/pages/__tests__/DesignPreview.test.tsx && npx tsc --noEmit`
  Expected: 기존 4 테스트 PASS, tsc 클린.

- [ ] **Step 5: 커밋**
```bash
cd /Users/topsphinx/Documents/coding/VibeLign && git add vibelign-gui/src/pages/DesignPreview.tsx vibelign-gui/src/pages/__tests__/DesignPreview.test.tsx
git commit -m "refactor(design-preview): DesignPreview를 useDesignJob 뷰로 — 잡 상태 외부화

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: App.tsx 배선 + 전체 검증

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: import 추가** — `src/App.tsx` 의 import 영역(예: `import DesignPreview, { type DesignBinding } from "./pages/DesignPreview";` 라인 부근, 약 line 42)에 두 줄 추가:
```tsx
import { useDesignJob } from "./lib/design-preview/useDesignJob";
import { DesignJobChip } from "./components/nav/DesignJobChip";
```

- [ ] **Step 2: 훅 인스턴스화** — `const [page, setPage] = useState<Page>("home");`(약 line 92) 다음 줄에 추가:
```tsx
  const designJob = useDesignJob(projectDir ?? "");
```
(`projectDir` 는 `string | null` 이므로 `?? ""` 로 넘긴다. null→"" 전환 시 훅이 reset.)

- [ ] **Step 3: DesignPreview에 job 주입** — `<DesignPreview ... />`(약 line 627-634)의 props에 `job={designJob}` 추가:
```tsx
                  <DesignPreview
                    projectDir={projectDir}
                    planPath={designPlanPath}
                    isLikelyWeb={designIsWeb}
                    job={designJob}
                    onBack={() => navigate("plan-doc")}
                    onConfirm={(b) => { setDesignBinding(b); navigate("work"); }}
                  />
```

- [ ] **Step 4: 셸에 칩 렌더** — `<GuideStrip ... />` 블록(약 line 574-589)의 닫는 `/>` 바로 다음 줄에 추가:
```tsx
            <DesignJobChip status={designJob.status} page={page} onOpen={() => navigate("design-preview")} />
```

- [ ] **Step 5: 타입·전체 테스트** — `npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests "`
  Expected: tsc 클린, 전체 테스트 통과(기존 287 + 신규 13 = 300 부근).

- [ ] **Step 6: 커밋**
```bash
cd /Users/topsphinx/Documents/coding/VibeLign && git add vibelign-gui/src/App.tsx
git commit -m "feat(design-preview): App에 useDesignJob 배선 + 셸 진행 칩

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: 수동 통합 검증(보고만, 커밋 없음)** — `npm run tauri dev` 로 앱을 띄워:
  1. 기획안 있는 프로젝트에서 디자인 미리보기 → "그려달라기" 클릭(진행 패널 표시·입력 잠금 확인).
  2. 생성 중 다른 탭(예: 홈/개발)로 이동 → 상단 "🎨 디자인 생성 중…" 칩 등장 확인.
  3. 완료까지 대기 → 칩이 "✓ 디자인 완성 — 보기"로 변경 확인.
  4. 칩 클릭 → 디자인 탭 복귀, 목업이 그대로 표시 확인.
  (실기기 수동 — 자동 테스트로 대체 불가한 부분만.)

---

## Self-Review (작성자 점검 완료)
- **스펙 커버리지**: §3-1 useDesignJob→Task1, §3-2 DesignPreview 뷰화→Task4, §3-3 칩(designChipState/DesignJobChip)→Task2·3, App 배선→Task5, recolor 응집→Task1(recolor 액션)+Task4(호출), reset-on-projectDir→Task1, stale 가드(시퀀스 ref)→Task1, 확정 후 소비(job.reset)→Task4, 테스트(§5)→각 Task TDD + Task5 전체. 매핑 완료.
- **플레이스홀더 없음**: 모든 코드/명령/기대 구체.
- **타입 일관**: `DesignJob{status,phaseMsg,html,synth,error,run,recolor,reset}`·`DesignRunParams`(describe|style)·`DesignJobStatus`·`RecolorKey` 정의(Task1)=사용(Task3·4·5)·테스트 일치. `designChipState(status, page): DesignChipState{visible,tone?,label?}` 정의(Task2)=사용(Task3). `run(params, planPath)` 시그니처 정의(Task1)=호출(Task4) 일치. `DesignPreview` props에 `job: DesignJob` 추가(Task4)=주입(Task5) 일치.
- **위험**: vi.mock 경로(`../../lib/vib/design`)가 훅의 `../vib/design` import와 동일 모듈로 해석됨(Task4 근거 명시). projectDir null→"" 처리(Task5 Step2). 확정 후 job.reset로 stale 칩 방지(Task4).
