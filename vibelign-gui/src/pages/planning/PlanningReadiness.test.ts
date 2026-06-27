// === ANCHOR: PLANNINGREADINESS_TEST_START ===
import { describe, expect, it } from "vitest";

import type { ReadinessReport, RequirementReadiness } from "../../lib/vib/types";
import { readinessSummary } from "./PlanningReadiness";

// === ANCHOR: PLANNINGREADINESS_TEST_REQ_START ===
function req(title: string, core: boolean, triggerRed: boolean): RequirementReadiness {
  const ok = { verdict: "green", note: "" } as const;
  return {
    title,
    summary: "",
    core,
    checks: {
      trigger: triggerRed ? { verdict: "red", note: "미정" } : ok,
      data: ok,
      logic: ok,
      acceptance: ok,
      edge: ok,
      platform: { verdict: "na", note: "" },
    },
  };
}
// === ANCHOR: PLANNINGREADINESS_TEST_REQ_END ===

describe("readinessSummary", () => {
  it("counts green/red and blocks when a core requirement has red", () => {
    const report: ReadinessReport = {
      status: "judged",
      requirements: [req("핵심카드", true, true), req("안내문구", false, false)],
    };
    const summary = readinessSummary(report);
    expect(summary.green).toBe(1);
    expect(summary.red).toBe(1);
    expect(summary.coreRedCount).toBe(1);
    expect(summary.canStartWork).toBe(false);
  });

  it("allows start when no core red", () => {
    const report: ReadinessReport = {
      status: "judged",
      requirements: [req("부가", false, true)],
    };
    expect(readinessSummary(report).canStartWork).toBe(true);
  });

  it("treats unavailable and missing report as start-allowed (no judgment to block on)", () => {
    expect(readinessSummary({ status: "unavailable", requirements: [] }).canStartWork).toBe(true);
    expect(readinessSummary(null).canStartWork).toBe(true);
    expect(readinessSummary(undefined).canStartWork).toBe(true);
  });
});
// === ANCHOR: PLANNINGREADINESS_TEST_END ===
