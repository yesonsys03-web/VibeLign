import type { BackupEntry } from "../../lib/vib";
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
    <section className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#F7F7F7", padding: "12px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#1A1A1A", borderColor: "#1A1A1A", color: "#fff" }}>📋</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 900, fontSize: 17 }}>파일 기록</div>
          <div style={{ fontSize: 11, color: "#555" }}>메모나 날짜로 원하는 저장본을 찾아요.</div>
        </div>
        <input className="input-field" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="검색어" style={{ width: 160, fontSize: 11 }} />
      </div>
      <div className="feature-card-body" style={{ display: "grid", gap: 6 }}>
        {visible.map((entry) => (
          <button key={entry.id} className="btn btn-ghost btn-sm" onClick={() => onSelect(entry.id)} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center", textAlign: "left", background: selectedId === entry.id ? "#FFF1B8" : "#fff" }}>
            <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cleanBackupNote(entry)}</strong>
            <span>{formatSavedAt(entry.createdAt)}</span>
            <span>{formatBytes(entry.totalSizeBytes)}</span>
          </button>
        ))}
        {visible.length === 0 && <div style={{ fontSize: 12, color: "#666" }}>찾은 내용이 없어요.</div>}
      </div>
    </section>
  );
}
