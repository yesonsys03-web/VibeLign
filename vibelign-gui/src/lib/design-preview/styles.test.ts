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
