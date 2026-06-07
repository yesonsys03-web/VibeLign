import type { ReadinessReport, RequirementReadiness } from "../../lib/vib/types";

export interface ReadinessSummary {
  status: "judged" | "unavailable" | "none";
  green: number;
  red: number;
  coreRedCount: number;
  canStartWork: boolean;
}

function requirementHasRed(requirement: RequirementReadiness): boolean {
  return Object.values(requirement.checks).some((check) => check.verdict === "red");
}

export function readinessSummary(report: ReadinessReport | null | undefined): ReadinessSummary {
  if (!report || report.status !== "judged") {
    return {
      status: report?.status ?? "none",
      green: 0,
      red: 0,
      coreRedCount: 0,
      canStartWork: true, // 판정이 없으면 막을 근거도 없다(정직함: 가짜 차단 금지).
    };
  }
  let green = 0;
  let red = 0;
  let coreRedCount = 0;
  for (const requirement of report.requirements) {
    const hasRed = requirementHasRed(requirement);
    if (hasRed) {
      red += 1;
      if (requirement.core) {
        coreRedCount += 1;
      }
    } else {
      green += 1;
    }
  }
  return { status: "judged", green, red, coreRedCount, canStartWork: coreRedCount === 0 };
}
