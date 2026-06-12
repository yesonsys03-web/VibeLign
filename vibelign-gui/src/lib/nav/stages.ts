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
  | "work"
  | "run";

export type Stage = "planning" | "develop" | "maintain";

export interface StageDef {
  key: Stage;
  label: string;
  icon: string;
  pages: Page[];
}

export const STAGE_DEFS: StageDef[] = [
  { key: "planning", label: "기획", icon: "📋", pages: ["planning", "plan-doc"] },
  { key: "develop", label: "개발", icon: "⚙️", pages: ["code", "docs", "work", "run"] },
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
  run: "실행해보기",
  doctor: "진단",
  backups: "백업",
  logs: "에러로그",
  manual: "사용법",
  settings: "설정",
};

/** 메뉴 말풍선(hover title) — 초보용 한 줄, 모두 10자 이내로 통일. */
export const PAGE_DESCRIPTIONS: Record<Page, string> = {
  home: "처음 화면",
  planning: "AI와 계획 짜기",
  "plan-doc": "계획 문서",
  code: "코드 둘러보기",
  docs: "설명 문서",
  work: "AI에게 시키기",
  run: "직접 켜보기",
  doctor: "문제 검사",
  backups: "되돌릴 시점",
  logs: "오류 기록",
  manual: "사용 설명서",
  settings: "환경 설정",
};

/** 단계 탭 말풍선 — 10자 이내. */
export const STAGE_DESCRIPTIONS: Record<Stage, string> = {
  planning: "계획 세우기",
  develop: "코드 만들기",
  maintain: "점검과 저장",
};
// === ANCHOR: NAV_STAGES_END ===
