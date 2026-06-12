// === ANCHOR: WORK_HANDOFF_START ===
// 실행해보기 → 작업방 핸드오프 채널 (plans/2026-06-12-작동검증-개선루프-design.md §4).
// M3b 의 단일 채널(error)을 kind 로 일반화 — error(시작 실패 고치기) / improve(써보니 다듬기).
import { buildRunErrorFixInstruction } from "./errorFixInstruction";
import { buildImproveInstruction } from "./improveInstruction";

export type WorkHandoffKind = "error" | "improve";

export interface WorkHandoff {
  readonly kind: WorkHandoffKind;
  readonly text: string;
}

/** 핸드오프 → 작업방 지시문. kind 로 프레이밍 분기. */
export function buildHandoffInstruction(handoff: WorkHandoff, planPath: string | null): string {
  return handoff.kind === "error"
    ? buildRunErrorFixInstruction({ errorText: handoff.text, planPath })
    : buildImproveInstruction({ requestText: handoff.text, planPath });
}
// === ANCHOR: WORK_HANDOFF_END ===
