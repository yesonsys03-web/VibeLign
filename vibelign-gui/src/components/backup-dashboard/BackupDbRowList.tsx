import type { BackupDbViewerCheckpointRow } from "../../lib/vib";
import { formatBytes, formatSavedAt } from "./model";

interface BackupDbRowListProps {
  rows: BackupDbViewerCheckpointRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const DB_ROW_LIST_MAX_HEIGHT = 320;

export default function BackupDbRowList({ rows, selectedId, onSelect }: BackupDbRowListProps) {
  if (rows.length === 0) {
    return <div style={{ fontSize: 12, color: "#666" }}>표시할 백업 DB row가 없어요.</div>;
  }
  return (
    <div style={{ display: "grid", gap: 6, maxHeight: DB_ROW_LIST_MAX_HEIGHT, overflowY: "auto", overscrollBehavior: "contain", paddingRight: rows.length > 6 ? 4 : 0 }}>
      {rows.map((row) => (
        <button
          key={row.checkpointId}
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => onSelect(row.checkpointId)}
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.4fr) auto auto",
            gap: 10,
            alignItems: "center",
            textAlign: "left",
            background: selectedId === row.checkpointId ? "#FFF1B8" : "#fff",
          }}
        >
          <span style={{ minWidth: 0 }}>
            <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.displayName}</strong>
            <span style={{ fontSize: 11, color: "#666" }}>{row.triggerLabel} · {formatSavedAt(row.createdAt)} · {row.fileCount}개 파일</span>
          </span>
          <span>{formatBytes(row.storedSizeBytes || row.totalSizeBytes)}</span>
          <span style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {row.internalBadges.slice(0, 3).map((badge) => <span key={badge} className="badge badge-ghost">{badge}</span>)}
          </span>
        </button>
      ))}
    </div>
  );
}
