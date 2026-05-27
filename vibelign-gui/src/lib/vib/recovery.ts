// === ANCHOR: RECOVERY_START ===
import { runVib } from "./core";
import { requireNumber, requireOptionalRecord, requireRecord, requireRecordArray, requireString } from "./normalizers";
import type { RecoveryPreviewResult, RecoveryRecommendationResponse } from "./types";

// === ANCHOR: RECOVERY_RECOVERYPREVIEW_START ===
export async function recoveryPreview(cwd: string): Promise<RecoveryPreviewResult> {
  const res = await runVib(["recover", "--preview", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  return parseRecoveryPreviewJson(res.stdout);
}
// === ANCHOR: RECOVERY_RECOVERYPREVIEW_END ===

// === ANCHOR: RECOVERY_RECOVERYRECOMMEND_START ===
export async function recoveryRecommend(cwd: string, phrase: string, aiEnv?: Record<string, string>): Promise<RecoveryRecommendationResponse> {
  const res = await runVib(["recover", "--recommend", "--phrase", phrase], cwd, aiEnv);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  return parseRecoveryRecommendationJson(res.stdout);
}
// === ANCHOR: RECOVERY_RECOVERYRECOMMEND_END ===

// === ANCHOR: RECOVERY_PARSERECOVERYPREVIEWJSON_START ===
function parseRecoveryPreviewJson(stdout: string): RecoveryPreviewResult {
  const data = requireRecord(JSON.parse(stdout), "recovery_plan.schema.json");
  requireString(data.plan_id, "plan_id");
  requireString(data.mode, "mode");
  requireNumber(data.level, "level");
  requireString(data.summary, "summary");
  const options = requireRecordArray(data.options, "options");
  const driftCandidates = requireRecordArray(data.drift_candidates, "drift_candidates");
  requireOptionalRecord(data.safe_checkpoint_candidate, "safe_checkpoint_candidate");
  requireString(data.circuit_breaker_state, "circuit_breaker_state");
  requireRecordArray(data.p0_summaries, "p0_summaries").forEach((item, index) => {
    requireString(item.slo_id, `p0_summaries[${index}].slo_id`);
    requireString(item.window_start, `p0_summaries[${index}].window_start`);
    requireString(item.window_end, `p0_summaries[${index}].window_end`);
    requireNumber(item.occurrences, `p0_summaries[${index}].occurrences`);
    requireNumber(item.sample_count, `p0_summaries[${index}].sample_count`);
    requireString(item.result, `p0_summaries[${index}].result`);
    requireNumber(item.corrupt_rows_count, `p0_summaries[${index}].corrupt_rows_count`);
    requireString(item.warning, `p0_summaries[${index}].warning`);
  });
  options.forEach((item, index) => requireString(item.label, `options[${index}].label`));
  driftCandidates.forEach((item, index) => {
    requireString(item.path, `drift_candidates[${index}].path`);
    requireString(item.why_outside_zone, `drift_candidates[${index}].why_outside_zone`);
  });
  if (data.safe_checkpoint_candidate !== undefined && data.safe_checkpoint_candidate !== null) {
    const candidate = data.safe_checkpoint_candidate as Record<string, unknown>;
    requireString(candidate.checkpoint_id, "safe_checkpoint_candidate.checkpoint_id");
    requireString(candidate.created_at, "safe_checkpoint_candidate.created_at");
    requireString(candidate.message, "safe_checkpoint_candidate.message");
    if (candidate.trigger !== undefined && candidate.trigger !== null) requireString(candidate.trigger, "safe_checkpoint_candidate.trigger");
    if (candidate.git_commit_message !== undefined && candidate.git_commit_message !== null) requireString(candidate.git_commit_message, "safe_checkpoint_candidate.git_commit_message");
  }
  const typed = data as {
    schema_version?: string;
    summary?: string;
    options?: Array<{ label?: string }>;
    drift_candidates?: Array<{ path?: string; why_outside_zone?: string }>;
    safe_checkpoint_candidate?: { checkpoint_id?: string; created_at?: string; message?: string; trigger?: string | null; git_commit_message?: string | null } | null;
  };
  const safeCheckpointCandidate = typed.safe_checkpoint_candidate
    ? {
        checkpointId: typed.safe_checkpoint_candidate.checkpoint_id ?? "",
        createdAt: typed.safe_checkpoint_candidate.created_at ?? "",
        message: typed.safe_checkpoint_candidate.message ?? "",
        trigger: typed.safe_checkpoint_candidate.trigger ?? null,
        gitCommitMessage: typed.safe_checkpoint_candidate.git_commit_message ?? null,
      }
    : null;
  return {
    schemaVersion: typed.schema_version ?? "recovery_plan.schema.json",
    summary: typed.summary || "No recovery summary available.",
    options: (typed.options ?? []).map((item) => item.label ?? "").filter(Boolean),
    driftCandidates: (typed.drift_candidates ?? []).map((item) => `${item.path ?? ""} — ${item.why_outside_zone ?? ""}`).filter((item) => !item.startsWith(" —")),
    safeCheckpointCandidate,
    raw: stdout,
  };
}
// === ANCHOR: RECOVERY_PARSERECOVERYPREVIEWJSON_END ===

// === ANCHOR: RECOVERY_PARSERECOVERYRECOMMENDATIONJSON_START ===
function parseRecoveryRecommendationJson(stdout: string): RecoveryRecommendationResponse {
  const data = requireRecord(JSON.parse(stdout), "recovery_recommendation.schema.json");
  requireString(data.recommendation_provider, "recommendation_provider");
  requireString(data.interpreted_goal, "interpreted_goal");
  if (data.fallback_reason !== null) requireString(data.fallback_reason, "fallback_reason");
  const ranked = requireRecordArray(data.ranked_candidates, "ranked_candidates");
  ranked.forEach((item, index) => {
    requireString(item.candidate_id, `ranked_candidates[${index}].candidate_id`);
    requireNumber(item.rank, `ranked_candidates[${index}].rank`);
    requireString(item.label, `ranked_candidates[${index}].label`);
    requireString(item.source, `ranked_candidates[${index}].source`);
    requireString(item.created_at, `ranked_candidates[${index}].created_at`);
    if (item.commit_message !== undefined && item.commit_message !== null) requireString(item.commit_message, `ranked_candidates[${index}].commit_message`);
    requireOptionalRecord(item.llm_confidence, `ranked_candidates[${index}].llm_confidence`);
    requireString(item.reason, `ranked_candidates[${index}].reason`);
    requireRecord(item.evidence_score, `ranked_candidates[${index}].evidence_score`);
  });
  return data as unknown as RecoveryRecommendationResponse;
}
// === ANCHOR: RECOVERY_PARSERECOVERYRECOMMENDATIONJSON_END ===
// === ANCHOR: RECOVERY_END ===
