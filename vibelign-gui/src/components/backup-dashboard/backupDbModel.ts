import type { BackupDbViewerCheckpointRow, BackupDbViewerInspectResult } from "../../lib/vib";

export function filterBackupDbRows(rows: BackupDbViewerCheckpointRow[], query: string): BackupDbViewerCheckpointRow[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) => [
    row.displayName,
    row.checkpointId,
    row.triggerLabel,
    row.gitCommitSha ?? "",
    row.gitCommitMessage ?? "",
  ].some((value) => value.toLowerCase().includes(normalized)));
}

export function storageEfficiencyPercent(report: BackupDbViewerInspectResult): number {
  if (report.totalOriginalSizeBytes <= 0) return 0;
  const saved = report.totalOriginalSizeBytes - report.totalStoredSizeBytes;
  return Math.max(0, Math.round((saved / report.totalOriginalSizeBytes) * 100));
}

export function compressionSummaryLabel(report: BackupDbViewerInspectResult): string {
  if (report.objectStore.compressionSummary.length === 0) return "정보 없음";
  return report.objectStore.compressionSummary
    .map((item) => `${item.compression} ${item.objectCount}개`)
    .join(" · ");
}
