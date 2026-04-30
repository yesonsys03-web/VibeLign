import type { BackupEntry } from "../../lib/vib";
import BackupCard from "./BackupCard";
import { cleanBackupNote, filterBackups, formatBytes, formatSavedAt } from "./model";

interface FileHistoryTableProps {
  entries: BackupEntry[];
  query: string;
  selectedId: string | null;
  onQueryChange: (query: string) => void;
  onSelect: (id: string) => void;
}

export default function FileHistoryTable({ entries, query, selectedId, onQueryChange, onSelect }: FileHistoryTableProps) {
  const visible = filterBackups(entries, query);
  return (
    <BackupCard
      icon="📋"
      title="파일 기록"
      subtitle="메모나 날짜로 원하는 저장본을 찾아요."
      headerStyle={{ background: "#F7F7F7", padding: "12px 14px" }}
      iconStyle={{ background: "#1A1A1A", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 6 }}
      actions={
        <input className="input-field" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="검색어" style={{ width: 160, fontSize: 11 }} />
      }
    >
      {visible.map((entry) => (
        <button key={entry.id} className="btn btn-ghost btn-sm" onClick={() => onSelect(entry.id)} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center", textAlign: "left", background: selectedId === entry.id ? "#FFF1B8" : "#fff" }}>
          <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cleanBackupNote(entry)}</strong>
          <span>{formatSavedAt(entry.createdAt)}</span>
          <span>{formatBytes(entry.totalSizeBytes)}</span>
        </button>
      ))}
      {visible.length === 0 && <div style={{ fontSize: 12, color: "#666" }}>찾은 내용이 없어요.</div>}
    </BackupCard>
  );
}
