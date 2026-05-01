import type { BackupDbViewerInspectResult } from "../../lib/vib";
import { compressionSummaryLabel, storageEfficiencyPercent } from "./backupDbModel";
import { formatBytes } from "./model";

interface BackupDbSummaryCardsProps {
  report: BackupDbViewerInspectResult;
}

export default function BackupDbSummaryCards({ report }: BackupDbSummaryCardsProps) {
  const retention = report.retentionPolicy;
  const cards = [
    { label: "DB 상태", value: report.schemaVersion ? `schema ${report.schemaVersion}` : "schema 정보 없음", detail: report.dbPath || "DB 경로 없음" },
    { label: "DB 파일", value: formatBytes(report.dbFile.totalBytes), detail: `DB ${formatBytes(report.dbFile.databaseBytes)} · WAL ${formatBytes(report.dbFile.walBytes)} · SHM ${formatBytes(report.dbFile.shmBytes)}` },
    { label: "전체 백업", value: `${report.checkpointCount}개`, detail: `Rust v2 ${report.rustV2Count}개 · legacy ${report.legacyCount}개` },
    { label: "Object store", value: `${report.casObjectCount}개`, detail: `${report.casRefCount}개 참조` },
    { label: "저장 효율", value: `${storageEfficiencyPercent(report)}% 절약`, detail: `${formatBytes(report.totalOriginalSizeBytes)} → ${formatBytes(report.totalStoredSizeBytes)}` },
    { label: "자동 백업", value: report.autoBackupOnCommit ? "켜짐" : "꺼짐", detail: report.autoBackupOnCommit ? "코드 저장 뒤 자동 보관" : "수동 백업 중심" },
    { label: "정리 정책", value: retention ? `최신 ${retention.keepLatest}개` : "정책 없음", detail: retention ? `최소 ${retention.minKeep}개 · 최대 ${formatBytes(retention.maxTotalSizeBytes)}` : "retention_policy 없음" },
    { label: "압축 방식", value: compressionSummaryLabel(report), detail: report.objectStore.exists ? "object store 확인됨" : "object store 없음" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
      {cards.map((card) => (
        <div key={card.label} className="feature-card" style={{ cursor: "default", padding: 12 }}>
          <div style={{ fontSize: 11, color: "#555", fontWeight: 800 }}>{card.label}</div>
          <div style={{ fontSize: 20, fontWeight: 900, marginTop: 4 }}>{card.value}</div>
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>{card.detail}</div>
        </div>
      ))}
    </div>
  );
}
