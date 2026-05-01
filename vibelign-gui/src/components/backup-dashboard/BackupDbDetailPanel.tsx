import type { BackupDbViewerCheckpointRow, BackupDbViewerInspectResult } from "../../lib/vib";
import BackupCard from "./BackupCard";
import { formatBytes, formatSavedAt } from "./model";

interface BackupDbDetailPanelProps {
  report: BackupDbViewerInspectResult;
  row: BackupDbViewerCheckpointRow | null;
}

export default function BackupDbDetailPanel({ report, row }: BackupDbDetailPanelProps) {
  return (
    <BackupCard
      icon="🔍"
      title="DB row 상세"
      subtitle="사람이 먼저 볼 정보와 복원 내부값을 나눠 보여줘요."
      headerStyle={{ background: "#EFFFF9", padding: "12px 14px" }}
      iconStyle={{ background: "#00A88F", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 10 }}
    >
      {row ? (
        <>
          <strong>{row.displayName}</strong>
          <span style={{ fontSize: 12, color: "#555" }}>{formatSavedAt(row.createdAt)} · {row.triggerLabel}</span>
          <div style={{ display: "grid", gap: 6, fontSize: 12 }}>
            <div>파일: {row.fileCount}개 · 변경 {row.changedFileCount}개 · 재사용 {row.reusedFileCount}개</div>
            <div>크기: 원본 {formatBytes(row.originalSizeBytes || row.totalSizeBytes)} / 실제 저장 {formatBytes(row.storedSizeBytes)}</div>
            {row.gitCommitSha ? <div>Git: {row.gitCommitSha.slice(0, 12)} {row.gitCommitMessage ? `· ${row.gitCommitMessage}` : ""}</div> : null}
          </div>
          <details style={{ fontSize: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>복원 내부값</summary>
            <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
              <code>저장본 ID: {row.checkpointId}</code>
              <code>parent ID: {row.parentCheckpointId ?? "없음"}</code>
              <code>engine version: {row.engineVersion ?? "legacy"}</code>
              <code>schema version: {report.schemaVersion ?? "알 수 없음"}</code>
              <code>DB path: {report.dbPath}</code>
            </div>
          </details>
        </>
      ) : (
        <div style={{ fontSize: 12, color: "#666" }}>왼쪽 목록에서 DB row를 선택하면 상세 정보가 보여요.</div>
      )}
    </BackupCard>
  );
}
