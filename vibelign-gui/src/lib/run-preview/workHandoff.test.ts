import { describe, expect, it } from "vitest";
import { buildHandoffInstruction } from "./workHandoff";

describe("buildHandoffInstruction", () => {
  it("routes error kind to the start-failure framing", () => {
    const out = buildHandoffInstruction({ kind: "error", text: "boom" }, null);
    expect(out).toContain("테스트 실패가 아니라"); // buildRunErrorFixInstruction 표식
    expect(out).toContain("boom");
  });

  it("routes improve kind to the improvement framing", () => {
    const out = buildHandoffInstruction({ kind: "improve", text: "더 빠르게" }, null);
    expect(out).toContain("이미 만든 것"); // buildImproveInstruction 표식
    expect(out).toContain("더 빠르게");
  });

  it("passes planPath through to both kinds", () => {
    expect(buildHandoffInstruction({ kind: "error", text: "x" }, "p.md")).toContain("p.md");
    expect(buildHandoffInstruction({ kind: "improve", text: "x" }, "p.md")).toContain("p.md");
  });
});
