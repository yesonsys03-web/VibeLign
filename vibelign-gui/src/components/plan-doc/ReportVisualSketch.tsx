import type { CSSProperties } from "react";

import type { ReportVisualCard } from "../../lib/vib/reportVisualCards";

type SketchSymbolKey =
  | "bell"
  | "calendar"
  | "checklist"
  | "people"
  | "board"
  | "phone"
  | "chart"
  | "document"
  | "lock"
  | "wallet"
  | "chat"
  | "map";

type SketchSymbol = {
  readonly key: SketchSymbolKey;
  readonly label: string;
  readonly keywords: readonly string[];
};

type SketchDescriptor = {
  readonly symbols: readonly [SketchSymbol, SketchSymbol, SketchSymbol];
  readonly colorShift: number;
};

type SymbolPlacement = {
  readonly symbol: SketchSymbolKey;
  readonly cx: number;
  readonly cy: number;
  readonly color: string;
  readonly scale: number;
};

const symbols: readonly SketchSymbol[] = [
  { key: "bell", label: "알림", keywords: ["알람", "알림", "notification", "reminder", "울림", "푸시"] },
  { key: "calendar", label: "일정", keywords: ["일정", "캘린더", "날짜", "반복", "예약", "schedule", "calendar", "date"] },
  { key: "checklist", label: "체크리스트", keywords: ["체크", "할일", "작업", "태스크", "todo", "task", "목록", "추가", "삭제", "수정"] },
  { key: "people", label: "사용자", keywords: ["사용자", "고객", "대상", "팀", "persona", "user", "customer", "member"] },
  { key: "board", label: "기획 보드", keywords: ["기획", "결정", "선택", "흐름", "로드맵", "plan", "decision", "roadmap", "workflow"] },
  { key: "phone", label: "앱 화면", keywords: ["앱", "모바일", "화면", "버튼", "ui", "ux", "app", "mobile", "screen"] },
  { key: "chart", label: "데이터", keywords: ["데이터", "분석", "통계", "지표", "보고서", "metric", "chart", "data", "analytics"] },
  { key: "document", label: "문서", keywords: ["문서", "기획안", "정책", "요구사항", "spec", "document", "report", "proposal", "policy"] },
  { key: "lock", label: "보안", keywords: ["보안", "로그인", "인증", "권한", "security", "login", "auth", "permission"] },
  { key: "wallet", label: "결제", keywords: ["결제", "가격", "환불", "매출", "구독", "payment", "price", "refund", "revenue", "subscription"] },
  { key: "chat", label: "대화", keywords: ["대화", "메시지", "문의", "피드백", "chat", "message", "feedback", "support"] },
  { key: "map", label: "위치", keywords: ["위치", "지도", "장소", "경로", "location", "map", "route", "place"] },
];

const palette = ["#FFD84D", "#FF4D4D", "#4D9FFF", "#4DFF91", "#F5621E"] as const;

export function ReportVisualSketch({ card }: { readonly card: ReportVisualCard }) {
  const descriptor = describeCard(card);
  const colors = shiftedColors(descriptor.colorShift);
  const placements: readonly SymbolPlacement[] = [
    { symbol: descriptor.symbols[0].key, cx: 72, cy: 74, color: colors[0], scale: 1 },
    { symbol: descriptor.symbols[1].key, cx: 160, cy: 66, color: colors[1], scale: 1.08 },
    { symbol: descriptor.symbols[2].key, cx: 248, cy: 74, color: colors[3], scale: 1 },
  ];
  return (
    <svg
      viewBox="0 0 320 150"
      role="img"
      aria-label={`카드뉴스 그림: ${descriptor.symbols.map((symbol) => symbol.label).join(", ")}`}
      data-sketch-symbols={descriptor.symbols.map((symbol) => symbol.key).join(",")}
      style={svgStyle}
    >
      <rect x="16" y="18" width="288" height="110" rx="16" fill="#FFF9DA" stroke="#1A1A1A" strokeWidth="4" />
      <path d="M55 116 C95 100 126 128 164 112 S235 98 278 116" fill="none" stroke={colors[2]} strokeWidth="5" strokeLinecap="round" />
      <path d="M92 76 C120 54 194 54 226 76" fill="none" stroke="#1A1A1A" strokeWidth="4" strokeLinecap="round" strokeDasharray="8 9" />
      {placements.map((placement) => (
        <SketchSymbolMark key={`${placement.symbol}-${placement.cx}`} placement={placement} />
      ))}
      <circle cx="45" cy="38" r="7" fill={colors[4]} stroke="#1A1A1A" strokeWidth="3" />
      <path d="M279 35 l7 13 13 5 -13 5 -7 13 -7 -13 -13 -5 13 -5z" fill={colors[0]} stroke="#1A1A1A" strokeWidth="3" />
    </svg>
  );
}

function describeCard(card: ReportVisualCard): SketchDescriptor {
  const text = `${card.title} ${card.body} ${card.caption} ${card.visual_prompt} ${card.image.prompt}`.toLowerCase();
  const selected = symbols
    .map((symbol, index) => ({
      symbol,
      index,
      score: symbol.keywords.filter((keyword) => text.includes(keyword.toLowerCase())).length,
    }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .map((item) => item.symbol);
  const hash = hashText(text);
  let cursor = 0;
  while (selected.length < 3) {
    const fallback = symbols[(hash + cursor * 7) % symbols.length];
    if (!selected.includes(fallback)) selected.push(fallback);
    cursor += 1;
  }
  return { symbols: [selected[0], selected[1], selected[2]], colorShift: hash % palette.length };
}

function hashText(text: string): number {
  let hash = 2166136261;
  for (const char of text) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash);
}

function shiftedColors(shift: number): readonly string[] {
  return palette.map((_, index) => palette[(index + shift) % palette.length]);
}

function SketchSymbolMark({ placement }: { readonly placement: SymbolPlacement }) {
  const size = 44 * placement.scale;
  const x = placement.cx - size / 2;
  const y = placement.cy - size / 2;
  return (
    <g transform={`translate(${x} ${y}) scale(${placement.scale})`}>
      <SymbolShape symbol={placement.symbol} color={placement.color} />
    </g>
  );
}

function SymbolShape({ symbol, color }: { readonly symbol: SketchSymbolKey; readonly color: string }) {
  if (symbol === "bell") {
    return (
      <>
        <path d="M22 8 C11 8 8 17 8 28 v8 l-6 7 h40 l-6-7 v-8 C36 17 33 8 22 8z" fill={color} stroke="#1A1A1A" strokeWidth="4" strokeLinejoin="round" />
        <path d="M17 45 C19 52 25 52 27 45" fill="none" stroke="#1A1A1A" strokeWidth="4" strokeLinecap="round" />
      </>
    );
  }
  if (symbol === "calendar") {
    return (
      <>
        <rect x="4" y="8" width="40" height="34" rx="6" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <path d="M4 19 h40 M14 4 v11 M34 4 v11" stroke="#1A1A1A" strokeWidth="4" strokeLinecap="round" />
        <rect x="13" y="26" width="8" height="8" fill={color} stroke="#1A1A1A" strokeWidth="3" />
      </>
    );
  }
  if (symbol === "checklist") {
    return (
      <>
        <rect x="5" y="5" width="38" height="40" rx="6" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <path d="M13 17 l5 5 9-11 M13 32 l5 5 15-17" fill="none" stroke={color} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      </>
    );
  }
  if (symbol === "people") {
    return (
      <>
        <circle cx="16" cy="17" r="10" fill={color} stroke="#1A1A1A" strokeWidth="4" />
        <circle cx="32" cy="19" r="9" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <path d="M5 43 C8 30 22 29 27 43" fill={color} stroke="#1A1A1A" strokeWidth="4" />
        <path d="M22 43 C24 33 39 32 43 43" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
      </>
    );
  }
  if (symbol === "board") {
    return (
      <>
        <rect x="4" y="8" width="42" height="32" rx="5" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <rect x="11" y="15" width="11" height="9" fill={color} stroke="#1A1A1A" strokeWidth="3" />
        <rect x="27" y="15" width="11" height="9" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="3" />
        <path d="M13 32 h24" stroke="#1A1A1A" strokeWidth="4" strokeLinecap="round" />
      </>
    );
  }
  if (symbol === "phone") {
    return (
      <>
        <rect x="12" y="3" width="26" height="44" rx="7" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <rect x="18" y="12" width="14" height="18" fill={color} stroke="#1A1A1A" strokeWidth="3" />
        <circle cx="25" cy="39" r="3" fill="#1A1A1A" />
      </>
    );
  }
  if (symbol === "chart") {
    return (
      <>
        <rect x="5" y="7" width="40" height="36" rx="6" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <path d="M13 34 v-9 M25 34 v-17 M37 34 v-24" stroke={color} strokeWidth="7" strokeLinecap="round" />
      </>
    );
  }
  if (symbol === "lock") {
    return (
      <>
        <rect x="8" y="22" width="34" height="24" rx="6" fill={color} stroke="#1A1A1A" strokeWidth="4" />
        <path d="M16 22 v-7 C16 4 34 4 34 15 v7" fill="none" stroke="#1A1A1A" strokeWidth="5" strokeLinecap="round" />
      </>
    );
  }
  if (symbol === "wallet") {
    return (
      <>
        <rect x="5" y="13" width="40" height="28" rx="7" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" />
        <rect x="25" y="20" width="20" height="14" rx="5" fill={color} stroke="#1A1A1A" strokeWidth="4" />
      </>
    );
  }
  if (symbol === "chat") {
    return (
      <>
        <path d="M6 10 h38 v25 H25 l-11 9 v-9 H6z" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" strokeLinejoin="round" />
        <circle cx="17" cy="23" r="4" fill={color} />
        <circle cx="27" cy="23" r="4" fill={color} />
        <circle cx="37" cy="23" r="4" fill={color} />
      </>
    );
  }
  if (symbol === "map") {
    return (
      <>
        <path d="M25 47 C14 34 10 26 10 18 C10 8 18 3 25 3 C32 3 40 8 40 18 C40 26 36 34 25 47z" fill={color} stroke="#1A1A1A" strokeWidth="4" />
        <circle cx="25" cy="18" r="6" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="3" />
      </>
    );
  }
  return (
    <>
      <path d="M10 4 h23 l9 9 v31 H10z" fill="#FFFFFF" stroke="#1A1A1A" strokeWidth="4" strokeLinejoin="round" />
      <path d="M33 4 v10 h9 M17 24 h18 M17 34 h14" stroke={color} strokeWidth="5" strokeLinecap="round" />
    </>
  );
}

const svgStyle: CSSProperties = { width: "100%", maxWidth: "100%", height: 132, display: "block" };
