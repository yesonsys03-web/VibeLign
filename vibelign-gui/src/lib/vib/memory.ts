import { runVib } from "./core";
import { requireNumber, requireOptionalRecord, requireRecord, requireRecordArray, requireString } from "./normalizers";
import type {
  HandoffDraftActionResult,
  HandoffDraftField,
  HandoffDraftPayload,
  HandoffDraftResponse,
  MemorySummaryResult,
  VibResult,
} from "./types";

export async function memorySummary(cwd: string): Promise<MemorySummaryResult> {
  const res = await runVib(["memory", "show", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  return parseMemorySummaryJson(res.stdout);
}

export async function createHandoffDraft(
  cwd: string,
  summary: string,
  nextAction: string,
  relevantFiles: string[] = [],
  verification: string[] = [],
  riskNotes: string[] = [],
): Promise<HandoffDraftResponse> {
  const args = ["memory", "proposal-create", "--session-summary", summary, "--first-next-action", nextAction];
  for (const item of relevantFiles) args.push("--relevant-file", item);
  for (const item of verification) args.push("--verification", item);
  for (const item of riskNotes) args.push("--risk-note", item);
  const res = await runVib(args, cwd);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  const payload = JSON.parse(res.stdout) as { ok: boolean; read_only: boolean; draft: HandoffDraftPayload };
  return {
    ok: payload.ok,
    mode: "handoff_memory_draft",
    project_context_path: "",
    deterministic_handoff_written: false,
    draft: payload.draft,
  };
}

export async function acceptHandoffDraftField(cwd: string, draft: HandoffDraftPayload, field: HandoffDraftField): Promise<HandoffDraftActionResult> {
  const res = await runVib(["memory", "proposal-accept", "--field", field, "--draft-json", JSON.stringify(draft)], cwd);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout) as HandoffDraftActionResult;
}

export async function dismissHandoffDraftField(cwd: string, draft: HandoffDraftPayload, field: HandoffDraftField): Promise<HandoffDraftActionResult> {
  const res = await runVib(["memory", "proposal-dismiss", "--field", field, "--draft-json", JSON.stringify(draft)], cwd);
  if (!res.ok) throw new Error(res.stderr || res.stdout || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout) as HandoffDraftActionResult;
}

function parseMemorySummaryJson(stdout: string): MemorySummaryResult {
  const data = requireRecord(JSON.parse(stdout), "memory_state.schema.json");
  requireNumber(data.schema_version, "schema_version");
  requireOptionalRecord(data.active_intent, "active_intent");
  requireOptionalRecord(data.next_action, "next_action");
  const decisions = requireRecordArray(data.decisions, "decisions");
  const relevantFiles = requireRecordArray(data.relevant_files, "relevant_files");
  const verificationItems = requireRecordArray(data.verification, "verification");
  const risks = requireRecordArray(data.risks, "risks");
  if (data.active_intent !== undefined && data.active_intent !== null) {
    requireString((data.active_intent as Record<string, unknown>).text, "active_intent.text");
  }
  if (data.next_action !== undefined && data.next_action !== null) {
    requireString((data.next_action as Record<string, unknown>).text, "next_action.text");
  }
  decisions.forEach((item, index) => requireString(item.text, `decisions[${index}].text`));
  relevantFiles.forEach((item, index) => {
    requireString(item.path, `relevant_files[${index}].path`);
    requireString(item.why, `relevant_files[${index}].why`);
  });
  verificationItems.forEach((item, index) => requireString(item.command, `verification[${index}].command`));
  risks.forEach((item, index) => requireString(item.text, `risks[${index}].text`));
  const typed = data as {
    schema_version?: number;
    active_intent?: { text?: string } | null;
    next_action?: { text?: string } | null;
    decisions?: Array<{ text?: string }>;
    relevant_files?: Array<{ path?: string; why?: string; source?: string }>;
    verification?: Array<{ command?: string; stale?: boolean }>;
    risks?: Array<{ text?: string }>;
    downgrade_warning?: string;
  };
  const verification = (typed.verification ?? []).map((item) => item.stale ? `${item.command ?? ""} (stale)` : item.command ?? "").filter(Boolean);
  return {
    schemaVersion: typed.schema_version,
    activeIntent: typed.active_intent?.text || "(none)",
    nextAction: typed.next_action?.text || "(none)",
    decisions: (typed.decisions ?? []).map((item) => item.text ?? "").filter(Boolean),
    relevantFiles: (typed.relevant_files ?? []).map((item) => `${item.path ?? ""} — ${item.why ?? ""} (${item.source ?? ""})`).filter((item) => !item.startsWith(" —")),
    verification,
    risks: (typed.risks ?? []).map((item) => item.text ?? "").filter(Boolean),
    verificationFreshness: verificationFreshness(verification),
    warning: typed.downgrade_warning || undefined,
  };
}

function verificationFreshness(lines: string[]): "fresh" | "stale" | "missing" {
  if (lines.length === 0) return "missing";
  return lines.some((line) => line.toLowerCase().includes("stale")) ? "stale" : "fresh";
}

export async function vibTransfer(
  cwd: string,
  opts?: {
    handoff?: boolean;
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
  if (opts?.full) args.push("--full");
  return runVib(args, cwd);
}
