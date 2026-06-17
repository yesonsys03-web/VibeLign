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
  ...generatedReportThemes(),
] as const satisfies readonly ReportThemeOption[];

export const REPORT_THEME_GROUPS = Array.from(new Set(REPORT_THEME_OPTIONS.map((theme) => theme.group)));
export const REPORT_THEME_COUNT = REPORT_THEME_OPTIONS.length;
// === ANCHOR: REPORT_THEMES_END ===
