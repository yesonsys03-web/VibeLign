// === ANCHOR: UNDO_CARD_START ===
import { useState } from "react";
import BackupCard from "../../backup-dashboard/BackupCard";
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
    <BackupCard
      icon={CMD.icon}
      title={CMD.title}
      subtitle={CMD.short}
      headerStyle={{ background: CMD.color + "18", padding: "8px 12px" }}
      iconStyle={{ background: CMD.color, color: "#fff", borderColor: CMD.color, width: 22, height: 22, fontSize: 11, fontWeight: 900 }}
      bodyStyle={{ padding: "6px 12px 8px" }}
      actions={
        <>
          {(st === "done" || (st === "idle" && out)) && !hasWarning && (
            <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
          )}
          {st === "error" && (
            <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
          )}
        </>
      }
    >
      <GuiCliOutputBlock text={out} placeholder={CMD.short} variant={st === "error" ? "error" : "default"} />
      <button
        className="btn btn-sm"
        style={{ width: "100%", background: CMD.color, color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
        onClick={() => onNavigate("backups")}
      >
        UNDO ▶
      </button>
    </BackupCard>
  );
}
// === ANCHOR: UNDO_CARD_END ===
