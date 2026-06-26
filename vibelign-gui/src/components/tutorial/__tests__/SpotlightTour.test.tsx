import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
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

afterEach(() => {
  cleanup();
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
