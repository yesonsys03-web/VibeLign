// === ANCHOR: PLANNINGPERSONAS_START ===
export type PlanningPersonaId = "chloe" | "gio" | "mina" | "deepseek";

export interface PlanningPersonaMeta {
  readonly id: string;
  readonly label: string;
  readonly role: string;
  /** 초보용 한 줄 설명(말풍선) — 이 도우미가 뭘 하는지 + 어떤 AI인지. */
  readonly description: string;
  readonly mention: string;
  readonly initial: string;
  readonly avatarBackground: string;
  readonly avatarBorder: string;
  readonly avatarColor: string;
}

export const PLANNING_PERSONAS = [
  {
    id: "chloe",
    label: "클로이",
    role: "설계",
    description: "구현 구조를 먼저 짜주는 도우미예요 (Claude)",
    mention: "@클로이",
    initial: "클",
    avatarBackground: "#F7F0DF",
    avatarBorder: "#1A1A1A",
    avatarColor: "#2F4F6F",
  },
  {
    id: "gio",
    label: "지오",
    role: "검토",
    description: "위험한 곳·테스트를 점검해주는 도우미예요 (Codex)",
    mention: "@지오",
    initial: "지",
    avatarBackground: "#EAF5ED",
    avatarBorder: "#1A1A1A",
    avatarColor: "#275E45",
  },
  {
    id: "mina",
    label: "미나",
    role: "탐색",
    description: "놓친 점·다른 방법을 찾아주는 도우미예요 (Antigravity)",
    mention: "@미나",
    initial: "미",
    avatarBackground: "#FCEDEA",
    avatarBorder: "#1A1A1A",
    avatarColor: "#8A352D",
  },
  {
    id: "deepseek",
    label: "딥시기",
    role: "조교",
    description: "어려운 내용을 쉽게 풀어주는 도우미예요 (OpenCode)",
    mention: "@딥시기",
    initial: "딥",
    avatarBackground: "#E8ECFB",
    avatarBorder: "#1A1A1A",
    avatarColor: "#3A4DBF",
  },
] as const satisfies readonly PlanningPersonaMeta[];

// === ANCHOR: PLANNINGPERSONAS_ALLPLANNINGPERSONAIDS_START ===
export function allPlanningPersonaIds(): readonly string[] {
  return PLANNING_PERSONAS.map((persona) => persona.id);
}
// === ANCHOR: PLANNINGPERSONAS_ALLPLANNINGPERSONAIDS_END ===

// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONAMETA_START ===
export function planningPersonaMeta(personaId: string, fallbackLabel?: string): PlanningPersonaMeta {
  const knownPersona = PLANNING_PERSONAS.find((persona) => persona.id === personaId);
  if (knownPersona) {
    return knownPersona;
  }
  const label = fallbackLabel?.trim() || personaId || "페르소나";
  return {
    id: personaId,
    label,
    role: "",
    description: "",
    mention: "",
    initial: label.slice(0, 1) || "?",
    avatarBackground: "#FFFFFF",
    avatarBorder: "#1A1A1A",
    avatarColor: "#1A1A1A",
  };
}
// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONAMETA_END ===

// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONALABEL_START ===
export function planningPersonaLabel(personaId: string): string {
  return planningPersonaMeta(personaId).label;
}
// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONALABEL_END ===

// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONAROLELABEL_START ===
export function planningPersonaRoleLabel(personaId: string): string {
  const persona = planningPersonaMeta(personaId);
  return persona.role ? `${persona.role}자 ${persona.label}` : persona.label;
}
// === ANCHOR: PLANNINGPERSONAS_PLANNINGPERSONAROLELABEL_END ===
// === ANCHOR: PLANNINGPERSONAS_END ===
