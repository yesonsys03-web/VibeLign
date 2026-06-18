// === ANCHOR: REPORT_THEMES_START ===
export type ReportThemeOption = {
  readonly id: string;
  readonly label: string;
  readonly group: string;
};

const BASE_REPORT_THEMES = [
  { id: "classic", label: "클래식", group: "기본" },
  { id: "minimal", label: "모던 미니멀", group: "기본" },
  { id: "executive", label: "임원 보고형", group: "기본" },
  { id: "compact", label: "컴팩트", group: "기본" },
  { id: "pastel", label: "부드러운 파스텔", group: "기본" },
] as const satisfies readonly ReportThemeOption[];

const REPORT_THEME_LAYOUTS = [
  { id: "plain", label: "기본형" },
  { id: "letter", label: "공문형" },
  { id: "board", label: "임원형" },
  { id: "cards", label: "카드형" },
  { id: "memo", label: "메모형" },
] as const;

const REPORT_THEME_PALETTES = [
  { id: "indigo", label: "인디고" },
  { id: "teal", label: "틸" },
  { id: "forest", label: "포레스트" },
  { id: "wine", label: "와인" },
  { id: "amber", label: "앰버" },
  { id: "slate", label: "슬레이트" },
  { id: "violet", label: "바이올렛" },
  { id: "coral", label: "코랄" },
  { id: "olive", label: "올리브" },
  { id: "mono", label: "모노" },
] as const;

const REPORT_THEME_DENSITIES = [
  { id: "balanced", label: "표준" },
  { id: "dense", label: "촘촘" },
] as const;

const SATGAT_REPORT_THEMES = [
  { id: "satgat-work-brief", label: "삿갓 · 업무 브리프", group: "삿갓 specimen" },
  { id: "satgat-executive-memo", label: "삿갓 · 임원 메모", group: "삿갓 specimen" },
  { id: "satgat-proposal", label: "삿갓 · 제안서", group: "삿갓 specimen" },
  { id: "satgat-result-report", label: "삿갓 · 결과 보고", group: "삿갓 specimen" },
  { id: "satgat-research-note", label: "삿갓 · 리서치 노트", group: "삿갓 specimen" },
  { id: "satgat-risk-review", label: "삿갓 · 리스크 검토", group: "삿갓 specimen" },
  { id: "satgat-roadmap", label: "삿갓 · 로드맵", group: "삿갓 specimen" },
  { id: "satgat-meeting-minutes", label: "삿갓 · 회의록", group: "삿갓 specimen" },
  { id: "satgat-release-note", label: "삿갓 · 릴리즈 노트", group: "삿갓 specimen" },
  { id: "satgat-decision-record", label: "삿갓 · 결정 기록", group: "삿갓 specimen" },
  { id: "satgat-retrospective", label: "삿갓 · 회고", group: "삿갓 specimen" },
  { id: "satgat-market-scan", label: "삿갓 · 시장 스캔", group: "삿갓 specimen" },
  { id: "satgat-case-study", label: "삿갓 · 사례 연구", group: "삿갓 specimen" },
] as const satisfies readonly ReportThemeOption[];

function generatedReportThemes(): readonly ReportThemeOption[] {
  return REPORT_THEME_LAYOUTS.flatMap((layout) =>
    REPORT_THEME_PALETTES.flatMap((palette) =>
      REPORT_THEME_DENSITIES.map((density) => ({
        id: `${layout.id}-${palette.id}-${density.id}`,
        label: `${layout.label} · ${palette.label} · ${density.label}`,
        group: layout.label,
      })),
    ),
  );
}

export const REPORT_THEME_OPTIONS = [
  ...BASE_REPORT_THEMES,
  ...SATGAT_REPORT_THEMES,
  ...generatedReportThemes(),
] as const satisfies readonly ReportThemeOption[];

export const REPORT_THEME_GROUPS = Array.from(new Set(REPORT_THEME_OPTIONS.map((theme) => theme.group)));
export const REPORT_THEME_COUNT = REPORT_THEME_OPTIONS.length;
// === ANCHOR: REPORT_THEMES_END ===
