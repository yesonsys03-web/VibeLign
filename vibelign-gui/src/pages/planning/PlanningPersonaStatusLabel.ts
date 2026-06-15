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
    case "disabled":
      return { label: "꺼짐", tone: "skipped" };
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

// === ANCHOR: PLANNINGPERSONASTATUSLABEL_FALLBACKREASONLABEL_START ===
/** fallback 사유→배지 라벨. 상태 라벨과 같은 파일에 둔다 — 새 실패 사유를 추가할 때
 *  두 표면(상태 표시·대체 배지)을 한 화면에서 같이 챙기게(리뷰 #10). */
export function fallbackReasonLabel(reason: string): string | undefined {
  switch (reason) {
    case "not_logged_in":
      return "로그인 필요";
    case "not_installed":
      return "미설치";
    case "error":
      return "응답 실패";
    case "timeout":
      return "응답 시간 초과";
    default:
      return undefined;
  }
}
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_FALLBACKREASONLABEL_END ===
// === ANCHOR: PLANNINGPERSONASTATUSLABEL_END ===
