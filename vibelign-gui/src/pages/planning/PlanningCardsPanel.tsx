import { useState } from "react";
import type { CSSProperties } from "react";

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

interface PlanningCardsPanelProps {
  readonly cards: readonly Card[] | null | undefined;
}

export function PlanningCardsPanel({ cards }: PlanningCardsPanelProps) {
  if (!cards || cards.length === 0) {
    return null;
  }
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {cards.map((card) => (
        <CardItem key={card.id} card={card} />
      ))}
    </div>
  );
}

function CardItem({ card }: { readonly card: Card }) {
  const [open, setOpen] = useState(false);
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
    </div>
  );
}
