import type { Page } from "./stages";
import type { DesignJobStatus } from "../design-preview/useDesignJob";

export interface DesignChipState {
  visible: boolean;
  tone?: "busy" | "done" | "error";
  label?: string;
}

/** 디자인 생성 잡의 상태/현재 페이지로 상단 칩 표시를 결정. design-preview 페이지에선 페이지 내 패널이 보이므로 칩 숨김. */
export function designChipState(status: DesignJobStatus, page: Page): DesignChipState {
  if (page === "design-preview") return { visible: false };
  if (status === "running") return { visible: true, tone: "busy", label: "🎨 디자인 생성 중…" };
  if (status === "done") return { visible: true, tone: "done", label: "✓ 디자인 완성 — 보기" };
  if (status === "error") return { visible: true, tone: "error", label: "⚠ 디자인 생성 실패 — 보기" };
  return { visible: false };
}
