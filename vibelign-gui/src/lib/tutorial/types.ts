// ANCHOR: TUTORIAL_TYPES_START
import type { Page } from "../nav/stages";

export type TutorialId = "todo" | "guestbook" | "quiz";

export type TutorialStepKind = "copy" | "pasteSend" | "click" | "confirm";

// spec §3 enum + 'copy'(복사 클릭 즉시 완료) + 'guardChecked'(§5 안전검사 단계)
export type StepDone =
  | "copy"
  | "sent"
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
