import { describe, it, expect } from "vitest";
import { scrollNavVisibility } from "../ScrollToTopButton";

describe("scrollNavVisibility", () => {
  it("shows the top button only when scrolled down past the threshold", () => {
    expect(scrollNavVisibility(0, 600, 2000).showTop).toBe(false);
    expect(scrollNavVisibility(400, 600, 2000).showTop).toBe(true);
  });

  it("shows the bottom button when far above the bottom", () => {
    // at top, lots of content below -> show ↓
    expect(scrollNavVisibility(0, 600, 2000).showBottom).toBe(true);
    // near the bottom (2000 - 1400 - 600 = 0) -> hide ↓
    expect(scrollNavVisibility(1400, 600, 2000).showBottom).toBe(false);
  });

  it("hides both buttons when content fits without scrolling", () => {
    const v = scrollNavVisibility(0, 600, 600);
    expect(v.showTop).toBe(false);
    expect(v.showBottom).toBe(false);
  });

  it("can show both buttons in the middle of a long conversation", () => {
    const v = scrollNavVisibility(700, 600, 2000);
    expect(v.showTop).toBe(true);
    expect(v.showBottom).toBe(true);
  });
});
