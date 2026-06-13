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
  {
    id: "minimal-saas",
    name: "미니멀 SaaS",
    description: "여백 많은 깔끔한 SaaS UI·부드러운 그림자",
    tokens: {
      bg: "#FFFFFF", surface: "#F8FAFC", text: "#0F172A", primary: "#4F46E5", accent: "#06B6D4",
      border: "1px solid #E2E8F0", fontFamily: "'Inter', 'Pretendard', system-ui, sans-serif",
      radius: "12px", shadow: "0 1px 3px rgba(15,23,42,0.08)",
    },
    recipe:
      "넉넉한 여백·정렬 그리드. 카드 라운드(--radius)·옅은 그림자(--shadow). primary는 CTA에만. 중립 배경에 한 강조색.",
    motion: {
      tokens: { duration: "200ms", easing: "cubic-bezier(.4,0,.2,1)" },
      recipe: "은은한 페이드/슬라이드 등장, 옅은 그림자 전환. 호버는 미묘한 상승. 과하지 않게 차분히. reduced-motion 에서 전부 정지.",
    },
  },
  {
    id: "frutiger-aero",
    name: "프루티거에어로",
    description: "2000년대 광택·하늘색 그라데이션·유리 질감",
    tokens: {
      bg: "#DFF3FF", surface: "rgba(255,255,255,0.7)", text: "#0B3D5C", primary: "#19B7FF", accent: "#7CF29B",
      border: "1px solid rgba(255,255,255,0.8)", fontFamily: "'Segoe UI', 'Pretendard', system-ui, sans-serif",
      radius: "16px", shadow: "0 8px 24px rgba(25,183,255,0.25)",
    },
    recipe:
      "맑은 하늘색 그라데이션·유리(반투명 surface)·광택 하이라이트. 둥근 라운드. 물방울 같은 생기. 녹색 강조.",
    motion: {
      tokens: { duration: "400ms", easing: "cubic-bezier(.34,1.56,.64,1)" },
      recipe: "플로팅·스프링 오버슈트(살짝 튕김). 광택 하이라이트 부드럽게 흐름. 등장은 떠오르듯. reduced-motion 에서 전부 정지.",
    },
  },
  {
    id: "retro-diner",
    name: "레트로다이너",
    description: "50년대 다이너·체커·볼드 헤드라인",
    tokens: {
      bg: "#FFF8E7", surface: "#FFFFFF", text: "#2B2118", primary: "#E63946", accent: "#1D9BF0",
      border: "2px solid #2B2118", fontFamily: "'Poppins', 'Pretendard', system-ui, sans-serif",
      radius: "8px", shadow: "0 4px 0 #2B2118",
    },
    recipe:
      "빨강·민트·크림 팔레트. 체커·스트라이프 장식. 굵은 헤드라인. 살짝 도드라진 그림자. 다이너 간판 느낌.",
    motion: {
      tokens: { duration: "300ms", easing: "cubic-bezier(.68,-.55,.27,1.55)" },
      recipe: "통통 바운스 등장, 강조 요소는 간판 점멸 느낌(은은하게). 호버 시 통 튀는 반응. reduced-motion 에서 전부 정지.",
    },
  },
  {
    id: "risograph",
    name: "리소그래프",
    description: "리소 인쇄·2~3색 오버프린트·거친 질감",
    tokens: {
      bg: "#F4F1E8", surface: "#FCFAF2", text: "#1A1A1A", primary: "#FF5C39", accent: "#2A5DB0",
      border: "2px solid #1A1A1A", fontFamily: "'Space Grotesk', 'Pretendard', system-ui, sans-serif",
      radius: "2px", shadow: "3px 3px 0 rgba(42,93,176,0.5)",
    },
    recipe:
      "제한된 2~3색(주황·파랑) 오버프린트·살짝 어긋난 겹침. 종이 질감. 납작한 컬러 블록. 거친 인쇄 느낌.",
    motion: {
      tokens: { duration: "120ms", easing: "steps(2, end)" },
      recipe: "스냅·즉각·약간 거친 끊김(steps). 부드러운 보간 지양. 등장은 톡 나타남. reduced-motion 에서 전부 정지.",
    },
  },
];
export function getStyle(id: string): StyleSpec | undefined {
  return DESIGN_STYLES.find((s) => s.id === id);
}
