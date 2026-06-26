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
