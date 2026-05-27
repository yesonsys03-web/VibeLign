// === ANCHOR: BACKUP_START ===
import { callEngineDirect, runVib } from "./core";
import type {
  BackupCleanupResult,
  BackupDbMaintenanceResult,
  BackupDbViewerCheckpointRow,
  BackupDbViewerInspectResult,
  BackupEntry,
  BackupFileEntry,
  BackupGraphNode,
  BackupGraphSummaryResult,
  BackupListResult,
  BackupSourceKind,
  CheckpointCreateResult,
} from "./types";

// === ANCHOR: BACKUP_GETAUTOBACKUPONCOMMIT_START ===
export async function getAutoBackupOnCommit(cwd: string): Promise<boolean> {
  const parsed = await callEngineDirect<{ enabled?: boolean }>({
    command: "auto_backup_status",
    root: cwd,
  });
  return Boolean(parsed.enabled);
}
// === ANCHOR: BACKUP_GETAUTOBACKUPONCOMMIT_END ===

// === ANCHOR: BACKUP_SETAUTOBACKUPONCOMMIT_START ===
export async function setAutoBackupOnCommit(cwd: string, enabled: boolean): Promise<boolean> {
  const parsed = await callEngineDirect<{ enabled?: boolean }>({
    command: "auto_backup_set",
    root: cwd,
    enabled,
  });
  return Boolean(parsed.enabled);
}
// === ANCHOR: BACKUP_SETAUTOBACKUPONCOMMIT_END ===

// === ANCHOR: BACKUP_CHECKPOINTCREATE_START ===
export async function checkpointCreate(cwd: string, message: string): Promise<CheckpointCreateResult> {
  const res = await runVib(["checkpoint", message, "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const data = JSON.parse(res.stdout) as CheckpointCreateResult;
  if (data.ok === false && data.error !== "no_changes") throw new Error(data.error ?? "checkpoint 실패");
  if (data.ok !== false) clearBackupCaches(cwd);
  return data;
}
// === ANCHOR: BACKUP_CHECKPOINTCREATE_END ===

// === ANCHOR: BACKUP_BACKUPCREATE_START ===
export async function backupCreate(cwd: string, note: string): Promise<CheckpointCreateResult> {
  return checkpointCreate(cwd, note);
}
// === ANCHOR: BACKUP_BACKUPCREATE_END ===

// === ANCHOR: BACKUP_CHECKPOINTLIST_START ===
export async function checkpointList(cwd: string): Promise<unknown> {
  return callEngineDirect<unknown>({ command: "checkpoint_list", root: cwd });
}
// === ANCHOR: BACKUP_CHECKPOINTLIST_END ===

/**
 * Phase 3 PoC consumer #2 — `vib undo --checkpoint-id … --force --json`
 * 의 CLI 프롬프트는 engine 에 없으므로 direct 호출이 곧 force 의미와 동치.
 * 응답 shape `{status, result: "restored", checkpoint_id}` 는 호출자가
 * `Promise<unknown>` 으로만 소비하므로 wrapper 변환 불필요.
 */
// === ANCHOR: BACKUP_UNDOCHECKPOINT_START ===
export async function undoCheckpoint(cwd: string, checkpointId: string): Promise<unknown> {
  return callEngineDirect<unknown>({
    command: "checkpoint_restore",
    root: cwd,
    checkpoint_id: checkpointId,
  });
}
// === ANCHOR: BACKUP_UNDOCHECKPOINT_END ===

interface RawCheckpointEntry {
  checkpoint_id?: string;
  message?: string;
  created_at?: string;
  file_count?: number | null;
  total_size_bytes?: number | null;
  files?: RawCheckpointFileEntry[] | null;
  trigger?: string | null;
  git_commit_message?: string | null;
}

interface RawCheckpointFileEntry {
  relative_path?: string | null;
  path?: string | null;
  size?: number | null;
  size_bytes?: number | null;
}

interface RawBackupDbViewerCheckpointRow {
  checkpoint_id?: string | null;
  display_name?: string | null;
  created_at?: string | null;
  pinned?: boolean | number | null;
  trigger?: string | null;
  trigger_label?: string | null;
  git_commit_sha?: string | null;
  git_commit_message?: string | null;
  file_count?: number | null;
  total_size_bytes?: number | null;
  original_size_bytes?: number | null;
  stored_size_bytes?: number | null;
  reused_file_count?: number | null;
  changed_file_count?: number | null;
  engine_version?: string | null;
  parent_checkpoint_id?: string | null;
  internal_badges?: string[] | null;
}

interface RawBackupDbViewerRetentionPolicy {
  keep_latest?: number | null;
  keep_daily_days?: number | null;
  keep_weekly_weeks?: number | null;
  max_total_size_bytes?: number | null;
  max_age_days?: number | null;
  min_keep?: number | null;
}

interface RawBackupDbViewerCompressionSummary {
  compression?: string | null;
  object_count?: number | null;
}

interface RawBackupDbViewerObjectStore {
  exists?: boolean;
  path?: string | null;
  compression_summary?: RawBackupDbViewerCompressionSummary[] | null;
  stored_size_bytes?: number | null;
  original_size_bytes?: number | null;
}

interface RawBackupDbViewerDbFileStats {
  database_bytes?: number | null;
  wal_bytes?: number | null;
  shm_bytes?: number | null;
  total_bytes?: number | null;
}

interface RawBackupDbViewerInspectResult {
  ok?: boolean;
  error?: string;
  db_exists?: boolean;
  db_path?: string | null;
  db_file?: RawBackupDbViewerDbFileStats | null;
  schema_version?: string | null;
  checkpoint_count?: number | null;
  rust_v2_count?: number | null;
  legacy_count?: number | null;
  cas_object_count?: number | null;
  cas_ref_count?: number | null;
  total_original_size_bytes?: number | null;
  total_stored_size_bytes?: number | null;
  auto_backup_on_commit?: boolean;
  retention_policy?: RawBackupDbViewerRetentionPolicy | null;
  object_store?: RawBackupDbViewerObjectStore | null;
  checkpoints?: RawBackupDbViewerCheckpointRow[] | null;
  warnings?: string[] | null;
}

interface RawBackupDbMaintenanceResult {
  ok?: boolean;
  error?: string;
  db_exists?: boolean;
  mode?: string | null;
  planned_action?: string | null;
  vacuum_recommended?: boolean | null;
  checkpoint_recommended?: boolean | null;
  reclaimed_bytes?: number | null;
  blockers?: string[] | null;
  warnings?: string[] | null;
}

interface RawBackupCleanupResult {
  ok?: boolean;
  error?: string;
  retention?: {
    count?: number | null;
    planned_count?: number | null;
    planned_bytes?: number | null;
    reclaimed_bytes?: number | null;
    partial_failure?: boolean | null;
  } | null;
  maintenance?: RawBackupDbMaintenanceResult | null;
}

interface RawBackupGraphNode {
  id?: string | null;
  name?: string | null;
  path?: string | null;
  size_bytes?: number | null;
  children?: RawBackupGraphNode[] | null;
}

interface RawBackupGraphSummaryResult {
  ok?: boolean;
  error?: string;
  db_exists?: boolean;
  file_row_count?: number | null;
  root?: RawBackupGraphNode | null;
  warnings?: string[] | null;
}

// === ANCHOR: BACKUP_READNUMBER_START ===
function readNumber(value: number | null | undefined): number {
  return typeof value === "number" ? value : 0;
}
// === ANCHOR: BACKUP_READNUMBER_END ===

// === ANCHOR: BACKUP_NORMALIZEDBFILE_START ===
function normalizeDbFile(raw?: RawBackupDbViewerDbFileStats | null): BackupDbViewerInspectResult["dbFile"] {
  return {
    databaseBytes: readNumber(raw?.database_bytes),
    walBytes: readNumber(raw?.wal_bytes),
    shmBytes: readNumber(raw?.shm_bytes),
    totalBytes: readNumber(raw?.total_bytes),
  };
}
// === ANCHOR: BACKUP_NORMALIZEDBFILE_END ===

// === ANCHOR: BACKUP_NORMALIZERETENTIONPOLICY_START ===
function normalizeRetentionPolicy(raw?: RawBackupDbViewerRetentionPolicy | null): BackupDbViewerInspectResult["retentionPolicy"] {
  if (!raw) return null;
  return {
    keepLatest: readNumber(raw.keep_latest),
    keepDailyDays: readNumber(raw.keep_daily_days),
    keepWeeklyWeeks: readNumber(raw.keep_weekly_weeks),
    maxTotalSizeBytes: readNumber(raw.max_total_size_bytes),
    maxAgeDays: readNumber(raw.max_age_days),
    minKeep: readNumber(raw.min_keep),
  };
}
// === ANCHOR: BACKUP_NORMALIZERETENTIONPOLICY_END ===

// === ANCHOR: BACKUP_NORMALIZEOBJECTSTORE_START ===
function normalizeObjectStore(raw?: RawBackupDbViewerObjectStore | null): BackupDbViewerInspectResult["objectStore"] {
  const compressionItems = Array.isArray(raw?.compression_summary) ? raw.compression_summary : [];
  return {
    exists: raw?.exists === true,
    path: typeof raw?.path === "string" ? raw.path : "",
    compressionSummary: compressionItems.map((item) => ({
      compression: item.compression ?? "unknown",
      objectCount: readNumber(item.object_count),
    })),
    storedSizeBytes: readNumber(raw?.stored_size_bytes),
    originalSizeBytes: readNumber(raw?.original_size_bytes),
  };
}
// === ANCHOR: BACKUP_NORMALIZEOBJECTSTORE_END ===

// === ANCHOR: BACKUP_NORMALIZEBACKUPDBVIEWERROW_START ===
function normalizeBackupDbViewerRow(raw: RawBackupDbViewerCheckpointRow): BackupDbViewerCheckpointRow {
  return {
    checkpointId: raw.checkpoint_id ?? "",
    displayName: raw.display_name ?? "메모 없는 저장본",
    createdAt: raw.created_at ?? "",
    pinned: raw.pinned === true || raw.pinned === 1,
    trigger: raw.trigger ?? null,
    triggerLabel: raw.trigger_label ?? "수동 백업",
    gitCommitSha: raw.git_commit_sha ?? null,
    gitCommitMessage: raw.git_commit_message ?? null,
    fileCount: readNumber(raw.file_count),
    totalSizeBytes: readNumber(raw.total_size_bytes),
    originalSizeBytes: readNumber(raw.original_size_bytes),
    storedSizeBytes: readNumber(raw.stored_size_bytes),
    reusedFileCount: readNumber(raw.reused_file_count),
    changedFileCount: readNumber(raw.changed_file_count),
    engineVersion: raw.engine_version ?? null,
    parentCheckpointId: raw.parent_checkpoint_id ?? null,
    internalBadges: Array.isArray(raw.internal_badges) ? raw.internal_badges : [],
  };
}
// === ANCHOR: BACKUP_NORMALIZEBACKUPDBVIEWERROW_END ===

// === ANCHOR: BACKUP_PARSEBACKUPDBVIEWERINSPECTRESULT_START ===
function parseBackupDbViewerInspectResult(raw: RawBackupDbViewerInspectResult): BackupDbViewerInspectResult {
  if (raw.ok === false) throw new Error(raw.error ?? "Backup DB Viewer 실패");
  const checkpoints = Array.isArray(raw.checkpoints) ? raw.checkpoints : [];
  const warnings = Array.isArray(raw.warnings) ? raw.warnings.filter((item): item is string => typeof item === "string") : [];
  return {
    dbExists: raw.db_exists === true,
    dbPath: typeof raw.db_path === "string" ? raw.db_path : "",
    dbFile: normalizeDbFile(raw.db_file),
    schemaVersion: typeof raw.schema_version === "string" ? raw.schema_version : null,
    checkpointCount: readNumber(raw.checkpoint_count),
    rustV2Count: readNumber(raw.rust_v2_count),
    legacyCount: readNumber(raw.legacy_count),
    casObjectCount: readNumber(raw.cas_object_count),
    casRefCount: readNumber(raw.cas_ref_count),
    totalOriginalSizeBytes: readNumber(raw.total_original_size_bytes),
    totalStoredSizeBytes: readNumber(raw.total_stored_size_bytes),
    autoBackupOnCommit: raw.auto_backup_on_commit === true,
    retentionPolicy: normalizeRetentionPolicy(raw.retention_policy),
    objectStore: normalizeObjectStore(raw.object_store),
    checkpoints: checkpoints.map(normalizeBackupDbViewerRow),
    warnings,
  };
}
// === ANCHOR: BACKUP_PARSEBACKUPDBVIEWERINSPECTRESULT_END ===

// === ANCHOR: BACKUP_PARSEBACKUPDBMAINTENANCERESULT_START ===
function parseBackupDbMaintenanceResult(raw: RawBackupDbMaintenanceResult): BackupDbMaintenanceResult {
  if (raw.ok === false) throw new Error(raw.error ?? "Backup DB maintenance 실패");
  return {
    dbExists: raw.db_exists === true,
    mode: raw.mode ?? "dry_run",
    plannedAction: raw.planned_action ?? "noop",
    vacuumRecommended: raw.vacuum_recommended === true,
    checkpointRecommended: raw.checkpoint_recommended === true,
    reclaimedBytes: readNumber(raw.reclaimed_bytes),
    blockers: Array.isArray(raw.blockers) ? raw.blockers.filter((item): item is string => typeof item === "string") : [],
    warnings: Array.isArray(raw.warnings) ? raw.warnings.filter((item): item is string => typeof item === "string") : [],
  };
}
// === ANCHOR: BACKUP_PARSEBACKUPDBMAINTENANCERESULT_END ===

// === ANCHOR: BACKUP_PARSEBACKUPCLEANUPRESULT_START ===
function parseBackupCleanupResult(raw: RawBackupCleanupResult): BackupCleanupResult {
  if (raw.ok === false) throw new Error(raw.error ?? "Backup cleanup 실패");
  const retention = raw.retention ?? {};
  return {
    retention: {
      count: readNumber(retention.count),
      plannedCount: readNumber(retention.planned_count),
      plannedBytes: readNumber(retention.planned_bytes),
      reclaimedBytes: readNumber(retention.reclaimed_bytes),
      partialFailure: retention.partial_failure === true,
    },
    maintenance: parseBackupDbMaintenanceResult(raw.maintenance ?? {}),
  };
}
// === ANCHOR: BACKUP_PARSEBACKUPCLEANUPRESULT_END ===

// === ANCHOR: BACKUP_NORMALIZEBACKUPGRAPHNODE_START ===
function normalizeBackupGraphNode(raw?: RawBackupGraphNode | null): BackupGraphNode {
  const rawChildren = Array.isArray(raw?.children) ? raw.children : [];
  const path = typeof raw?.path === "string" ? raw.path.replaceAll("\\", "/") : "";
  return {
    id: raw?.id || path || "root",
    name: raw?.name || (path ? path.split("/").filter(Boolean).at(-1) ?? path : "백업"),
    path,
    sizeBytes: readNumber(raw?.size_bytes),
    children: rawChildren.map(normalizeBackupGraphNode),
  };
}
// === ANCHOR: BACKUP_NORMALIZEBACKUPGRAPHNODE_END ===

// === ANCHOR: BACKUP_PARSEBACKUPGRAPHSUMMARYRESULT_START ===
function parseBackupGraphSummaryResult(raw: RawBackupGraphSummaryResult): BackupGraphSummaryResult {
  if (raw.ok === false) throw new Error(raw.error ?? "Backup graph summary 실패");
  return {
    dbExists: raw.db_exists === true,
    fileRowCount: readNumber(raw.file_row_count),
    root: normalizeBackupGraphNode(raw.root),
    warnings: Array.isArray(raw.warnings) ? raw.warnings.filter((item): item is string => typeof item === "string") : [],
  };
}
// === ANCHOR: BACKUP_PARSEBACKUPGRAPHSUMMARYRESULT_END ===

// === ANCHOR: BACKUP_BACKUPSOURCEKIND_START ===
function backupSourceKind(trigger?: string | null): BackupSourceKind {
  if (trigger === "post_commit") return "auto";
  if (trigger === "safe_restore") return "safe";
  if (!trigger) return "manual";
  return "unknown";
}
// === ANCHOR: BACKUP_BACKUPSOURCEKIND_END ===

// === ANCHOR: BACKUP_CLEANRAWBACKUPNOTE_START ===
function cleanRawBackupNote(raw: RawCheckpointEntry): string {
  // === ANCHOR: BACKUP_NOTE_START ===
  const note = (raw.git_commit_message || raw.message || "")
    .replace(/^vibelign:\s*checkpoint\s*-?\s*/i, "")
    .replace(/\s*\(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\)\s*$/, "")
  // === ANCHOR: BACKUP_NOTE_END ===
    .trim();
  if (raw.trigger === "post_commit") {
    return note ? `코드 저장 뒤 자동 보관 - ${note}` : "코드 저장 뒤 자동 보관";
  }
// === ANCHOR: BACKUP_CLEANRAWBACKUPNOTE_END ===
  return note || "메모 없는 저장본";
}

// === ANCHOR: BACKUP_NORMALIZEBACKUPENTRY_START ===
function normalizeBackupEntry(raw: RawCheckpointEntry): BackupEntry {
  const files = Array.isArray(raw.files) ? raw.files.map(normalizeBackupFileEntry).filter((entry): entry is BackupFileEntry => entry !== null) : [];
  return {
    id: raw.checkpoint_id ?? "",
    note: cleanRawBackupNote(raw),
    createdAt: raw.created_at,
    fileCount: typeof raw.file_count === "number" ? raw.file_count : undefined,
    totalSizeBytes: typeof raw.total_size_bytes === "number" ? raw.total_size_bytes : 0,
    files,
    sourceKind: backupSourceKind(raw.trigger),
    commitNote: raw.git_commit_message ?? undefined,
  };
}
// === ANCHOR: BACKUP_NORMALIZEBACKUPENTRY_END ===

// === ANCHOR: BACKUP_NORMALIZEBACKUPENTRYFROMDBROW_START ===
function normalizeBackupEntryFromDbRow(row: BackupDbViewerCheckpointRow): BackupEntry {
  return {
    id: row.checkpointId,
    note: row.displayName || "메모 없는 저장본",
    createdAt: row.createdAt,
    fileCount: row.fileCount,
    totalSizeBytes: row.originalSizeBytes || row.totalSizeBytes,
    files: [],
    sourceKind: backupSourceKind(row.trigger),
    commitNote: row.gitCommitMessage ?? undefined,
  };
}
// === ANCHOR: BACKUP_NORMALIZEBACKUPENTRYFROMDBROW_END ===

// === ANCHOR: BACKUP_NORMALIZEBACKUPFILEENTRY_START ===
function normalizeBackupFileEntry(raw: RawCheckpointFileEntry): BackupFileEntry | null {
  const path = raw.relative_path ?? raw.path;
  if (!path) return null;
  const size = raw.size ?? raw.size_bytes ?? 0;
  return {
    path: path.replaceAll("\\", "/"),
    sizeBytes: typeof size === "number" ? size : 0,
  };
}
// === ANCHOR: BACKUP_NORMALIZEBACKUPFILEENTRY_END ===

const backupListCache = new Map<string, BackupListResult>();
const backupDbViewerInspectCache = new Map<string, BackupDbViewerInspectResult>();
const backupGraphSummaryCache = new Map<string, BackupGraphSummaryResult>();

// === ANCHOR: BACKUP_CLEARBACKUPCACHES_START ===
function clearBackupCaches(cwd: string): void {
  backupListCache.delete(cwd);
  backupDbViewerInspectCache.delete(cwd);
  backupGraphSummaryCache.delete(cwd);
}
// === ANCHOR: BACKUP_CLEARBACKUPCACHES_END ===

// === ANCHOR: BACKUP_GETCACHEDBACKUPLIST_START ===
export function getCachedBackupList(cwd: string): BackupListResult | undefined {
  return backupListCache.get(cwd);
}
// === ANCHOR: BACKUP_GETCACHEDBACKUPLIST_END ===

// === ANCHOR: BACKUP_GETCACHEDBACKUPDBVIEWERINSPECT_START ===
export function getCachedBackupDbViewerInspect(cwd: string): BackupDbViewerInspectResult | undefined {
  return backupDbViewerInspectCache.get(cwd);
}
// === ANCHOR: BACKUP_GETCACHEDBACKUPDBVIEWERINSPECT_END ===

// === ANCHOR: BACKUP_GETCACHEDBACKUPGRAPHSUMMARY_START ===
export function getCachedBackupGraphSummary(cwd: string): BackupGraphSummaryResult | undefined {
  return backupGraphSummaryCache.get(cwd);
}
// === ANCHOR: BACKUP_GETCACHEDBACKUPGRAPHSUMMARY_END ===

// === ANCHOR: BACKUP_BACKUPLIST_START ===
export async function backupList(cwd: string, options?: { force?: boolean }): Promise<BackupListResult> {
  try {
    const report = await backupDbViewerInspect(cwd, { force: options?.force });
    if (report.dbExists) {
      const result: BackupListResult = {
        backups: report.checkpoints
          .map(normalizeBackupEntryFromDbRow)
          .filter((entry) => entry.id && entry.sourceKind !== "safe"),
        warning: report.warnings[0] ?? null,
      };
      backupListCache.set(cwd, result);
      return result;
    }
  } catch {
    // Fall back to the older checkpoint list path so legacy projects still load.
  }
  const data = await checkpointList(cwd) as {
    checkpoints?: RawCheckpointEntry[];
    warning?: string | null;
  };
  const result: BackupListResult = {
    backups: (data.checkpoints ?? [])
      .map(normalizeBackupEntry)
      .filter((entry) => entry.id && entry.sourceKind !== "safe"),
    warning: data.warning ?? null,
  };
  backupListCache.set(cwd, result);
  return result;
}
// === ANCHOR: BACKUP_BACKUPLIST_END ===

/**
 * Phase 3 PoC consumer #3 — read-only `backup_db_viewer_inspect`.
 * Python wrapper 가 `{ok:true, ...report}` 로 감싸지만 TS parser 는 `raw.ok === false`
 * (explicit false) 만 실패로 보므로, engine raw `{status:"ok", ...}` 가 ok 필드 없이도
 * 그대로 통과한다. cache 정책은 변경 없음.
 */
// === ANCHOR: BACKUP_BACKUPDBVIEWERINSPECT_START ===
export async function backupDbViewerInspect(cwd: string, options?: { force?: boolean }): Promise<BackupDbViewerInspectResult> {
  if (!options?.force) {
    const cached = backupDbViewerInspectCache.get(cwd);
    if (cached) return cached;
  }
  const parsed = await callEngineDirect<RawBackupDbViewerInspectResult>({
    command: "backup_db_viewer_inspect",
    root: cwd,
  });
  const result = parseBackupDbViewerInspectResult(parsed);
  backupDbViewerInspectCache.set(cwd, result);
  return result;
}
// === ANCHOR: BACKUP_BACKUPDBVIEWERINSPECT_END ===

/**
 * Phase 3 PoC consumer #4 — read-only `backup_graph_summary`. 동일 shape parity 패턴.
 */
// === ANCHOR: BACKUP_BACKUPGRAPHSUMMARY_START ===
export async function backupGraphSummary(cwd: string, options?: { force?: boolean }): Promise<BackupGraphSummaryResult> {
  if (!options?.force) {
    const cached = backupGraphSummaryCache.get(cwd);
    if (cached) return cached;
  }
  const parsed = await callEngineDirect<RawBackupGraphSummaryResult>({
    command: "backup_graph_summary",
    root: cwd,
  });
  const result = parseBackupGraphSummaryResult(parsed);
  backupGraphSummaryCache.set(cwd, result);
  return result;
}
// === ANCHOR: BACKUP_BACKUPGRAPHSUMMARY_END ===

/**
 * Phase 3 PoC consumer #5 — `backup_db_maintenance` (write path with apply param).
 * Python wrapper 가 `{ok:true, ...report}` 로만 감쌈 — TS parser 가 `raw.ok === false`
 * 만 실패로 보므로 engine raw `{status:"ok", ...}` 그대로 통과.
 */
// === ANCHOR: BACKUP_BACKUPDBMAINTENANCE_START ===
export async function backupDbMaintenance(cwd: string, apply = false): Promise<BackupDbMaintenanceResult> {
  const parsed = await callEngineDirect<RawBackupDbMaintenanceResult>({
    command: "backup_db_maintenance",
    root: cwd,
    apply,
  });
  const result = parseBackupDbMaintenanceResult(parsed);
  if (apply) clearBackupCaches(cwd);
  return result;
}
// === ANCHOR: BACKUP_BACKUPDBMAINTENANCE_END ===

/**
 * Phase 3 PoC consumer #6 — `backup_cleanup` 는 Python 측에서
 * `apply_retention` + `maintain_backup_db(apply=True)` 두 엔진 호출을 묶어서
 * `{ok, retention, maintenance}` 로 합치는 컴포지트. direct path 에서는 두 호출을
 * 순차 실행 후 같은 shape 로 wrap. 필드 이름 매핑(`pruned_count → count` 등)은
 * Python `parse_retention` 이 하던 일을 TS 에서 동일하게 재현.
 */
// === ANCHOR: BACKUP_BACKUPCLEANUP_START ===
export async function backupCleanup(cwd: string): Promise<BackupCleanupResult> {
  interface RetentionRaw {
    pruned_count?: number;
    planned_count?: number;
    planned_bytes?: number;
    reclaimed_bytes?: number;
    partial_failure?: boolean;
  }
  const retentionRaw = await callEngineDirect<RetentionRaw>({
    command: "retention_apply",
    root: cwd,
  });
  const maintenanceRaw = await callEngineDirect<RawBackupDbMaintenanceResult>({
    command: "backup_db_maintenance",
    root: cwd,
    apply: true,
  });
  const wrapped: RawBackupCleanupResult = {
    retention: {
      count: retentionRaw.pruned_count,
      planned_count: retentionRaw.planned_count,
      planned_bytes: retentionRaw.planned_bytes,
      reclaimed_bytes: retentionRaw.reclaimed_bytes,
      partial_failure: retentionRaw.partial_failure,
    },
    maintenance: maintenanceRaw,
  };
  const result = parseBackupCleanupResult(wrapped);
  clearBackupCaches(cwd);
  return result;
}
// === ANCHOR: BACKUP_BACKUPCLEANUP_END ===

// === ANCHOR: BACKUP_BACKUPRESTORE_START ===
export async function backupRestore(cwd: string, backupId: string): Promise<unknown> {
  const result = await undoCheckpoint(cwd, backupId);
  clearBackupCaches(cwd);
  return result;
}
// === ANCHOR: BACKUP_BACKUPRESTORE_END ===
// === ANCHOR: BACKUP_END ===
