// === ANCHOR: CUSTOMSTYLES_TEST_START ===
import { describe, expect, test } from "vitest";
import { mergeStyleLists, EXAMPLE_CHIPS, tokensToCssVars, replaceRootBlock } from "../customStyles";
import type { StyleSpec } from "../styles";

// === ANCHOR: CUSTOMSTYLES_TEST_MK_START ===
const mk = (id: string, name: string): StyleSpec => ({
  id, name, description: "d",
  tokens: { bg: "#fff", surface: "#fff", text: "#000", primary: "#000", accent: "#000",
    border: "1px solid #000", fontFamily: "sans-serif", radius: "8px", shadow: "none" },
  recipe: "r",
});
// === ANCHOR: CUSTOMSTYLES_TEST_MK_END ===

describe("customStyles", () => {
  test("mergeStyleLists: 내장 뒤에 커스텀을 붙인다", () => {
    const merged = mergeStyleLists([mk("a", "A")], [mk("custom-1", "C")]);
    expect(merged.map((s) => s.id)).toEqual(["a", "custom-1"]);
  });
  test("mergeStyleLists: 같은 id 커스텀은 내장을 가리지 않고 한 번만(커스텀 우선)", () => {
    const merged = mergeStyleLists([mk("a", "A")], [mk("a", "A-custom")]);
    expect(merged).toHaveLength(1);
    expect(merged[0].name).toBe("A-custom");
  });
  test("EXAMPLE_CHIPS: 비어있지 않은 일상어 시드", () => {
    expect(EXAMPLE_CHIPS.length).toBeGreaterThanOrEqual(4);
    expect(EXAMPLE_CHIPS.every((c) => c.trim().length > 0)).toBe(true);
  });

  test("tokensToCssVars: 변경된 색이 :root 변수로 들어간다", () => {
    const css = tokensToCssVars({ ...mk("x", "X").tokens, primary: "#ff0000" });
    expect(css.startsWith(":root{")).toBe(true);
    expect(css).toContain("--primary:#ff0000;");
    expect(css).toContain("--font:sans-serif;");
  });
  test("tokensToCssVars: motion 있으면 --dur/--ease 합류", () => {
    const css = tokensToCssVars(mk("x", "X").tokens, { tokens: { duration: "200ms", easing: "ease" }, recipe: "r" });
    expect(css).toContain("--dur:200ms;");
    expect(css).toContain("--ease:ease;");
    expect(css.endsWith("}")).toBe(true);
  });
  test("replaceRootBlock: 첫 :root 블록만 치환, 매치 없으면 원본", () => {
    const html = "<style>:root{--bg:#000;} .x{color:red}</style>";
    const out = replaceRootBlock(html, ":root{--bg:#fff;}");
    expect(out).toBe("<style>:root{--bg:#fff;} .x{color:red}</style>");
    expect(replaceRootBlock("<style>.x{}</style>", ":root{--bg:#fff;}")).toBe("<style>.x{}</style>");
  });
});
// === ANCHOR: CUSTOMSTYLES_TEST_END ===
