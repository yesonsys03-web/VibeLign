// === ANCHOR: DESIGNCHIP_TEST_START ===
import { describe, test, expect } from "vitest";
import { designChipState } from "../designChip";

describe("designChipState", () => {
  test("running·타페이지 → busy 칩", () => {
    const s = designChipState("running", "home");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("busy");
    expect(s.label).toContain("생성 중");
  });
  test("done·타페이지 → done 칩", () => {
    const s = designChipState("done", "work");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("done");
    expect(s.label).toContain("완성");
  });
  test("error·타페이지 → error 칩", () => {
    const s = designChipState("error", "work");
    expect(s.visible).toBe(true);
    expect(s.tone).toBe("error");
    expect(s.label).toContain("실패");
  });
  test("design-preview 페이지에선 어떤 상태든 숨김", () => {
    expect(designChipState("running", "design-preview").visible).toBe(false);
    expect(designChipState("done", "design-preview").visible).toBe(false);
    expect(designChipState("error", "design-preview").visible).toBe(false);
  });
  test("idle → 숨김", () => {
    expect(designChipState("idle", "home").visible).toBe(false);
  });
});
// === ANCHOR: DESIGNCHIP_TEST_END ===
