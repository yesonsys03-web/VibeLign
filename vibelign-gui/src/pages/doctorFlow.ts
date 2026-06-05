// === ANCHOR: DOCTORFLOW_START ===
export type DoctorView = "report" | "plan";

export type DoctorApplyMode = "ai" | "local";

export interface DoctorLaunchIntent {
  readonly targetView: DoctorView;
  readonly applyMode: DoctorApplyMode;
}

// === ANCHOR: DOCTORFLOW_BUILDGUARDDOCTORLAUNCHINTENT_START ===
export function buildGuardDoctorLaunchIntent(hasAnyAiKey: boolean): DoctorLaunchIntent {
  return {
    targetView: "plan",
    applyMode: hasAnyAiKey ? "ai" : "local",
  };
}
// === ANCHOR: DOCTORFLOW_BUILDGUARDDOCTORLAUNCHINTENT_END ===
// === ANCHOR: DOCTORFLOW_END ===
