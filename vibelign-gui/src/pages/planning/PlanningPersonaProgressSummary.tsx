import type { PlanningChatMessage } from "../../lib/vib";
import { PlanningPersonaAvatar } from "./PlanningPersonaAvatar";
import { PLANNING_PERSONAS, type PlanningPersonaId } from "./PlanningPersonas";
import { planningPersonaStatusBackground, planningPersonaStatusColor, planningPersonaStatusDisplay } from "./PlanningPersonaStatusLabel";

interface PlanningPersonaProgressSummaryProps {
  readonly messages: readonly PlanningChatMessage[];
}

export function PlanningPersonaProgressSummary({ messages }: PlanningPersonaProgressSummaryProps) {
  return (
    <section
      role="status"
      aria-label="페르소나 진행"
      style={{
        border: "2px solid #1A1A1A",
        background: "#FFFFFF",
        padding: 10,
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <span style={{ fontSize: 11, fontWeight: 900 }}>페르소나 진행</span>
      {PLANNING_PERSONAS.map((persona) => {
        const status = personaProgressStatus(messages, persona.id);
        const display = planningPersonaStatusDisplay(status);
        return (
          <span
            key={persona.id}
            aria-label={`${persona.label} ${display.label}`}
            style={{
              border: "2px solid #1A1A1A",
              background: planningPersonaStatusBackground(display.tone),
              color: planningPersonaStatusColor(display.tone),
              padding: "5px 7px",
              display: "inline-flex",
              gap: 5,
              alignItems: "center",
              fontSize: 11,
              fontWeight: 900,
            }}
          >
            <PlanningPersonaAvatar personaId={persona.id} label={persona.label} size={18} />
            <span>{persona.label}</span>
            <span style={{ color: "#666" }}>{persona.role}</span>
            <span>{display.label}</span>
          </span>
        );
      })}
    </section>
  );
}

function personaProgressStatus(messages: readonly PlanningChatMessage[], personaId: PlanningPersonaId): string {
  const matchingMessages = messages.filter((message) => message.role === "assistant" && message.personaId === personaId);
  const latestMessage = matchingMessages[matchingMessages.length - 1];
  if (!latestMessage) {
    return "ready";
  }
  return latestMessage.status;
}
