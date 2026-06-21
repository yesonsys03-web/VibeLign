// === ANCHOR: REPORTFONTS_TEST_START ===
import { describe, expect, it } from "vitest";
import { REPORT_FONT_OPTIONS, reportFontArgs } from "../reportFonts";

describe("reportFonts", () => {
  it("exposes the five OFL fonts", () => {
    expect(REPORT_FONT_OPTIONS.map((f) => f.id)).toEqual([
      "pretendard", "nanum-myeongjo", "gowun-batang", "gowun-dodum", "black-han-sans",
    ]);
  });

  it("builds CLI args only for set fonts", () => {
    expect(reportFontArgs({})).toEqual([]);
    expect(reportFontArgs({ heading: "pretendard" })).toEqual(["--heading-font", "pretendard"]);
    expect(reportFontArgs({ heading: "pretendard", body: "gowun-batang" })).toEqual([
      "--heading-font", "pretendard", "--body-font", "gowun-batang",
    ]);
  });
});
// === ANCHOR: REPORTFONTS_TEST_END ===
