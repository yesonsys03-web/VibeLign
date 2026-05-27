// Public bridge types preserved from ../vib.ts.
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
  body_preview?: string[];
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

export interface DocsHtmlArtifact {
  source_path: string;
  source_hash: string;
  generated_at: string;
  generator_version: string;
  schema_version: number;
  title: string;
  html: string;
  csp: string;
  mode: "raw_html";
}

export interface DocsHtmlReadResult {
  path: string;
  artifact: DocsHtmlArtifact;
  contract: DocsVisualContract;
}

export interface EnhanceDocResult {
  ok: boolean;
  path: string;
  ai_fields: DocsVisualAIFields;
}

export interface VibResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
}

export interface MemorySummaryResult {
  schemaVersion?: number;
  activeIntent: string;
  nextAction: string;
  decisions: string[];
  relevantFiles: string[];
  verification: string[];
  risks: string[];
  verificationFreshness: "fresh" | "stale" | "missing";
  warning?: string;
}

export type HandoffDraftField = "session_summary" | "active_intent" | "next_action" | "relevant_files" | "verification" | "risk_notes";

export interface HandoffDraftRecommendation {
  field: HandoffDraftField;
  value: unknown;
  reason: string;
  proposal_hash: string;
  source: string;
}

export interface HandoffDraftPayload {
  draft_id: string;
  context_hash: string;
  provider: string;
  should_write_memory: boolean;
  recommendations: HandoffDraftRecommendation[];
}

export interface HandoffDraftResponse {
  ok: boolean;
  mode: string;
  project_context_path: string;
  deterministic_handoff_written: boolean;
  draft: HandoffDraftPayload;
}

export interface HandoffDraftActionResult {
  ok: boolean;
  action: "accepted" | "dismissed" | "undone";
  field: HandoffDraftField;
  proposal_hash: string;
  message?: string;
}

export interface RecoveryPreviewResult {
  schemaVersion?: string;
  summary: string;
  options: string[];
  driftCandidates: string[];
  safeCheckpointCandidate: SafeCheckpointCandidatePreview | null;
  raw: string;
}

export interface SafeCheckpointCandidatePreview {
  checkpointId: string;
  createdAt: string;
  message: string;
  trigger: string | null;
  gitCommitMessage: string | null;
}

export type RecommendationProvider = "deterministic" | "llm" | "cache" | "invalid";

export interface EvidenceScorePayload {
  score: number;
  formula_version: string;
  commit_boundary?: boolean;
  verification_fresh?: boolean;
  diff_small?: boolean;
  protected_paths_clean?: boolean;
  time_match_user_request?: boolean;
}

export interface LLMConfidencePayload {
  level: "high" | "medium" | "low";
  reason: string;
}

export interface RankedCandidatePayload {
  candidate_id: string;
  rank: number;
  label: string;
  source: string;
  created_at: string;
  commit_message?: string | null;
  evidence_score: EvidenceScorePayload;
  llm_confidence: LLMConfidencePayload | null;
  reason: string;
  expected_loss: string[];
}

export interface RecoveryRecommendationResponse {
  recommendation_provider: RecommendationProvider;
  interpreted_goal: string;
  fallback_reason: string | null;
  ranked_candidates: RankedCandidatePayload[];
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

export interface AnchorSetIntentExtras {
  aliases?: string[];
  description?: string;
  warning?: string;
  connects?: string[];
}

export interface CheckpointCreateResult {
  ok?: boolean;
  error?: string;
  warning?: string | null;
}

export interface ErrorLogEntry {
  ts: string;
  kind: "cli" | "gui";
  error_class: string | null;
  message: string;
  context: string | null;
  raw_json: string;
}

export interface ClearErrorLogsResult {
  removed: number;
  kept: number;
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

export interface BackupDbMaintenanceResult {
  dbExists: boolean;
  mode: string;
  plannedAction: string;
  vacuumRecommended: boolean;
  checkpointRecommended: boolean;
  reclaimedBytes: number;
  blockers: string[];
  warnings: string[];
}

export interface BackupCleanupResult {
  retention: {
    count: number;
    plannedCount: number;
    plannedBytes: number;
    reclaimedBytes: number;
    partialFailure: boolean;
  };
  maintenance: BackupDbMaintenanceResult;
}

export interface BackupGraphNode {
  id: string;
  name: string;
  path: string;
  sizeBytes: number;
  children: BackupGraphNode[];
}

export interface BackupGraphSummaryResult {
  dbExists: boolean;
  fileRowCount: number;
  root: BackupGraphNode;
  warnings: string[];
}

export interface BackupListResult {
  backups: BackupEntry[];
  warning?: string | null;
}

export interface GuardIssue { found: string; next_step: string; path: string }

export interface GuardResult {
  status: string;
  summary: string;
  recommendations: string[];
  issues: GuardIssue[];
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

export interface CodeFileEntry {
  path: string;
  category: string;
  imports: string[];
}

export interface ProjectScanResult {
  result?: string;
  files?: CodeFileEntry[];
}

export interface CodeFileReadResult {
  path: string;
  content: string;
  source_hash: string;
  size_bytes: number;
  line_count: number;
  language: string;
}
