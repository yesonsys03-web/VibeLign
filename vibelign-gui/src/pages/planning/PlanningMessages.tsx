// === ANCHOR: PLANNINGMESSAGES_START ===
import { useEffect, useRef } from "react";
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
  // 스마트 자동 스크롤: 사용자가 최신 메시지 근처에 있을 때만 새 답변으로 따라간다.
  // 위에서 이전 대화를 읽는 중이면 가로채지 않는다. 스크롤 컨테이너는 .page-content.
  const listRef = useRef<HTMLDivElement>(null);
  const followRef = useRef(true);
  useEffect(() => {
    const container = document.querySelector<HTMLElement>(".page-content");
    if (!container) return;
    const onScroll = () => {
      const list = listRef.current;
      if (!list) return;
      // 입력창·액션바가 메시지 목록 아래에 있으므로 페이지 끝이 아니라 '목록 끝'을 기준으로
      // 따라가기 여부를 판단한다(getBoundingClientRect 로 위치 무관 계산).
      const listBottom = list.getBoundingClientRect().bottom;
      const viewBottom = container.getBoundingClientRect().bottom;
      followRef.current = listBottom - viewBottom <= 220;
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => container.removeEventListener("scroll", onScroll);
  }, []);

  // 새 메시지/응답이 추가되면 페이지 맨 아래가 아니라 '그 답변 메시지'로 스크롤한다.
  const last = messages[messages.length - 1];
  const tail = `${messages.length}:${last?.id ?? ""}:${last?.content.length ?? 0}:${last?.status ?? ""}`;
  useEffect(() => {
    if (!followRef.current) return;
    const bubbles = listRef.current?.querySelectorAll<HTMLElement>("[data-planning-msg]");
    const lastBubble = bubbles?.[bubbles.length - 1];
    if (typeof lastBubble?.scrollIntoView === "function") {
      lastBubble.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [tail]);

  return (
    <div ref={listRef} style={{ display: "grid", gap: 12 }}>
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
      data-planning-msg
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
      {message.status === "pending" ? (
        // 답변 대기 중에는 placeholder 텍스트 대신 갸리카가 부릉부릉 달리는 로딩 애니메이션만 보여준다.
        <span
          className="gyari-loader"
          role="img"
          aria-label={`${message.personaId ? planningPersonaLabel(message.personaId) : "AI"} 답변을 준비하는 중`}
        />
      ) : (
        message.content
      )}
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
