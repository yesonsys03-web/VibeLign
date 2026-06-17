// === ANCHOR: REPORT_FONT_SIZES_START ===
export type ReportFontSizeKey = "title" | "heading" | "body";

export type ReportFontSizes = Partial<Record<ReportFontSizeKey, number>>;

export type ReportFontSizeField = {
  readonly key: ReportFontSizeKey;
  readonly label: string;
  readonly flag: string;
  readonly placeholder: string;
};

export const REPORT_FONT_SIZE_MIN = 8;
export const REPORT_FONT_SIZE_MAX = 72;

export const REPORT_FONT_SIZE_FIELDS = [
  { key: "title", label: "타이틀", flag: "--title-font-size", placeholder: "28" },
  { key: "heading", label: "헤드라인", flag: "--heading-font-size", placeholder: "17" },
  { key: "body", label: "본문", flag: "--body-font-size", placeholder: "14" },
] as const satisfies readonly ReportFontSizeField[];

export function reportFontSizeArgs(fontSizes: ReportFontSizes): readonly string[] {
  return REPORT_FONT_SIZE_FIELDS.flatMap((field) => {
    const value = fontSizes[field.key];
    return value === undefined ? [] : [field.flag, String(value)];
  });
}

export function parseReportFontSizeInput(value: string): number | undefined {
  if (value.trim() === "") return undefined;
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) return undefined;
  return parsed;
}
// === ANCHOR: REPORT_FONT_SIZES_END ===
