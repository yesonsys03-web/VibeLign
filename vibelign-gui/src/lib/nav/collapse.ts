// === ANCHOR: COLLAPSE_START ===
// 접기 토글 공통 — 앱 전반의 ▸/▾ 접기 버튼 스타일·선호 저장을 한 곳에서(통일).
import type { CSSProperties } from "react";

/** 제목 앞 접기 토글(▸/▾)의 정사각 버튼 스타일 — 가이드 스트립·기획안 카드 등 통일. */
export const collapseToggleStyle: CSSProperties = {
  fontSize: 13,
  width: 22,
  height: 22,
  padding: 0,
  flexShrink: 0,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  background: "transparent",
  border: "1px solid #1A1A1A",
  borderRadius: 4,
  cursor: "pointer",
  color: "#1A1A1A",
  lineHeight: 1,
};

// "작업 기준 기획안" 카드(작업방·코드탐색 공통)의 접힘 선호 — 전역 localStorage 저장.
// 한 번 접으면 양쪽 화면에서 계속 접힌 채 유지. 기본은 펼침.
const PLAN_CARD_COLLAPSED_KEY = "vibelign:plancard-collapsed";

export function planCardCollapsed(): boolean {
  try {
    return localStorage.getItem(PLAN_CARD_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function setPlanCardCollapsed(v: boolean) {
  try {
    localStorage.setItem(PLAN_CARD_COLLAPSED_KEY, v ? "1" : "0");
  } catch {
    /* localStorage 불가 환경 — 세션 내 상태만 유지 */
  }
}
// === ANCHOR: COLLAPSE_END ===
