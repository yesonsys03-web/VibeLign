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
