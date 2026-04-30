import type { BackupEntry } from "../../lib/vib";
import BackupCard from "./BackupCard";
import { cleanBackupNote, formatSavedAt } from "./model";

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
          <span style={{ fontSize: 12, color: "#555" }}>{formatSavedAt(entry.createdAt)} · {entry.fileCount ?? 0}개 파일</span>
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
