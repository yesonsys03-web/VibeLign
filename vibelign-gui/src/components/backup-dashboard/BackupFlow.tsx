import type { BackupEntry } from "../../lib/vib";
import BackupCard from "./BackupCard";
import { cleanBackupNote, formatSavedAt } from "./model";

interface BackupFlowProps {
  entries: BackupEntry[];
}

export default function BackupFlow({ entries }: BackupFlowProps) {
  return (
    <BackupCard
      icon="🧭"
      title="저장 흐름"
      subtitle="최근 보관 순서를 짧게 보여 줘요."
      headerStyle={{ background: "#F0E7FF", padding: "12px 14px" }}
      iconStyle={{ background: "#7B4DFF", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 8 }}
    >
      {entries.slice(0, 5).map((entry) => (
        <div key={entry.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: 8, border: "2px solid #1A1A1A", background: "#fff" }}>
          <span style={{ fontSize: 18 }}>{entry.sourceKind === "auto" ? "🤖" : "✍️"}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cleanBackupNote(entry)}</div>
            <div style={{ fontSize: 11, color: "#666" }}>{formatSavedAt(entry.createdAt)}</div>
          </div>
        </div>
      ))}
      {entries.length === 0 && <div style={{ fontSize: 12, color: "#666" }}>저장 버튼을 눌러 첫 보관을 만들 수 있어요.</div>}
    </BackupCard>
  );
}
