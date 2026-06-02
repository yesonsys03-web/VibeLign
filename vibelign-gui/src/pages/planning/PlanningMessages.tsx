import type { PlanningChatMessage } from "../../lib/vib";

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
      {message.personaId && <div style={{ fontWeight: 900, marginBottom: 6 }}>{personaLabel(message.personaId)}</div>}
      {message.content}
    </div>
  );
}

function personaLabel(personaId: string): string {
  switch (personaId) {
    case "chloe":
      return "클로이";
    case "gio":
      return "지오";
    case "mina":
      return "미나";
    default:
      return personaId;
  }
}
