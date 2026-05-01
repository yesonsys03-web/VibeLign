// === ANCHOR: VIB_BRIDGE_START ===
/**
 * Tauri IPC 브리지 — Rust의 run_vib / get_vib_path command 호출.
 * 모든 vib CLI 접근은 이 모듈을 통한다.
 */
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { open as dialogOpen } from "@tauri-apps/plugin-dialog";

export async function pickFile(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ multiple: false, defaultPath: defaultPath ?? undefined });
  return typeof result === "string" ? result : null;
}
export async function openFolder(path: string): Promise<void> {
  return invoke<void>("open_folder", { path });
}

export interface ReadFileResult {
  path: string;
  content: string;
  source_hash: string;
}

export interface DocsIndexEntry {
  category: "Manual" | "Context" | "Wiki" | "Spec" | "Plan" | "Custom" | "Root" | "Docs" | "Readme" | string;
  path: string;
  title: string;
  modified_at_ms: number;
  source_root?: string | null;
}

export interface DocSourcesResponse {
  ok: boolean;
  sources: string[];
  entries: DocsIndexEntry[];
  warnings: string[];
}

export interface DocsVisualContract {
  schema_version: number;
  generator_version: string;
}

export interface DocsVisualSection {
  id: string;
  title: string;
  level: number;
  summary: string;
}

export interface DocsVisualHeuristicFields {
  tldr_one_liner: string;
  key_rules: string[];
  success_criteria: string[];
  edge_cases: string[];
  components: string[];
  provenance: "heuristic";
  generator: string;
  generated_at: string;
}

export interface DocsVisualAIFields {
  tldr_one_liner: string;
  key_rules: string[];
  success_criteria: string[];
  edge_cases: string[];
  components: string[];
  provenance: "ai_draft";
  model: string;
  provider: string;
  generated_at: string;
  source_hash: string;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
}

export interface DocsVisualArtifact {
  source_path: string;
  source_hash: string;
  generated_at: string;
  generator_version: string;
  schema_version: number;
  title: string;
  summary: string;
  sections: DocsVisualSection[];
  glossary: Array<{ term: string; definition: string }>;
  action_items: Array<{ text: string; checked: boolean }>;
  diagram_blocks: Array<{
    id: string;
    kind: string;
    title?: string;
    source?: string;
    provenance?: "authored" | "heuristic" | "ai_draft";
    generator?: string;
    confidence?: "high" | "medium";
    warnings?: string[];
  }>;
  warnings?: string[];
  heuristic_fields?: DocsVisualHeuristicFields | null;
  ai_fields?: DocsVisualAIFields | null;
}

export interface DocsVisualReadResult {
  path: string;
  artifact: DocsVisualArtifact;
  contract: DocsVisualContract;
}

export async function readFile(root: string, path: string): Promise<ReadFileResult> {
  return invoke<ReadFileResult>("read_file", { root, path });
}

export async function listDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("list_docs_index", { root });
}

export async function rebuildDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("rebuild_docs_index", { root });
}

export async function readDocsVisual(root: string, path: string): Promise<DocsVisualReadResult | null> {
  return invoke<DocsVisualReadResult | null>("read_docs_visual", { root, path });
}

export async function listExtraDocSources(root: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("list_extra_doc_sources", { root });
}

export async function addExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("add_extra_doc_source", { root, path });
}

export async function removeExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("remove_extra_doc_source", { root, path });
}

export async function pickFolder(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ directory: true, multiple: false, defaultPath });
  return typeof result === "string" ? result : null;
}

export interface EnhanceDocResult {
  ok: boolean;
  path: string;
  ai_fields: DocsVisualAIFields;
}

export async function enhanceDocWithAi(
  root: string,
  path: string,
  models?: Record<string, string>,
): Promise<EnhanceDocResult> {
  const raw = await invoke<string>("enhance_doc_with_ai", {
    root,
    path,
    models: models ?? null,
  });
  return JSON.parse(raw) as EnhanceDocResult;
}

export interface VibResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
}

export type OnboardingState =
  | "idle"
  | "diagnosing"
  | "needs_git"
  | "ready_to_install"
  | "installing_native"
  | "installing_wsl"
  | "verifying_shells"
  | "needs_cmd_fallback"
  | "needs_wsl_fallback"
  | "needs_manual_step"
  | "login_required"
  | "probing_login"
  | "success"
  | "blocked";

export type NextAction =
  | "start_install"
  | "install_git"
  | "retry"
  | "retry_with_cmd"
  | "continue_with_wsl"
  | "open_manual_steps"
  | "add_to_path"
  | "start_login"
  | "launch_claude"
  | "share_logs"
  | "none";

export type InstallPathKind = "native-powershell" | "native-cmd" | "wsl" | "manual" | "unknown";

export interface OnboardingDiagnostics {
  gitInstalled?: boolean;
  wslAvailable?: boolean;
  claudeOnPath?: boolean;
  claudeVersionOk?: boolean;
  claudeDoctorOk?: boolean;
  loginStatusKnown?: boolean;
}

export interface OnboardingLastError {
  code:
    | "missing_git"
    | "exec_policy_blocked"
    | "path_not_configured"
    | "installer_false_success"
    | "installer_oom"
    | "placeholder_artifact"
    | "command_not_found"
    | "login_probe_failed"
    | "unsupported_environment"
    | "unknown";
  summary: string;
  detail?: string;
  suggestedAction?: NextAction;
}

export interface OnboardingSnapshot {
  state: OnboardingState;
  os: "macos" | "windows" | "linux";
  installPathKind: InstallPathKind;
  shellTargets: string[];
  nextAction: NextAction;
  headline: string;
  detail?: string;
  primaryButtonLabel?: string;
  logsAvailable: boolean;
  diagnostics: OnboardingDiagnostics;
  lastError?: OnboardingLastError;
}

export interface OnboardingProgressEvent {
  phase: "diagnose" | "install" | "verify" | "login";
  state: OnboardingState;
  stepId:
    | "check_os"
    | "check_git"
    | "run_powershell_installer"
    | "run_cmd_installer"
    | "run_wsl_installer"
    | "verify_version"
    | "verify_doctor"
    | "probe_login"
    | "complete";
  status: "started" | "stream" | "succeeded" | "failed";
  message: string;
  streamChunk?: string;
  shellTarget?: string;
  observedPath?: string;
  errorCode?: OnboardingLastError["code"];
}

/** vib 실행 파일 경로 반환. 없으면 null. */
export async function getVibPath(): Promise<string | null> {
  return invoke<string | null>("get_vib_path");
}

export async function getOnboardingSnapshot(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("get_onboarding_snapshot");
}

export async function startNativeInstall(pathKind: "native-powershell" | "native-cmd"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_native_install", { pathKind });
}

export async function startWslInstall(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_wsl_install");
}

export async function retryOnboardingVerification(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("retry_verification");
}

export async function startOnboardingLoginProbe(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_login_probe");
}

export async function addClaudeToUserPath(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("add_claude_to_user_path");
}

export async function uninstallClaudeCode(track?: "all" | "native" | "wsl"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("uninstall_claude_code", { track: track ?? "all" });
}

export async function getOnboardingLogs(): Promise<{ text: string }> {
  return invoke<{ text: string }>("get_onboarding_logs");
}

export async function listenOnboardingProgress(
  handler: (event: OnboardingProgressEvent) => void,
): Promise<UnlistenFn> {
  return listen<OnboardingProgressEvent>("onboarding_progress", (event) => handler(event.payload));
}

/** GUI에서 캡처한 문자열이 터미널에서 Rich 없이 볼 때와 같도록 plain 출력을 강제한다. */
const GUI_VIB_PLAIN_ENV: Record<string, string> = {
  VIBELIGN_ASK_PLAIN: "1",
  NO_COLOR: "1",
  // Windows에서는 기본 stdout 인코딩이 cp949인 경우가 많아서,
  // Rust(tauri)가 UTF-8로 디코딩할 때 한글이 깨지는 문제가 생길 수 있어요.
  // vib 프로세스의 출력 인코딩을 UTF-8로 강제합니다.
  PYTHONUTF8: "1",
  PYTHONIOENCODING: "utf-8",
};

/** vib CLI 실행. */
export async function runVib(
  args: string[],
  cwd?: string,
  env?: Record<string, string>
): Promise<VibResult> {
  const rootEnv: Record<string, string> = cwd
    ? { VIBELIGN_PROJECT_ROOT: cwd }
    : {};
  return invoke<VibResult>("run_vib", {
    args,
    cwd: cwd ?? null,
    env: { ...GUI_VIB_PLAIN_ENV, ...rootEnv, ...(env ?? {}) },
  });
}

export interface VibProgressEvent {
  step: string;
  done?: number | null;
  total?: number | null;
  cached?: number | null;
  to_call?: number | null;
  batches?: number | null;
  message?: string | null;
  stage?: string | null;
  batch?: number | null;
  count?: number | null;
  processed?: number | null;
  failed?: number | null;
  retried?: number | null;
  anchors?: number | null;
}

/** vib CLI 를 실행하면서 stderr `[progress]` 라인을 실시간 이벤트로 받는다. */
export async function runVibWithProgress(
  args: string[],
  cwd: string | undefined,
  env: Record<string, string> | undefined,
  onProgress: (e: VibProgressEvent) => void,
): Promise<VibResult> {
  const rootEnv: Record<string, string> = cwd
    ? { VIBELIGN_PROJECT_ROOT: cwd }
    : {};
  const eventName = `vib-progress:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
  const unlisten: UnlistenFn = await listen<VibProgressEvent>(eventName, (ev) => {
    onProgress(ev.payload);
  });
  try {
    return await invoke<VibResult>("run_vib_with_progress", {
      args,
      cwd: cwd ?? null,
      env: { ...GUI_VIB_PLAIN_ENV, ...rootEnv, ...(env ?? {}) },
      eventName,
    });
  } finally {
    unlisten();
  }
}

// ─── 편의 함수 ─────────────────────────────────────────────────────────────────

export async function vibStart(cwd: string, tools?: string[]): Promise<VibResult> {
  const args = ["start"];
  if (tools && tools.length > 0) {
    args.push("--tools", tools.join(","));
  }
  return runVib(args, cwd);
}

export async function doctorJson(cwd: string, strict = false): Promise<unknown> {
  const args = ["doctor", "--json"];
  if (strict) args.push("--strict");
  const res = await runVib(args, cwd);
  // vib doctor --json 은 {"ok": true, "data": {...}} envelope 반환
  // exit code가 0이 아니어도 JSON ok 필드가 true이면 정상 결과로 처리
  const stdout = res.stdout.trim();
  if (stdout.startsWith("{")) {
    try {
      const parsed = JSON.parse(stdout);
      if (parsed.ok && parsed.data) return parsed.data;
    } catch { /* JSON 파싱 실패 시 아래 에러 경로로 */ }
  }
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout);
  return parsed.data ?? parsed;
}

export async function doctorPlanJson(cwd: string): Promise<unknown> {
  const res = await runVib(["doctor", "--plan", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

/** GUI에 저장된 제공자 키 → `run_vib`용 환경변수 (레거시 Anthropic 단일 키 병합). */
export function buildGuiAiEnv(
  providerKeys: Record<string, string> | null | undefined,
  legacyAnthropic: string | null | undefined
): Record<string, string> | undefined {
  const map: Record<string, string> = {
    ANTHROPIC: "ANTHROPIC_API_KEY",
    OPENAI: "OPENAI_API_KEY",
    GEMINI: "GEMINI_API_KEY",
    GLM: "GLM_API_KEY",
    MOONSHOT: "MOONSHOT_API_KEY",
  };
  const env: Record<string, string> = {};
  if (providerKeys) {
    for (const [prov, envName] of Object.entries(map)) {
      const v = providerKeys[prov]?.trim();
      if (v) env[envName] = v;
    }
  }
  const leg = legacyAnthropic?.trim();
  if (leg && !env.ANTHROPIC_API_KEY) env.ANTHROPIC_API_KEY = leg;
  return Object.keys(env).length ? env : undefined;
}

export async function doctorApply(cwd: string, aiEnv?: Record<string, string>): Promise<unknown> {
  const res = await runVib(["doctor", "--apply", "--force", "--json"], cwd, aiEnv);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

// ai-enhance 설정은 Settings 토글로만 바뀌고 같은 세션 동안 반복 조회되므로
// 프로젝트별 메모리 캐시로 중복 `vib config` subprocess 호출을 제거한다.
// Why: Doctor 페이지 mount 마다 `vib config --ai-enhance status` 가 PyInstaller
//      콜드스타트를 맞아 지연을 만들었다.
const aiEnhancementCache = new Map<string, boolean>();
const autoBackupOnCommitCache = new Map<string, boolean>();

export async function getAiEnhancement(cwd: string): Promise<boolean> {
  const cached = aiEnhancementCache.get(cwd);
  if (cached !== undefined) return cached;
  const res = await runVib(["config", "--ai-enhance", "status", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { ai_enhancement?: boolean } };
  const value = Boolean(parsed.data?.ai_enhancement);
  aiEnhancementCache.set(cwd, value);
  return value;
}

export async function setAiEnhancement(cwd: string, enabled: boolean): Promise<boolean> {
  const res = await runVib(["config", "--ai-enhance", enabled ? "enable" : "disable", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { ai_enhancement?: boolean } };
  const value = Boolean(parsed.data?.ai_enhancement);
  aiEnhancementCache.set(cwd, value);
  return value;
}

export async function getAutoBackupOnCommit(cwd: string): Promise<boolean> {
  const cached = autoBackupOnCommitCache.get(cwd);
  if (cached !== undefined) return cached;
  const res = await runVib(["config", "auto-backup", "status", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { auto_backup_on_commit?: boolean } };
  const value = Boolean(parsed.data?.auto_backup_on_commit);
  autoBackupOnCommitCache.set(cwd, value);
  return value;
}

export async function setAutoBackupOnCommit(cwd: string, enabled: boolean): Promise<boolean> {
  const res = await runVib(["config", "auto-backup", enabled ? "on" : "off", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { auto_backup_on_commit?: boolean } };
  const value = Boolean(parsed.data?.auto_backup_on_commit);
  autoBackupOnCommitCache.set(cwd, value);
  return value;
}

export async function anchorAutoIntent(
  cwd: string,
  aiEnv?: Record<string, string>,
  withAi = false,
): Promise<unknown> {
  const args = ["anchor", "--auto-intent"];
  if (withAi) args.push("--with-ai");
  const res = await runVib(args, cwd, aiEnv);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return res.stdout;
}

export interface AnchorMetaEntry {
  intent?: string;
  connects?: string[];
  warning?: string;
  aliases?: string[];
  description?: string;
  _source?: string;
}

export interface AnchorAutoIntentResult {
  code_count: number;
  ai_count: number;
  ai_cached_hit?: number;
  ai_total_considered?: number;
  ai_batches?: number;
  ai_failed?: number;
  ai_retried?: number;
  total_anchors: number;
  ai_available: boolean;
  forced: boolean;
  anchor_meta_path?: string;
  message?: string;
}

export interface AnchorAutoIntentRun {
  data: AnchorAutoIntentResult;
  stderrLog: string;
}

export async function anchorAutoIntentJson(
  cwd: string,
  opts?: {
    force?: boolean;
    aiEnv?: Record<string, string>;
    withAi?: boolean;
    onProgress?: (e: VibProgressEvent) => void;
  }
): Promise<AnchorAutoIntentRun> {
  const args = ["anchor", "--auto-intent", "--json"];
  if (opts?.force) args.push("--force");
  if (opts?.withAi) args.push("--with-ai");
  const res = opts?.onProgress
    ? await runVibWithProgress(args, cwd, opts.aiEnv, opts.onProgress)
    : await runVib(args, cwd, opts?.aiEnv);
  const stdout = res.stdout.trim();
  if (!stdout) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(stdout) as {
    ok?: boolean;
    error?: string;
    data?: AnchorAutoIntentResult;
  };
  if (parsed.ok === false) throw new Error(parsed.error ?? "auto-intent 실패");
  if (!parsed.data) throw new Error("auto-intent 응답에 data가 없습니다");
  return { data: parsed.data, stderrLog: res.stderr.trim() };
}

export interface AnchorSetIntentExtras {
  aliases?: string[];
  description?: string;
  warning?: string;
  connects?: string[];
}

export async function anchorSetIntent(
  cwd: string,
  anchorName: string,
  intent: string,
  extras?: AnchorSetIntentExtras,
): Promise<{ anchor_name: string; entry: AnchorMetaEntry }> {
  const args = ["anchor", "--set-intent", anchorName, "--intent", intent, "--json"];
  const aliases = extras?.aliases?.filter((a) => a.trim()).join(",");
  if (aliases) { args.push("--aliases", aliases); }
  if (extras?.description?.trim()) { args.push("--description", extras.description); }
  if (extras?.warning?.trim()) { args.push("--warning", extras.warning); }
  const connects = extras?.connects?.filter((c) => c.trim()).join(",");
  if (connects) { args.push("--connects", connects); }
  const res = await runVib(args, cwd);
  const stdout = res.stdout.trim();
  if (!stdout) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(stdout) as {
    ok?: boolean;
    error?: string;
    data?: { anchor_name: string; entry: AnchorMetaEntry };
  };
  if (parsed.ok === false) throw new Error(parsed.error ?? "set-intent 실패");
  if (!parsed.data) throw new Error("set-intent 응답에 data가 없습니다");
  return parsed.data;
}

export async function anchorListMeta(cwd: string): Promise<Record<string, AnchorMetaEntry>> {
  const res = await runVib(["anchor", "--list-intent", "--json"], cwd);
  const stdout = res.stdout.trim();
  if (!stdout) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(stdout) as {
    ok?: boolean;
    error?: string;
    data?: { meta?: Record<string, AnchorMetaEntry> };
  };
  if (parsed.ok === false) throw new Error(parsed.error ?? "list-intent 실패");
  return parsed.data?.meta ?? {};
}

export async function checkpointCreate(cwd: string, message: string): Promise<unknown> {
  const res = await runVib(["checkpoint", message, "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const data = JSON.parse(res.stdout) as { ok?: boolean; error?: string };
  if (data.ok === false) throw new Error(data.error ?? "checkpoint 실패");
  return data;
}

export async function checkpointList(cwd: string): Promise<unknown> {
  const res = await runVib(["checkpoint", "list", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

export async function undoCheckpoint(cwd: string, checkpointId: string): Promise<unknown> {
  const res = await runVib(
    ["undo", "--checkpoint-id", checkpointId, "--force", "--json"],
    cwd
  );
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

export type BackupSourceKind = "manual" | "auto" | "safe" | "unknown";

export interface BackupFileEntry {
  path: string;
  sizeBytes: number;
}

export interface BackupEntry {
  id: string;
  note: string;
  createdAt?: string;
  fileCount?: number;
  totalSizeBytes: number;
  files: BackupFileEntry[];
  sourceKind: BackupSourceKind;
  commitNote?: string;
}

export interface BackupDbViewerCheckpointRow {
  checkpointId: string;
  displayName: string;
  createdAt: string;
  pinned: boolean;
  trigger?: string | null;
  triggerLabel: string;
  gitCommitSha?: string | null;
  gitCommitMessage?: string | null;
  fileCount: number;
  totalSizeBytes: number;
  originalSizeBytes: number;
  storedSizeBytes: number;
  reusedFileCount: number;
  changedFileCount: number;
  engineVersion?: string | null;
  parentCheckpointId?: string | null;
  internalBadges: string[];
}

export interface BackupDbViewerInspectResult {
  dbExists: boolean;
  dbPath: string;
  dbFile: {
    databaseBytes: number;
    walBytes: number;
    shmBytes: number;
    totalBytes: number;
  };
  schemaVersion?: string | null;
  checkpointCount: number;
  rustV2Count: number;
  legacyCount: number;
  casObjectCount: number;
  casRefCount: number;
  totalOriginalSizeBytes: number;
  totalStoredSizeBytes: number;
  autoBackupOnCommit: boolean;
  retentionPolicy?: {
    keepLatest: number;
    keepDailyDays: number;
    keepWeeklyWeeks: number;
    maxTotalSizeBytes: number;
    maxAgeDays: number;
    minKeep: number;
  } | null;
  objectStore: {
    exists: boolean;
    path: string;
    compressionSummary: Array<{ compression: string; objectCount: number }>;
    storedSizeBytes: number;
    originalSizeBytes: number;
  };
  checkpoints: BackupDbViewerCheckpointRow[];
  warnings: string[];
}

export interface BackupListResult {
  backups: BackupEntry[];
  warning?: string | null;
}

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

function readNumber(value: number | null | undefined): number {
  return typeof value === "number" ? value : 0;
}

function normalizeDbFile(raw?: RawBackupDbViewerDbFileStats | null): BackupDbViewerInspectResult["dbFile"] {
  return {
    databaseBytes: readNumber(raw?.database_bytes),
    walBytes: readNumber(raw?.wal_bytes),
    shmBytes: readNumber(raw?.shm_bytes),
    totalBytes: readNumber(raw?.total_bytes),
  };
}

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

function backupSourceKind(trigger?: string | null): BackupSourceKind {
  if (trigger === "post_commit") return "auto";
  if (trigger === "safe_restore") return "safe";
  if (!trigger) return "manual";
  return "unknown";
}

function cleanRawBackupNote(raw: RawCheckpointEntry): string {
  const note = (raw.git_commit_message || raw.message || "")
    .replace(/^vibelign:\s*checkpoint\s*-?\s*/i, "")
    .replace(/\s*\(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\)\s*$/, "")
    .trim();
  if (raw.trigger === "post_commit") {
    return note ? `코드 저장 뒤 자동 보관 - ${note}` : "코드 저장 뒤 자동 보관";
  }
  return note || "메모 없는 저장본";
}

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

function normalizeBackupFileEntry(raw: RawCheckpointFileEntry): BackupFileEntry | null {
  const path = raw.relative_path ?? raw.path;
  if (!path) return null;
  const size = raw.size ?? raw.size_bytes ?? 0;
  return {
    path: path.replaceAll("\\", "/"),
    sizeBytes: typeof size === "number" ? size : 0,
  };
}

export async function backupCreate(cwd: string, note: string): Promise<unknown> {
  return checkpointCreate(cwd, note);
}

export async function backupList(cwd: string): Promise<BackupListResult> {
  const data = await checkpointList(cwd) as {
    checkpoints?: RawCheckpointEntry[];
    warning?: string | null;
  };
  return {
    backups: (data.checkpoints ?? [])
      .map(normalizeBackupEntry)
      .filter((entry) => entry.id && entry.sourceKind !== "safe"),
    warning: data.warning ?? null,
  };
}

export async function backupDbViewerInspect(cwd: string): Promise<BackupDbViewerInspectResult> {
  const res = await runVib(["backup-db-viewer", "--json"], cwd);
  const stdout = res.stdout.trim();
  if (!res.ok && stdout.startsWith("{")) {
    const parsed = JSON.parse(stdout) as RawBackupDbViewerInspectResult;
    return parseBackupDbViewerInspectResult(parsed);
  }
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(stdout) as RawBackupDbViewerInspectResult;
  return parseBackupDbViewerInspectResult(parsed);
}

export async function backupRestore(cwd: string, backupId: string): Promise<unknown> {
  return undoCheckpoint(cwd, backupId);
}

export interface GuardIssue { found: string; next_step: string; path: string }
export interface GuardResult {
  status: string;
  summary: string;
  recommendations: string[];
  issues: GuardIssue[];
}

function _toStr(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function _toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}

function _toGuardIssues(value: unknown): GuardIssue[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((i): i is Record<string, unknown> => typeof i === "object" && i !== null)
    .map((i) => ({
      found: _toStr(i.found),
      next_step: _toStr(i.next_step),
      path: _toStr(i.path),
    }));
}

export async function vibGuard(cwd: string, opts?: { strict?: boolean; sinceMinutes?: number; writeReport?: boolean }): Promise<GuardResult> {
  const args = ["guard", "--json"];
  if (opts?.strict) args.push("--strict");
  if (opts?.sinceMinutes) args.push("--since-minutes", String(opts.sinceMinutes));
  if (opts?.writeReport) args.push("--write-report");
  const res = await runVib(args, cwd);
  const raw = res.stdout.trim();
  if (!raw) throw new Error(res.stderr || `exit ${res.exit_code}`);
  // JSON.parse 결과는 unknown 으로 다루고 IPC 경계에서 런타임 검증한다.
  // Why: vib CLI 스키마가 달라지거나 비정상 종료로 stderr 가 섞여도
  // UI 가 조용히 `undefined` 를 문자열로 렌더링하지 않게 한다.
  const parsed: unknown = JSON.parse(raw);
  const root = (parsed && typeof parsed === "object" ? parsed as Record<string, unknown> : {});
  const data = (root.data && typeof root.data === "object" ? root.data as Record<string, unknown> : root);
  const doctor = (data.doctor && typeof data.doctor === "object" ? data.doctor as Record<string, unknown> : {});
  return {
    status: _toStr(data.status) || "unknown",
    summary: _toStr(data.summary),
    recommendations: _toStringArray(data.recommendations),
    issues: _toGuardIssues(doctor.issues),
  };
}

export async function vibScan(cwd: string): Promise<VibResult> {
  return runVib(["scan"], cwd);
}

export async function vibTransfer(
  cwd: string,
  opts?: {
    handoff?: boolean;
    compact?: boolean;
    full?: boolean;
    sessionSummary?: string;
    firstNextAction?: string;
  },
): Promise<VibResult> {
  const args = ["transfer"];
  if (opts?.handoff) {
    args.push("--handoff");
    args.push("--no-prompt");
    if (opts.sessionSummary) args.push("--session-summary", opts.sessionSummary);
    if (opts.firstNextAction) args.push("--first-next-action", opts.firstNextAction);
  }
  if (opts?.compact) args.push("--compact");
  if (opts?.full) args.push("--full");
  return runVib(args, cwd);
}

export async function startWatch(cwd: string): Promise<void> {
  return invoke<void>("start_watch", { cwd });
}

export async function stopWatch(): Promise<void> {
  return invoke<void>("stop_watch");
}

export async function watchStatus(): Promise<boolean> {
  return invoke<boolean>("watch_status");
}

export async function getWatchLogs(): Promise<string[]> {
  return invoke<string[]>("get_watch_logs");
}

export async function getWatchErrors(): Promise<string[]> {
  return invoke<string[]>("get_watch_errors");
}

// ─── API 키 관리 ────────────────────────────────────────────────────────────────

export async function saveRecentProjects(dirs: string[]): Promise<void> {
  return invoke<void>("save_recent_projects", { dirs });
}

export async function loadRecentProjects(): Promise<string[]> {
  return invoke<string[]>("load_recent_projects");
}

export async function saveApiKey(key: string): Promise<void> {
  return invoke<void>("save_api_key", { key });
}

export async function loadApiKey(): Promise<string | null> {
  return invoke<string | null>("load_api_key");
}

export async function deleteApiKey(): Promise<void> {
  return invoke<void>("delete_api_key");
}

export async function saveProviderApiKey(provider: string, key: string): Promise<void> {
  return invoke<void>("save_provider_api_key", { provider, key });
}

export async function deleteProviderApiKey(provider: string): Promise<void> {
  return invoke<void>("delete_provider_api_key", { provider });
}

export async function loadProviderApiKeys(): Promise<Record<string, string>> {
  return invoke<Record<string, string>>("load_provider_api_keys");
}

export async function getManualJson(): Promise<Record<string, unknown>> {
  const res = await runVib(["manual", "--json"]);
  const raw = res.stdout.trim();
  if (!raw) {
    throw new Error(res.stderr || `exit ${res.exit_code}`);
  }
  const parsed = JSON.parse(raw) as unknown;
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    const data = parsed as Record<string, unknown>;
    if ("data" in data && data.data && typeof data.data === "object" && !Array.isArray(data.data)) {
      return data.data as Record<string, unknown>;
    }
    return data;
  }
  throw new Error("manual json parse failed");
}

export async function getEnvKeyStatus(): Promise<Record<string, boolean>> {
  return invoke<Record<string, boolean>>("get_env_key_status");
}

export interface SummaryLine {
  display: string;
  detail: string;
}

export interface ProjectSummary {
  project_name: string;
  checkpoints: SummaryLine[];
  git_commits: SummaryLine[];
}

export async function readProjectSummary(dir: string): Promise<ProjectSummary> {
  return invoke<ProjectSummary>("read_project_summary", { dir });
}

export async function checkGitInstalled(): Promise<boolean> {
  return invoke<boolean>("check_git_installed");
}

export async function checkXcodeClt(): Promise<boolean> {
  return invoke<boolean>("check_xcode_clt");
}
// === ANCHOR: VIB_BRIDGE_END ===
