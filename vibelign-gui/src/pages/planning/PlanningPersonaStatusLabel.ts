// === ANCHOR: PLANNINGPERSONASTATUSLABEL_START ===
export type PlanningPersonaStatusTone = "ready" | "pending" | "ok" | "failed" | "needsConnection" | "skipped" | "unknown";

export interface PlanningPersonaStatusDisplay {
  readonly label: string;
  readonly tone: PlanningPersonaStatusTone;
}

type PlanningPersonaStatusSurface = "progress" | "message";

// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSDISPLAY_START ===
export function planningPersonaStatusDisplay(status: string, surface: PlanningPersonaStatusSurface = "progress"): PlanningPersonaStatusDisplay {
  switch (status) {
    case "ready":
      return { label: "준비됨", tone: "ready" };
    case "pending":
      return { label: surface === "message" ? "준비 중" : "검토 중", tone: "pending" };
    case "ok":
      return { label: "완료", tone: "ok" };
    case "failed":
      return { label: "실패", tone: "failed" };
    case "not_installed":
    case "not_logged_in":
    case "tty_required":
      return { label: "연결 필요", tone: "needsConnection" };
    case "timeout":
    case "rate_limited":
    case "bad_output":
    case "terms_blocked":
    case "process_error":
      return { label: "건너뜀", tone: "skipped" };
    default:
      return { label: status, tone: "unknown" };
  }
}
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSDISPLAY_END ===

// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSBACKGROUND_START ===
export function planningPersonaStatusBackground(tone: PlanningPersonaStatusTone): string {
  switch (tone) {
    case "ready":
      return "#F7F0DF";
    case "pending":
      return "#FFF5D6";
    case "ok":
      return "#EAF5ED";
    case "failed":
      return "#FCEDEA";
    case "needsConnection":
      return "#F1F4F8";
    case "skipped":
      return "#F7F0DF";
    case "unknown":
      return "#FFFFFF";
  }
}
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSBACKGROUND_END ===

// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSCOLOR_START ===
export function planningPersonaStatusColor(tone: PlanningPersonaStatusTone): string {
  switch (tone) {
    case "failed":
      return "#B42318";
    case "needsConnection":
      return "#315F7C";
    case "skipped":
      return "#6F4F1F";
    case "ready":
    case "pending":
    case "ok":
    case "unknown":
      return "#1A1A1A";
  }
}
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_PLANNINGPERSONASTATUSCOLOR_END ===
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_END ===
