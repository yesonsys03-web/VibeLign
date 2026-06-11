// === ANCHOR: NAV_USE_GUIDE_START ===
// guide.ts 순수 로직의 React 바인딩 — localStorage 영속(전역 토글 + 프로젝트별 override).
import { useEffect, useMemo, useState } from "react";
import {
  GUIDE_ENABLED_KEY,
  guideOverrideKey,
  inferStep,
  resolveOverride,
  type ActiveGuideStep,
  type GuideOverride,
  type GuideSignals,
} from "./guide";

function readOverride(projectDir: string): GuideOverride | null {
  try {
    const raw = localStorage.getItem(guideOverrideKey(projectDir));
    return raw ? (JSON.parse(raw) as GuideOverride) : null;
  } catch {
    return null;
  }
}

export interface GuideState {
  enabled: boolean;
  /** 현재 단계. null = 신호 로딩 전(렌더 금지, spec §4-4) 또는 프로젝트 없음 */
  step: ActiveGuideStep | null;
  setStep: (next: ActiveGuideStep) => void;
  setEnabled: (on: boolean) => void;
}

export function useGuide(
  projectDir: string | null,
  signals: GuideSignals,
  signalsReady: boolean,
): GuideState {
  const [enabled, setEnabledState] = useState(
    () => localStorage.getItem(GUIDE_ENABLED_KEY) !== "0",
  );
  const [override, setOverride] = useState<GuideOverride | null>(null);

  useEffect(() => {
    setOverride(projectDir ? readOverride(projectDir) : null);
  }, [projectDir]);

  const inferred = useMemo(() => inferStep(signals), [signals]);
  const step = resolveOverride(override, inferred);

  function setStep(next: ActiveGuideStep) {
    const o: GuideOverride = { step: next, baseInferred: inferred };
    setOverride(o);
    if (projectDir) localStorage.setItem(guideOverrideKey(projectDir), JSON.stringify(o));
  }

  function setEnabled(on: boolean) {
    setEnabledState(on);
    localStorage.setItem(GUIDE_ENABLED_KEY, on ? "1" : "0");
  }

  return {
    enabled,
    step: projectDir && signalsReady ? step : null,
    setStep,
    setEnabled,
  };
}
// === ANCHOR: NAV_USE_GUIDE_END ===
