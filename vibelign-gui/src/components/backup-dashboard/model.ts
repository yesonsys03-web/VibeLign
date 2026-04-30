import type { BackupEntry } from "../../lib/vib";

export interface BackupDashboardStats {
  totalCount: number;
  autoCount: number;
  manualCount: number;
  totalFiles: number;
  storedBytes: number;
  lastSavedLabel: string;
}

export interface DayBucket {
  label: string;
  count: number;
}

export interface RestoreSuggestion {
  id: string;
  title: string;
  detail: string;
}

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatSavedAt(value?: string): string {
  if (!value) return "시간 정보 없음";
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 16);
    return date.toLocaleString("ko-KR", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value.slice(0, 16);
  }
}

export function cleanBackupNote(entry: BackupEntry): string {
  return entry.note || "메모 없는 저장본";
}

export function buildStats(entries: BackupEntry[]): BackupDashboardStats {
  const totalFiles = entries.reduce((sum, item) => sum + (item.fileCount ?? 0), 0);
  const storedBytes = entries.reduce((sum, item) => sum + item.totalSizeBytes, 0);
  return {
    totalCount: entries.length,
    autoCount: entries.filter((item) => item.sourceKind === "auto").length,
    manualCount: entries.filter((item) => item.sourceKind === "manual").length,
    totalFiles,
    storedBytes,
    lastSavedLabel: entries[0] ? formatSavedAt(entries[0].createdAt) : "아직 없음",
  };
}

export function buildDayBuckets(entries: BackupEntry[]): DayBucket[] {
  const counts = new Map<string, number>();
  for (const entry of entries) {
    const label = formatDayLabel(entry.createdAt);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return Array.from(counts.entries()).slice(0, 10).map(([label, count]) => ({ label, count }));
}

function formatDayLabel(value?: string): string {
  if (!value) return "날짜 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10) || "날짜 없음";
  return date.toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" });
}

export function buildRestoreSuggestions(entries: BackupEntry[]): RestoreSuggestion[] {
  return entries.slice(0, 3).map((entry, index) => ({
    id: entry.id,
    title: index === 0 ? "가장 최근 저장본" : cleanBackupNote(entry),
    detail: `${formatSavedAt(entry.createdAt)} · ${entry.fileCount ?? 0}개 파일`,
  }));
}

export function filterBackups(entries: BackupEntry[], query: string): BackupEntry[] {
  const needle = query.trim().toLocaleLowerCase("ko-KR");
  if (!needle) return entries;
  return entries.filter((entry) => {
    const haystack = `${cleanBackupNote(entry)} ${formatSavedAt(entry.createdAt)} ${entry.id}`.toLocaleLowerCase("ko-KR");
    return haystack.includes(needle);
  });
}
