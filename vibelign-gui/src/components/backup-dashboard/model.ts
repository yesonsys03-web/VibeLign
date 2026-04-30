import type { BackupEntry } from "../../lib/vib";

export interface BackupDashboardStats {
  totalCount: number;
  autoCount: number;
  manualCount: number;
  totalFiles: number;
  storedBytes: number;
  lastSavedLabel: string;
}

export interface TimelinePoint {
  id: string;
  dateLabel: string;
  timeLabel: string;
  detailLabel: string;
  sourceKind: BackupEntry["sourceKind"];
  position: number;
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

export function buildTimelinePoints(entries: BackupEntry[]): TimelinePoint[] {
  const visible = entries
    .slice(0, 50)
    .map((entry, index) => ({ entry, index, time: parseBackupTime(entry.createdAt) }))
    .sort((left, right) => (left.time ?? left.index) - (right.time ?? right.index));
  return visible.map(({ entry, time }, index) => ({
    id: entry.id,
    dateLabel: formatDayLabel(entry.createdAt),
    timeLabel: formatTimeLabel(time, entry.createdAt),
    detailLabel: `${cleanBackupNote(entry)} · ${formatSavedAt(entry.createdAt)}`,
    sourceKind: entry.sourceKind,
    position: timelinePosition(index, visible.length),
  }));
}

function formatDayLabel(value?: string): string {
  if (!value) return "날짜 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10) || "날짜 없음";
  return date.toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" });
}

function parseBackupTime(value?: string): number | null {
  if (!value) return null;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
}

function formatTimeLabel(time: number | null, fallback?: string): string {
  if (time === null) return fallback?.slice(11, 16) || "시간 없음";
  return new Date(time).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function timelinePosition(index: number, total: number): number {
  if (total <= 1) return 8;
  return 4 + (index / (total - 1)) * 92;
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
