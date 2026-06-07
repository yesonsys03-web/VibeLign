// === ANCHOR: PLANNINGMODES_START ===
import { allPlanningPersonaIds, planningPersonaLabel } from "./PlanningPersonas";

export interface PlanningModeOption {
  readonly id: "instant" | "draft" | "explore" | "full";
  readonly label: string;
  readonly targetLabel: string;
  readonly personaIds: readonly string[];
}

export const PLANNING_MODE_OPTIONS = [
  { id: "instant", label: "Instant", targetLabel: planningPersonaLabel("gio"), personaIds: ["gio"] },
  { id: "draft", label: "초안", targetLabel: planningPersonaLabel("chloe"), personaIds: ["chloe"] },
  { id: "explore", label: "탐색", targetLabel: planningPersonaLabel("mina"), personaIds: ["mina"] },
  { id: "full", label: "전체", targetLabel: "모두", personaIds: allPlanningPersonaIds() },
] as const satisfies readonly PlanningModeOption[];

export const DEFAULT_PLANNING_MODE = PLANNING_MODE_OPTIONS[0];

// === ANCHOR: PLANNINGMODES_RESOLVEPLANNINGMODE_START ===
export function resolvePlanningMode(value: string): PlanningModeOption {
  return PLANNING_MODE_OPTIONS.find((option) => option.id === value) ?? DEFAULT_PLANNING_MODE;
}
// === ANCHOR: PLANNINGMODES_RESOLVEPLANNINGMODE_END ===
// === ANCHOR: PLANNINGMODES_END ===
