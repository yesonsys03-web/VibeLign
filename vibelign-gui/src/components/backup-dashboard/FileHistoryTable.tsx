// === ANCHOR: FILEHISTORYTABLE_START ===
import { useEffect, useRef, useState } from "react";
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

const HISTORY_LIST_MAX_HEIGHT = 320;
const PAGE_SIZE = 10;

export default function FileHistoryTable({ entries, query, selectedId, onQueryChange, onSelect }: FileHistoryTableProps) {
  const visible = filterBackups(entries, query);
  const selectedButtonRef = useRef<HTMLButtonElement | null>(null);
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const start = safePage * PAGE_SIZE;
  const paged = visible.slice(start, start + PAGE_SIZE);

  useEffect(() => { setPage(0); }, [query]);

  useEffect(() => {
    if (!selectedId) return;
    const idx = visible.findIndex((entry) => entry.id === selectedId);
    if (idx < 0) return;
    const targetPage = Math.floor(idx / PAGE_SIZE);
    setPage((current) => (current === targetPage ? current : targetPage));
  }, [selectedId, visible]);

  useEffect(() => {
    selectedButtonRef.current?.scrollIntoView({ block: "nearest" });
  }, [selectedId, safePage]);

  const canPrev = safePage > 0;
  const canNext = safePage < totalPages - 1;

  return (
    <BackupCard
      icon="📋"
      title="파일 기록"
      subtitle="메모나 날짜로 원하는 저장본을 찾아요."
      headerStyle={{ background: "#F7F7F7", padding: "12px 14px" }}
      iconStyle={{ background: "#1A1A1A", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 8 }}
      actions={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 800, whiteSpace: "nowrap" }}>{visible.length}/{entries.length}</span>
          <input className="input-field" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="검색어" style={{ width: 160, fontSize: 11 }} />
        </div>
      }
    >
      <div style={{ display: "grid", gap: 6, maxHeight: HISTORY_LIST_MAX_HEIGHT, overflowY: "auto", overscrollBehavior: "contain", paddingRight: paged.length > 6 ? 4 : 0 }}>
        {paged.map((entry) => (
          <button key={entry.id} ref={selectedId === entry.id ? selectedButtonRef : null} className="btn btn-ghost btn-sm backup-row-button" onClick={() => onSelect(entry.id)} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center", textAlign: "left", background: selectedId === entry.id ? "#FFF1B8" : "#fff" }}>
            <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cleanBackupNote(entry)}</strong>
            <span>{formatSavedAt(entry.createdAt)}</span>
            <span>{formatBytes(entry.totalSizeBytes)}</span>
          </button>
        ))}
        {paged.length === 0 && <div style={{ fontSize: 12, color: "#666" }}>찾은 내용이 없어요.</div>}
      </div>
      {visible.length > PAGE_SIZE && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, gap: 8 }}>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!canPrev} onClick={() => setPage((p) => Math.max(0, p - 1))}>← 이전</button>
          <span style={{ color: "#666" }}>{safePage + 1} / {totalPages} 페이지 · {start + 1}–{Math.min(start + PAGE_SIZE, visible.length)} / {visible.length}</span>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!canNext} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>다음 →</button>
        </div>
      )}
    </BackupCard>
  );
}
// === ANCHOR: FILEHISTORYTABLE_END ===
