// === ANCHOR: NAV_STAGES_START ===
// 3단계 IA(기획·개발·유지보수)의 page↔stage 매핑. 순수 데이터/함수.
export type Page =
  | "home"
  | "manual"
  | "docs"
  | "code"
  | "doctor"
  | "backups"
  | "logs"
  | "settings"
  | "planning"
  | "plan-doc"
  | "work";

export type Stage = "planning" | "develop" | "maintain";

export interface StageDef {
  key: Stage;
  label: string;
  icon: string;
  pages: Page[];
}

export const STAGE_DEFS: StageDef[] = [
  { key: "planning", label: "기획", icon: "📋", pages: ["planning", "plan-doc"] },
  { key: "develop", label: "개발", icon: "⚙️", pages: ["code", "docs", "work"] },
  { key: "maintain", label: "유지보수", icon: "🛡️", pages: ["doctor", "backups", "logs"] },
];

/** page가 속한 단계. 홈/사용법/설정은 단계 없음(null). */
export function stageOf(page: Page): Stage | null {
  return STAGE_DEFS.find((d) => d.pages.includes(page))?.key ?? null;
}

/** 단계에 속한 page 목록(서브탭 순서). */
export function pagesForStage(stage: Stage): Page[] {
  return STAGE_DEFS.find((d) => d.key === stage)?.pages ?? [];
}

/** A안에서 확정한 한글 라벨. 서브탭·표시용. */
export const PAGE_LABELS: Record<Page, string> = {
  home: "홈",
  planning: "기획방",
  "plan-doc": "기획안",
  code: "코드탐색",
  docs: "문서",
  work: "작업방",
  doctor: "진단",
  backups: "백업",
  logs: "에러로그",
  manual: "사용법",
  settings: "설정",
};
// === ANCHOR: NAV_STAGES_END ===
