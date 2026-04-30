// === ANCHOR: UNDO_CARD_START ===
import { useState } from "react";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";
import { COMMANDS, CardState } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "undo")!;

interface UndoCardProps {
  projectDir: string;
  onNavigate: (page: "backups") => void;
}

export default function UndoCard({ onNavigate }: UndoCardProps) {
  const [st] = useState<CardState>("idle");
  const [out] = useState("");
  const hasWarning = false;

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: CMD.color + "18", padding: "8px 12px" }}>
        <div className="feature-card-icon" style={{
          background: CMD.color, color: "#fff", borderColor: CMD.color,
          width: 22, height: 22, fontSize: 11, fontWeight: 900,
        }}>{CMD.icon}</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{CMD.title}</span>
          <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{CMD.short}</span>
        </div>
        {(st === "done" || (st === "idle" && out)) && !hasWarning && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
        {st === "error" && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
        <GuiCliOutputBlock text={out} placeholder={CMD.short} variant={st === "error" ? "error" : "default"} />
        <button
          className="btn btn-sm"
          style={{ width: "100%", background: CMD.color, color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
          onClick={() => onNavigate("backups")}
        >
          UNDO ▶
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: UNDO_CARD_END ===
