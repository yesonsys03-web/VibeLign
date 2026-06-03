import type { CreatePlanningTemplateResponse } from "../../lib/vib";
import { PLANNING_PERSONAS, type PlanningPersonaMeta } from "./PlanningPersonas";
import { planningPersonaStatusDisplay } from "./PlanningPersonaStatusLabel";

interface PlanningPersonaStatusProps {
  readonly result: CreatePlanningTemplateResponse;
}

export function PlanningPersonaStatus({ result }: PlanningPersonaStatusProps) {
  const requested = result.agentsRequested?.length ? result.agentsRequested : legacyRequested(result);
  if (!requested.length) {
    return null;
  }
  const statuses = result.agentStatuses ?? {};
  const anyPending = requested.some((id) => (statuses[id] ?? result.llmStatus) === "pending");
  const anyOk = requested.some((id) => (statuses[id] ?? result.llmStatus) === "ok");
  const message = anyPending
    ? "AI들이 기획안을 나눠서 확인하는 중이에요."
    : anyOk
      ? "AI들이 기획안을 역할별로 확인했어요."
      : "AI 연결은 아직 준비되지 않았지만, 기본 기획안은 저장했어요.";

  return (
    <section
      role="status"
      style={{
        border: "2px solid #1A1A1A",
        background: anyOk ? "#EAF8EF" : "#FFF5D6",
        padding: "10px 12px",
        display: "grid",
        gap: 10,
      }}
    >
      <strong style={{ fontSize: 12 }}>{message}</strong>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {PLANNING_PERSONAS.filter((persona) => requested.includes(persona.id)).map((persona) => (
          <PersonaChip key={persona.id} persona={persona} status={statuses[persona.id] ?? result.llmStatus ?? "unknown"} />
        ))}
      </div>
    </section>
  );
}

function PersonaChip({ persona, status }: { readonly persona: PlanningPersonaMeta; readonly status: string }) {
  return (
    <span
      style={{
        border: "2px solid #1A1A1A",
        background: status === "ok" ? "#FFFFFF" : "#F7F0DF",
        padding: "6px 8px",
        fontSize: 11,
        fontWeight: 800,
        display: "inline-flex",
        gap: 6,
        alignItems: "center",
      }}
    >
      <span>{persona.label}</span>
      <span style={{ color: "#6F6F6F" }}>{persona.role}</span>
      <span>{statusLabel(status)}</span>
    </span>
  );
}

function legacyRequested(result: CreatePlanningTemplateResponse): readonly string[] {
  if (result.personaId) {
    return [result.personaId];
  }
  if (result.adapter || result.llmStatus) {
    return ["gio"];
  }
  return [];
}

function statusLabel(status: string): string {
  return planningPersonaStatusDisplay(status).label;
}
