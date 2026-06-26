// ANCHOR: SPOTLIGHT_TOUR_START
import { useEffect, useRef, useState } from "react";
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

  // goPage: refs keep latest values; the effect fires once per step.id change (not per render)
  // so onNavigate being a new closure each render cannot re-trigger navigation.
  const onNavigateRef = useRef(onNavigate);
  const goPageRef = useRef(step.goPage);
  onNavigateRef.current = onNavigate;
  goPageRef.current = step.goPage;

  // 이 단계가 요구하는 화면으로 데려다 놓기 (단계 변경 시 1회만)
  useEffect(() => {
    if (goPageRef.current) onNavigateRef.current(goPageRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step.id]);

  // 대상 요소 위치 추적 — rAF 루프로 레이아웃 변화를 즉시 반영
  useEffect(() => {
    let raf = 0;
    let prev: SpotRect | null = null;
    const tick = () => {
      const next = readRect(step.target);
      const changed =
        (!prev !== !next) ||
        (prev !== null && next !== null &&
          (prev.top !== next.top || prev.left !== next.left ||
           prev.width !== next.width || prev.height !== next.height));
      if (changed) { prev = next; setRect(next); }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [step.id, step.target]);

  // 신호 기반 자동 진행(click/pasteSend) — edge-gating: 진입 시 이미 충족된 신호는 무시
  const lastStepId = useRef<string | null>(null);
  const armed = useRef(false);
  useEffect(() => {
    if (step.kind !== "click" && step.kind !== "pasteSend") return;
    if (lastStepId.current !== step.id) {
      lastStepId.current = step.id;
      armed.current = !isStepComplete(step.done, signals); // arm only if not already satisfied
    }
    if (armed.current && isStepComplete(step.done, signals)) {
      armed.current = false;
      onAdvance();
    }
  }, [step.id, step.kind, step.done, signals, onAdvance]);

  const hole = spotlightStyle(rect);
  const total = tutorial.steps.length;

  function handleCopy() {
    if (step.copyText) navigator.clipboard.writeText(step.copyText).catch(() => {});
    onAdvance();
  }

  function handleReCopy() {
    if (step.copyText) navigator.clipboard.writeText(step.copyText).catch(() => {});
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
          {step.copyText && (
            <div className="tour-copybox">{step.copyText}</div>
          )}
          {step.why && <p className="tour-why">〔왜?〕 {step.why}</p>}
          <div className="tour-actions">
            {step.kind === "copy" && (
              <button className="btn" onClick={handleCopy}>📋 복사</button>
            )}
            {step.kind === "pasteSend" && step.copyText && (
              <button className="btn btn-sm" onClick={handleReCopy}>📋 다시 복사</button>
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
