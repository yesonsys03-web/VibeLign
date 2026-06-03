export type PlanningPersonaId = "chloe" | "gio" | "mina";

export interface PlanningPersonaMeta {
  readonly id: string;
  readonly label: string;
  readonly role: string;
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
    mention: "@미나",
    initial: "미",
    avatarBackground: "#FCEDEA",
    avatarBorder: "#1A1A1A",
    avatarColor: "#8A352D",
  },
] as const satisfies readonly PlanningPersonaMeta[];

export function allPlanningPersonaIds(): readonly string[] {
  return PLANNING_PERSONAS.map((persona) => persona.id);
}

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
    mention: "",
    initial: label.slice(0, 1) || "?",
    avatarBackground: "#FFFFFF",
    avatarBorder: "#1A1A1A",
    avatarColor: "#1A1A1A",
  };
}

export function planningPersonaLabel(personaId: string): string {
  return planningPersonaMeta(personaId).label;
}
