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
export interface StyleSpec {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly tokens: DesignTokens;
  readonly recipe: string;
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
  },
];
export function getStyle(id: string): StyleSpec | undefined {
  return DESIGN_STYLES.find((s) => s.id === id);
}
