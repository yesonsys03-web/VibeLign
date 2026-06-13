export interface DesignTokens {
  readonly bg: string;
  readonly surface: string;
  readonly text: string;
  readonly primary: string;
  readonly accent: string;
  readonly border: string;
  readonly fontFamily: string;
  readonly radius: string;
  readonly shadow: string;
}
export interface MotionTokens {
  readonly duration: string;
  readonly easing: string;
}
export interface MotionSpec {
  readonly tokens: MotionTokens;
  readonly recipe: string;
}
export interface StyleSpec {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly tokens: DesignTokens;
  readonly recipe: string;
  readonly motion?: MotionSpec;
}
export const DESIGN_STYLES: readonly StyleSpec[] = [
  {
    id: "neo-brutalism",
    name: "네오브루탈리즘",
    description: "두꺼운 검정 테두리·날것 색·하드 그림자",
    tokens: {
      bg: "#FFFDF5", surface: "#FFFFFF", text: "#111111", primary: "#FFD400",
      accent: "#FF4D4D", border: "3px solid #111111",
      fontFamily: "'Archivo', 'Pretendard', system-ui, sans-serif",
      radius: "0px", shadow: "6px 6px 0 #111111",
    },
    recipe:
      "버튼·카드는 굵은 검정 테두리(--border)와 하드 그림자(--shadow). hover 시 그림자 방향으로 2px 이동. 모서리 직각(--radius=0). 강조는 채도 높은 원색. 겹침·비대칭 허용. 폰트는 굵게.",
    motion: {
      tokens: { duration: "80ms", easing: "cubic-bezier(.2,0,0,1)" },
      recipe:
        "호버 시 그림자 방향으로 2px 즉각 이동, 전환은 거의 없이 딱딱(--dur 짧게). 카드 등장은 계단식 pop(스케일 0.96→1, 빠르게). 부드러운 ease 금지 — 각지고 즉각적. reduced-motion 에서 전부 정지.",
    },
  },
];
export function getStyle(id: string): StyleSpec | undefined {
  return DESIGN_STYLES.find((s) => s.id === id);
}
