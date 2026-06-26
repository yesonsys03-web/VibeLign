import { describe, it, expect } from "vitest";
import { spotlightStyle } from "../spotlight";

describe("spotlightStyle", () => {
  it("rect이 없으면 숨긴다", () => {
    expect(spotlightStyle(null)).toEqual({ display: "none", top: 0, left: 0, width: 0, height: 0 });
  });

  it("rect에 패딩을 더해 구멍 위치를 만든다", () => {
    const s = spotlightStyle({ top: 100, left: 50, width: 200, height: 40 }, 8);
    expect(s.display).toBe("block");
    expect(s.top).toBe(92);
    expect(s.left).toBe(42);
    expect(s.width).toBe(216);
    expect(s.height).toBe(56);
  });

  it("기본 패딩은 8이다", () => {
    const s = spotlightStyle({ top: 0, left: 0, width: 10, height: 10 });
    expect(s.width).toBe(26);
  });
});
