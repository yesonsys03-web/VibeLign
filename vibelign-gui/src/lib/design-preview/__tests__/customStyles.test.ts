import { describe, expect, test } from "vitest";
import { mergeStyleLists, EXAMPLE_CHIPS } from "../customStyles";
import type { StyleSpec } from "../styles";

const mk = (id: string, name: string): StyleSpec => ({
  id, name, description: "d",
  tokens: { bg: "#fff", surface: "#fff", text: "#000", primary: "#000", accent: "#000",
    border: "1px solid #000", fontFamily: "sans-serif", radius: "8px", shadow: "none" },
  recipe: "r",
});

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
});
