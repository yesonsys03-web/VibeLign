// === ANCHOR: REPORT_MODEL_START ===
export interface RModelBlock { kind: "paragraph" | "bullets" | "summary"; text: string; items: string[]; }
export interface RModelSection { heading: string; blocks: RModelBlock[]; }
export interface RModel {
  title: string; report_type: string; date: string; source_plan_path: string; sections: RModelSection[];
}
export interface GuardRecord { section: number; block: number; reason: string; missing: string[]; }
export interface VagueWarning { section: number; block: number; term: string; offset: number; }
export interface EmitPayload {
  ok: true; report_type: string; slug: string; key: string;
  base: RModel; polished: RModel; guards: GuardRecord[]; vague_warnings: VagueWarning[];
}

/** 블록 좌표 "section:block" → 결정. */
export type Decision = "accept" | "reject";
export type ReviewDecisions = Record<string, Decision>;

export function blockKey(section: number, block: number): string { return `${section}:${block}`; }

/** 거부된 블록 좌표만 [[section,block],...] 로 추린다(CLI --reject-blocks 페이로드). */
export function rejectPairs(decisions: ReviewDecisions): [number, number][] {
  const out: [number, number][] = [];
  for (const [key, d] of Object.entries(decisions)) {
    if (d !== "reject") continue;
    const [s, b] = key.split(":").map(Number);
    out.push([s, b]);
  }
  return out;
}

/** paragraph/summary 만 diff 대상(bullets 는 읽기전용). */
export function isPolishable(block: RModelBlock): boolean {
  return block.kind === "paragraph" || block.kind === "summary";
}
// === ANCHOR: REPORT_MODEL_END ===
