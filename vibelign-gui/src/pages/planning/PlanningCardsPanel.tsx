import { useState } from "react";
import type { CSSProperties } from "react";

import { updateCard } from "../../lib/vib";
import type { Card, CardState } from "../../lib/vib/types";

const STATE_STYLE: Record<CardState, CSSProperties> = {
  draft: { borderStyle: "dashed", opacity: 0.6 },
  held: { borderStyle: "dashed", opacity: 0.6, marginLeft: 24 },
  confirmed: { borderStyle: "solid", opacity: 1 },
};

const STATE_LABEL: Record<CardState, string> = {
  draft: "초안",
  held: "보류",
  confirmed: "확정",
};

type CardAction = "confirm" | "hold" | "reject";

interface PlanningCardsPanelProps {
  readonly cards: readonly Card[] | null | undefined;
  readonly projectDir: string;
  readonly sessionId: string | null;
  readonly onCardsChange: (cards: readonly Card[]) => void;
}

export function PlanningCardsPanel({ cards, projectDir, sessionId, onCardsChange }: PlanningCardsPanelProps) {
  const [busyId, setBusyId] = useState<string | null>(null);

  if (!cards || cards.length === 0) {
    return null;
  }

  async function handleAction(cardId: string, action: CardAction) {
    if (!sessionId || busyId) {
      return;
    }
    setBusyId(cardId);
    try {
      const result = await updateCard({ projectDir, sessionId, cardId, action });
      if (result.ok) {
        onCardsChange(result.cards);
      }
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {cards.map((card) => (
        <CardItem key={card.id} card={card} busy={busyId === card.id} onAction={handleAction} />
      ))}
    </div>
  );
}

function CardItem({
  card,
  busy,
  onAction,
}: {
  readonly card: Card;
  readonly busy: boolean;
  readonly onAction: (cardId: string, action: CardAction) => void;
}) {
  const [open, setOpen] = useState(false);
  const showButtons = card.state === "draft" || card.state === "held";
  return (
    <div
      style={{
        border: "2px solid #1A1A1A",
        background: "#FEFBF0",
        padding: "10px 12px",
        transition: "opacity 0.3s ease, border-style 0.3s ease",
        ...STATE_STYLE[card.state],
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <strong style={{ fontSize: 12 }}>{card.title}</strong>
        <span style={{ fontSize: 10, opacity: 0.7 }}>{STATE_LABEL[card.state]}</span>
      </div>
      {card.summary && <div style={{ fontSize: 11, marginTop: 4 }}>{card.summary}</div>}
      {card.reason && (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          style={{ fontSize: 10, marginTop: 6, background: "none", border: "none", cursor: "pointer", padding: 0, textDecoration: "underline" }}
        >
          {open ? "이유 접기" : "이유 보기"}
        </button>
      )}
      {open && card.reason && <div style={{ fontSize: 11, marginTop: 4, opacity: 0.85 }}>{card.reason}</div>}
      {showButtons && (
        <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
          <button type="button" disabled={busy} onClick={() => onAction(card.id, "confirm")} style={cardBtnStyle}>✓ 동의</button>
          <button type="button" disabled={busy} onClick={() => onAction(card.id, "hold")} style={cardBtnStyle}>⏸ 보류</button>
          <button type="button" disabled={busy} onClick={() => onAction(card.id, "reject")} style={cardBtnStyle}>✕ 빼기</button>
        </div>
      )}
    </div>
  );
}

const cardBtnStyle: CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  border: "1.5px solid #1A1A1A",
  background: "#fff",
  padding: "3px 8px",
  cursor: "pointer",
};
