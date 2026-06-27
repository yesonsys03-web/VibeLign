// === ANCHOR: STYLES_TEST_START ===
import { describe, it, expect } from "vitest";
import { DESIGN_STYLES, getStyle } from "./styles";

describe("DESIGN_STYLES", () => {
  it("네오브루탈리즘이 토큰 9필드 + 레시피를 가진다", () => {
    const s = getStyle("neo-brutalism");
    expect(s).toBeDefined();
    expect(s!.tokens.bg).toBeTruthy();
    expect(s!.tokens.primary).toBeTruthy();
    expect(s!.tokens.fontFamily).toBeTruthy();
    expect(s!.tokens.radius).toBeTruthy();
    expect(s!.tokens.shadow).toBeTruthy();
    expect(s!.recipe.length).toBeGreaterThan(20);
  });
  it("모든 id가 [a-z0-9-]+ 이고 고유하다", () => {
    const ids = DESIGN_STYLES.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z0-9-]+$/);
  });
});

describe("DESIGN_STYLES motion", () => {
  it("네오브루탈리즘은 motion(tokens+recipe)을 가진다", () => {
    const m = getStyle("neo-brutalism")!.motion;
    expect(m).toBeDefined();
    expect(m!.tokens.duration).toMatch(/^\d+(\.\d+)?m?s$/);
    expect(m!.tokens.easing).toBeTruthy();
    expect(m!.recipe.length).toBeGreaterThan(20);
  });
});

describe("DESIGN_STYLES 5종 완성", () => {
  it("5종이 순서대로 존재", () => {
    expect(DESIGN_STYLES.map((s) => s.id)).toEqual(
      ["neo-brutalism", "minimal-saas", "frutiger-aero", "retro-diner", "risograph"]);
  });
  it("모든 스타일이 motion(tokens+recipe)을 가진다", () => {
    for (const s of DESIGN_STYLES) {
      expect(s.motion, s.id).toBeDefined();
      expect(s.motion!.tokens.duration).toMatch(/^\d+(\.\d+)?m?s$/);
      expect(s.motion!.tokens.easing.length).toBeGreaterThan(0);
      expect(s.motion!.recipe.length).toBeGreaterThan(10);
    }
  });
  it("신규 4스타일은 토큰 9필드를 모두 가진다", () => {
    for (const id of ["minimal-saas", "frutiger-aero", "retro-diner", "risograph"]) {
      const t = getStyle(id)!.tokens;
      for (const k of ["bg","surface","text","primary","accent","border","fontFamily","radius","shadow"] as const) {
        expect(t[k], `${id}.${k}`).toBeTruthy();
      }
    }
  });
});
// === ANCHOR: STYLES_TEST_END ===
