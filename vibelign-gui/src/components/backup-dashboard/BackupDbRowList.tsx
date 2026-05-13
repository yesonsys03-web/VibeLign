// === ANCHOR: BACKUPDBROWLIST_START ===
import { useState } from "react";
import type { BackupDbViewerCheckpointRow } from "../../lib/vib";
import { formatBytes, formatSavedAt } from "./model";

interface BackupDbRowListProps {
  rows: BackupDbViewerCheckpointRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const DB_ROW_LIST_MAX_HEIGHT = 320;
const PAGE_SIZE = 10;

export default function BackupDbRowList({ rows, selectedId, onSelect }: BackupDbRowListProps) {
  const [page, setPage] = useState(0);

  if (rows.length === 0) {
    return <div style={{ fontSize: 12, color: "#666" }}>표시할 백업 DB row가 없어요.</div>;
  }

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const start = safePage * PAGE_SIZE;
  const paged = rows.slice(start, start + PAGE_SIZE);
  const canPrev = safePage > 0;
  const canNext = safePage < totalPages - 1;

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={{ display: "grid", gap: 6, maxHeight: DB_ROW_LIST_MAX_HEIGHT, overflowY: "auto", overscrollBehavior: "contain", paddingRight: paged.length > 6 ? 4 : 0 }}>
        {paged.map((row) => (
          <button
            key={row.checkpointId}
            type="button"
            className="btn btn-ghost btn-sm backup-row-button"
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
      {rows.length > PAGE_SIZE && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, gap: 8 }}>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!canPrev} onClick={() => setPage((p) => Math.max(0, p - 1))}>← 이전</button>
          <span style={{ color: "#666" }}>{safePage + 1} / {totalPages} 페이지 · {start + 1}–{Math.min(start + PAGE_SIZE, rows.length)} / {rows.length}</span>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!canNext} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>다음 →</button>
        </div>
      )}
    </div>
  );
}
// === ANCHOR: BACKUPDBROWLIST_END ===
