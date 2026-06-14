import type { StyleSpec } from "./styles";

/** 빈 입력 막막함 해소용 일상어 예시 칩(클릭 시 입력칸에 채움). */
export const EXAMPLE_CHIPS: readonly string[] = [
  "귀엽고 파스텔톤으로",
  "신뢰감 있는 업무용",
  "게임처럼 화려하고 네온",
  "단아하고 여백 많은 일본풍",
  "따뜻한 종이 질감 레트로",
];

/** 내장 + 커스텀 병합. 같은 id 는 커스텀 우선(중복 제거). 내장 순서 유지 후 신규 커스텀 추가. */
export function mergeStyleLists(builtin: readonly StyleSpec[], custom: readonly StyleSpec[]): StyleSpec[] {
  const customById = new Map(custom.map((s) => [s.id, s]));
  const result: StyleSpec[] = builtin.map((b) => customById.get(b.id) ?? b);
  const builtinIds = new Set(builtin.map((b) => b.id));
  for (const c of custom) {
    if (!builtinIds.has(c.id)) result.push(c);
  }
  return result;
}
