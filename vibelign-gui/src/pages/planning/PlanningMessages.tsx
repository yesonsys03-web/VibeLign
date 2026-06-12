// === ANCHOR: PLANNINGMESSAGES_START ===
import type { PlanningChatMessage } from "../../lib/vib";
import { PlanningPersonaAvatar } from "./PlanningPersonaAvatar";
import { planningPersonaLabel } from "./PlanningPersonas";
import { fallbackReasonLabel, planningPersonaStatusBackground, planningPersonaStatusColor, planningPersonaStatusDisplay } from "./PlanningPersonaStatusLabel";

// === ANCHOR: PLANNINGMESSAGES_FALLBACKBADGELABEL_START ===
export function fallbackBadgeLabel(message: PlanningChatMessage): string | null {
  if (!message.providerUsed) return null;
  const base = `${message.providerUsed}로 대체됨`;
  const reason = message.fallbackReason ? fallbackReasonLabel(message.fallbackReason) : undefined;
  return reason ? `${base} · ${reason}` : base;
}
// === ANCHOR: PLANNINGMESSAGES_FALLBACKBADGELABEL_END ===

interface PlanningMessagesProps {
  readonly messages: readonly PlanningChatMessage[];
  readonly outputPath: string | null;
  readonly onRetry?: (message: PlanningChatMessage) => void;
}

// === ANCHOR: PLANNINGMESSAGES_PLANNINGMESSAGES_START ===
export function PlanningMessages({ messages, outputPath, onRetry }: PlanningMessagesProps) {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {messages.map((message) => (
        <PlanningMessageBubble key={message.id} message={message} onRetry={onRetry} />
      ))}
      {outputPath && <div style={{ fontSize: 12, color: "#555", fontWeight: 700 }}>저장 위치: {outputPath}</div>}
    </div>
  );
}
// === ANCHOR: PLANNINGMESSAGES_PLANNINGMESSAGES_END ===

// === ANCHOR: PLANNINGMESSAGES_PLANNINGMESSAGEBUBBLE_START ===
function PlanningMessageBubble({
  message,
  onRetry,
}: {
  readonly message: PlanningChatMessage;
  readonly onRetry?: (message: PlanningChatMessage) => void;
}) {
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
              fontSize: 12,
              fontWeight: 900,
              lineHeight: "14px",
            }}
          >
            {display.label}
          </span>
          {(() => {
            const fb = fallbackBadgeLabel(message);
            return fb ? (
              <span
                title="고른 AI가 없거나 실패해서 다른 AI가 대신 답했어요"
                style={{
                  border: "1px solid #8A352D",
                  background: "#FCEDEA",
                  color: "#8A352D",
                  padding: "1px 5px",
                  fontSize: 12,
                  fontWeight: 900,
                  lineHeight: "14px",
                }}
              >
                {fb}
              </span>
            ) : null;
          })()}
        </div>
      )}
      {message.content}
      {message.status === "failed" && onRetry && (
        <div style={{ marginTop: 8 }}>
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            onClick={() => onRetry(message)}
            style={{ fontSize: 12 }}
          >
            다시 시도
          </button>
        </div>
      )}
    </div>
  );
}
// === ANCHOR: PLANNINGMESSAGES_PLANNINGMESSAGEBUBBLE_END ===
// === ANCHOR: PLANNINGMESSAGES_END ===
