// === ANCHOR: MODEL_START ===
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

// === ANCHOR: MODEL_FORMATBYTES_START ===
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
// === ANCHOR: MODEL_FORMATBYTES_END ===

// === ANCHOR: MODEL_FORMATSAVEDAT_START ===
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
// === ANCHOR: MODEL_FORMATSAVEDAT_END ===

// === ANCHOR: MODEL_CLEANBACKUPNOTE_START ===
const BACKUP_NOTE_MAX_CHARS = 80;

/**
 * 백업 카드 / 미리보기 패널에 표시할 한 줄 요약을 만든다.
 * 원본 note 는 git commit body 전체일 수 있어 (수십~수백 줄), 그대로 노출하면
 * 가독성이 망가진다. 첫 줄만 사용하고 80자 이상이면 말줄임 처리.
 *
 * 전체 본문은 상세 화면에서 별도로 보여주기로 한다 (entry.note 그대로 사용).
 */
export function cleanBackupNote(entry: BackupEntry): string {
  if (!entry.note) return "메모 없는 저장본";
  const firstLine = entry.note.split(/\r?\n/)[0]?.trim() ?? "";
  if (!firstLine) return "메모 없는 저장본";
  if (firstLine.length <= BACKUP_NOTE_MAX_CHARS) return firstLine;
  return firstLine.slice(0, BACKUP_NOTE_MAX_CHARS - 1).trimEnd() + "…";
}
// === ANCHOR: MODEL_CLEANBACKUPNOTE_END ===

// === ANCHOR: MODEL_FORMATRELATIVETIME_START ===
export function formatRelativeTime(value?: string): string {
  if (!value) return "시간 정보 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatSavedAt(value);
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return formatSavedAt(value);
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}일 전`;
  return formatSavedAt(value);
}
// === ANCHOR: MODEL_FORMATRELATIVETIME_END ===

// === ANCHOR: MODEL_BUILDSTATS_START ===
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
// === ANCHOR: MODEL_BUILDSTATS_END ===

// === ANCHOR: MODEL_BUILDTIMELINEPOINTS_START ===
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
// === ANCHOR: MODEL_BUILDTIMELINEPOINTS_END ===

// === ANCHOR: MODEL_FORMATDAYLABEL_START ===
function formatDayLabel(value?: string): string {
  if (!value) return "날짜 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10) || "날짜 없음";
  return date.toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" });
}
// === ANCHOR: MODEL_FORMATDAYLABEL_END ===

// === ANCHOR: MODEL_PARSEBACKUPTIME_START ===
function parseBackupTime(value?: string): number | null {
  if (!value) return null;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
}
// === ANCHOR: MODEL_PARSEBACKUPTIME_END ===

// === ANCHOR: MODEL_FORMATTIMELABEL_START ===
function formatTimeLabel(time: number | null, fallback?: string): string {
  if (time === null) return fallback?.slice(11, 16) || "시간 없음";
  return new Date(time).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}
// === ANCHOR: MODEL_FORMATTIMELABEL_END ===

// === ANCHOR: MODEL_TIMELINEPOSITION_START ===
function timelinePosition(index: number, total: number): number {
  if (total <= 1) return 8;
  return 4 + (index / (total - 1)) * 92;
}
// === ANCHOR: MODEL_TIMELINEPOSITION_END ===

// === ANCHOR: MODEL_BUILDRESTORESUGGESTIONS_START ===
export function buildRestoreSuggestions(entries: BackupEntry[]): RestoreSuggestion[] {
  return entries.slice(0, 3).map((entry, index) => ({
    id: entry.id,
    title: index === 0 ? "가장 최근 저장본" : cleanBackupNote(entry),
    detail: `${formatSavedAt(entry.createdAt)} · ${entry.fileCount ?? 0}개 파일`,
  }));
}
// === ANCHOR: MODEL_BUILDRESTORESUGGESTIONS_END ===

// === ANCHOR: MODEL_FILTERBACKUPS_START ===
export function filterBackups(entries: BackupEntry[], query: string): BackupEntry[] {
  const needle = query.trim().toLocaleLowerCase("ko-KR");
  if (!needle) return entries;
  return entries.filter((entry) => {
    const haystack = `${cleanBackupNote(entry)} ${formatSavedAt(entry.createdAt)} ${entry.id}`.toLocaleLowerCase("ko-KR");
    return haystack.includes(needle);
  });
}
// === ANCHOR: MODEL_FILTERBACKUPS_END ===
// === ANCHOR: MODEL_END ===
