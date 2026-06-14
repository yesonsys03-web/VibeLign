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

/** 토큰 → `:root{…}` CSS 변수 블록(백엔드 tokens_to_css_vars 미러, motion 변수 포함). */
export function tokensToCssVars(t: StyleSpec["tokens"], motion?: StyleSpec["motion"]): string {
  let s = `:root{--bg:${t.bg};--surface:${t.surface};--text:${t.text};--primary:${t.primary};--accent:${t.accent};--border:${t.border};--font:${t.fontFamily};--radius:${t.radius};--shadow:${t.shadow};}`;
  if (motion) {
    s = s.replace(/\}$/, `--dur:${motion.tokens.duration};--ease:${motion.tokens.easing};}`);
  }
  return s;
}

/** 목업 HTML 의 첫 `:root{…}` 블록을 새 블록으로 치환(LLM 재호출 없는 즉시 재색칠). 매치 없으면 원본 유지. */
export function replaceRootBlock(html: string, rootBlock: string): string {
  return html.replace(/:root\s*\{[^}]*\}/, rootBlock);
}
