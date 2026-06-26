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
