// ANCHOR: TUTORIAL_SPOTLIGHT_START
export interface SpotRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface SpotStyle {
  display: string;
  top: number;
  left: number;
  width: number;
  height: number;
}

/** 대상 요소의 사각형 + 패딩 → 스포트라이트 구멍 위치. rect 없으면 숨김. */
export function spotlightStyle(rect: SpotRect | null, pad = 8): SpotStyle {
  if (!rect) return { display: "none", top: 0, left: 0, width: 0, height: 0 };
  return {
    display: "block",
    top: rect.top - pad,
    left: rect.left - pad,
    width: rect.width + pad * 2,
    height: rect.height + pad * 2,
  };
}
// ANCHOR: TUTORIAL_SPOTLIGHT_END
