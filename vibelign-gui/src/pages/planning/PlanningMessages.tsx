import type { PlanningChatMessage } from "../../lib/vib";
import { PlanningPersonaAvatar } from "./PlanningPersonaAvatar";
import { planningPersonaLabel } from "./PlanningPersonas";
import { planningPersonaStatusBackground, planningPersonaStatusColor, planningPersonaStatusDisplay } from "./PlanningPersonaStatusLabel";

interface PlanningMessagesProps {
  readonly messages: readonly PlanningChatMessage[];
  readonly outputPath: string | null;
}

export function PlanningMessages({ messages, outputPath }: PlanningMessagesProps) {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {messages.map((message) => (
        <PlanningMessageBubble key={message.id} message={message} />
      ))}
      {outputPath && <div style={{ fontSize: 12, color: "#555", fontWeight: 700 }}>저장 위치: {outputPath}</div>}
    </div>
  );
}

function PlanningMessageBubble({ message }: { readonly message: PlanningChatMessage }) {
  const isUser = message.role === "user";
  const display = planningPersonaStatusDisplay(message.status, "message");
  return (
    <div
      style={{
        justifySelf: isUser ? "end" : "start",
        maxWidth: isUser ? 680 : 720,
        border: "2px solid #1A1A1A",
        background: isUser ? "#FFFFFF" : "#F5F1E3",
        padding: 12,
        fontSize: 13,
        fontWeight: isUser ? 700 : 500,
        lineHeight: 1.5,
        whiteSpace: "pre-wrap",
      }}
    >
      {message.personaId && (
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
          <PlanningPersonaAvatar personaId={message.personaId} label={planningPersonaLabel(message.personaId)} decorative size={18} />
          <div style={{ fontWeight: 900 }}>{planningPersonaLabel(message.personaId)}</div>
          <span
            style={{
              border: "1px solid #1A1A1A",
              background: planningPersonaStatusBackground(display.tone),
              color: planningPersonaStatusColor(display.tone),
              padding: "1px 5px",
              fontSize: 10,
              fontWeight: 900,
              lineHeight: "14px",
            }}
          >
            {display.label}
          </span>
        </div>
      )}
      {message.content}
    </div>
  );
}
