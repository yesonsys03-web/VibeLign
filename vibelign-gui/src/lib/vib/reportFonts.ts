// === ANCHOR: REPORT_FONTS_START ===
export type ReportFontSlot = "heading" | "body";

export type ReportFonts = Partial<Record<ReportFontSlot, string>>;

export type ReportFontOption = { readonly id: string; readonly label: string };

// Python vibelign/core/reporting_cli/fonts.py 의 REPORT_FONTS 와 ID·순서 일치.
export const REPORT_FONT_OPTIONS = [
  { id: "pretendard", label: "Pretendard (고딕)" },
  { id: "nanum-myeongjo", label: "나눔명조" },
  { id: "gowun-batang", label: "고운바탕" },
  { id: "gowun-dodum", label: "고운돋움" },
  { id: "black-han-sans", label: "검은고딕" },
] as const satisfies readonly ReportFontOption[];

const SLOT_FLAGS: readonly { slot: ReportFontSlot; flag: string }[] = [
  { slot: "heading", flag: "--heading-font" },
  { slot: "body", flag: "--body-font" },
];

export function reportFontArgs(fonts: ReportFonts): readonly string[] {
  return SLOT_FLAGS.flatMap(({ slot, flag }) => {
    const id = fonts[slot];
    return id ? [flag, id] : [];
  });
}
// === ANCHOR: REPORT_FONTS_END ===
