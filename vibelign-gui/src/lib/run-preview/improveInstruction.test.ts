import { describe, expect, it } from "vitest";
import { buildImproveInstruction } from "./improveInstruction";

describe("buildImproveInstruction", () => {
  it("frames the request as improving already-built code, not building anew", () => {
    const out = buildImproveInstruction({ requestText: "버튼 색을 더 진하게", planPath: null });
    expect(out).toContain("이미 만든 것");
    expect(out).toContain("버튼 색을 더 진하게");
  });

  it("references the plan only when planPath is present", () => {
    expect(buildImproveInstruction({ requestText: "x", planPath: "plans/p.md" })).toContain("plans/p.md");
    expect(buildImproveInstruction({ requestText: "x", planPath: null })).not.toContain("기획안은");
  });

  it("does NOT instruct the agent to re-run or preview (re-entrancy trap)", () => {
    expect(buildImproveInstruction({ requestText: "x", planPath: null })).toContain("직접 띄우지 마세요");
  });

  it("degrades when the request is empty", () => {
    expect(buildImproveInstruction({ requestText: "  ", planPath: null })).toContain("구체적인 요청이 없");
  });
});
