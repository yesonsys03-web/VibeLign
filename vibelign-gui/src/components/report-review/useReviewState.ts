// === ANCHOR: USE_REVIEW_STATE_START ===
import { useState } from "react";
import {
  blockKey, isPolishable, rejectPairs,
  type Decision, type EmitPayload, type ReviewDecisions,
} from "../../lib/vib/reportModel";

/** guard 걸린 블록은 기본 reject(원본 유지), 그 외 polishable 블록은 기본 accept. */
export function initialDecisions(payload: EmitPayload): ReviewDecisions {
  const guarded = new Set(payload.guards.map((g) => blockKey(g.section, g.block)));
  const out: ReviewDecisions = {};
  payload.base.sections.forEach((sec, si) =>
    sec.blocks.forEach((blk, bi) => {
      if (!isPolishable(blk)) return;
      const key = blockKey(si, bi);
      out[key] = guarded.has(key) ? "reject" : "accept";
    }),
  );
  return out;
}

export function useReviewState(payload: EmitPayload) {
  const [decisions, setDecisions] = useState<ReviewDecisions>(() => initialDecisions(payload));
  const set = (si: number, bi: number, d: Decision) =>
    setDecisions((prev) => ({ ...prev, [blockKey(si, bi)]: d }));
  const setAll = (d: Decision) =>
    setDecisions((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, d])) as ReviewDecisions);
  return { decisions, set, setAll, reject: () => rejectPairs(decisions) };
}
// === ANCHOR: USE_REVIEW_STATE_END ===
