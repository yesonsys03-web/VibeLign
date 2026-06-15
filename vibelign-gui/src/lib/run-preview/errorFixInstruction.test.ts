// === ANCHOR: ERRORFIXINSTRUCTION_TEST_START ===
import { describe, expect, it } from "vitest";
import { buildRunErrorFixInstruction } from "./errorFixInstruction";

describe("buildRunErrorFixInstruction", () => {
  it("frames the failure as a start-up error, not a test failure", () => {
    const out = buildRunErrorFixInstruction({ errorText: "Error: Cannot find module 'x'", planPath: null });
    expect(out).toContain("켜지지 않고 실패");
    expect(out).toContain("테스트 실패가 아니라");
    expect(out).toContain("Error: Cannot find module 'x'");
  });

  it("references the plan only when planPath is present", () => {
    const withPlan = buildRunErrorFixInstruction({ errorText: "boom", planPath: "plans/알람앱.md" });
    expect(withPlan).toContain("plans/알람앱.md");

    const noPlan = buildRunErrorFixInstruction({ errorText: "boom", planPath: null });
    expect(noPlan).not.toContain("기획안은");
  });

  it("does NOT instruct the agent to re-run or preview (re-entrancy trap)", () => {
    const out = buildRunErrorFixInstruction({ errorText: "boom", planPath: "p.md" });
    expect(out).toContain("dev 서버를 직접 띄우지 마세요");
  });

  it("degrades gracefully when no output was captured", () => {
    // 즉시 실패(출력 0줄)면 collectErrorTail 이 정확히 "" 를 낸다 — 실제 producer 값.
    expect(buildRunErrorFixInstruction({ errorText: "", planPath: null })).toContain("캡처된 출력이 없어요");
    expect(buildRunErrorFixInstruction({ errorText: "   ", planPath: null })).toContain("캡처된 출력이 없어요");
  });
});
// === ANCHOR: ERRORFIXINSTRUCTION_TEST_END ===
