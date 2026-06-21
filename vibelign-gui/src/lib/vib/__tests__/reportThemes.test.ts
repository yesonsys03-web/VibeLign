// === ANCHOR: REPORTTHEMES_TEST_START ===
import { describe, expect, test } from "vitest";

import { REPORT_THEME_COUNT, REPORT_THEME_OPTIONS } from "../reportThemes";

describe("reportThemes", () => {
  test("exposes the satgat thirteen-specimen report pack", () => {
    const satgatThemes = REPORT_THEME_OPTIONS.filter((theme) => theme.group === "삿갓 specimen");

    expect(REPORT_THEME_COUNT).toBe(118);
    expect(satgatThemes).toHaveLength(13);
    expect(satgatThemes[0]).toEqual({
      id: "satgat-work-brief",
      label: "삿갓 · 업무 브리프",
      group: "삿갓 specimen",
    });
    expect(satgatThemes.at(-1)?.id).toBe("satgat-case-study");
  });
});
// === ANCHOR: REPORTTHEMES_TEST_END ===
