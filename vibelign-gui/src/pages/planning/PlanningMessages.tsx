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
      {message.personaId && (
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
          <div style={{ fontWeight: 900 }}>{personaLabel(message.personaId)}</div>
          <span
            style={{
              border: "1px solid #1A1A1A",
              background: statusBackground(message.status),
              color: statusColor(message.status),
              padding: "1px 5px",
              fontSize: 10,
              fontWeight: 900,
              lineHeight: "14px",
            }}
          >
            {statusLabel(message.status)}
          </span>
        </div>
      )}
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

function statusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "준비 중";
    case "ok":
      return "완료";
    case "failed":
      return "실패";
    default:
      return status;
  }
}

function statusBackground(status: string): string {
  switch (status) {
    case "pending":
      return "#F7F0DF";
    case "ok":
      return "#EAF5ED";
    case "failed":
      return "#FCEDEA";
    default:
      return "#FFFFFF";
  }
}

function statusColor(status: string): string {
  switch (status) {
    case "failed":
      return "#B42318";
    default:
      return "#1A1A1A";
  }
}
