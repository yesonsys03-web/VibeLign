import type { CSSProperties } from "react";
import type { BackupEntry } from "../../lib/vib";
import BackupCard from "./BackupCard";
import { cleanBackupNote, formatRelativeTime, formatSavedAt } from "./model";

const chipBase: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  padding: "3px 9px",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
  border: "1px solid #1A1A1A",
  background: "#fff",
  lineHeight: 1.4,
};
const chipTime: CSSProperties = { ...chipBase, background: "#F0F4FF" };
const chipFiles: CSSProperties = { ...chipBase, background: "#FFF8E1" };
const chipSafe: CSSProperties = { ...chipBase, background: "#E6F8EE", borderColor: "#1E9E5A", color: "#0E6B3C" };
const chipRow: CSSProperties = { display: "flex", gap: 6, flexWrap: "wrap" };

interface RestorePreviewPanelProps {
  entry: BackupEntry | null;
  restoring: boolean;
  onRestore: (id: string) => void;
}

export default function RestorePreviewPanel({ entry, restoring, onRestore }: RestorePreviewPanelProps) {
  return (
    <BackupCard
      icon="🔎"
      title="되돌리기 전 확인"
      subtitle="선택한 저장본을 한 번 더 확인해요."
      headerStyle={{ background: "#EFFFF9", padding: "12px 14px" }}
      iconStyle={{ background: "#00A88F", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 10 }}
    >
      {entry ? (
        <>
          <strong>{cleanBackupNote(entry)}</strong>
          <div style={chipRow}>
            <span style={chipTime} title={formatSavedAt(entry.createdAt)}>🕐 {formatRelativeTime(entry.createdAt)}</span>
            <span style={chipFiles}>📄 {entry.fileCount ?? 0}개 파일</span>
            <span style={chipSafe}>✓ 안전</span>
          </div>
          <div className="alert alert-success" style={{ margin: 0 }}>한 파일만 골라 되돌릴 때도 다른 파일은 그대로 둡니다.</div>
          <button className="btn btn-sm" disabled={restoring} onClick={() => onRestore(entry.id)}>
            {restoring ? <span className="spinner" /> : "이 저장본으로 되돌리기"}
          </button>
        </>
      ) : (
        <div style={{ fontSize: 12, color: "#666" }}>아래 목록에서 저장본을 고르면 여기서 확인할 수 있어요.</div>
      )}
    </BackupCard>
  );
}
