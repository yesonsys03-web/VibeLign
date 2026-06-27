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
