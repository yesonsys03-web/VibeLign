// === ANCHOR: VIB_BRIDGE_START ===
/**
 * Tauri IPC 브리지 — Rust의 run_vib / get_vib_path command 호출.
 * 모든 vib CLI 접근은 이 모듈을 통한다.
 */
import { invoke } from "@tauri-apps/api/core";
import { open as dialogOpen } from "@tauri-apps/plugin-dialog";

export async function pickFile(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ multiple: false, defaultPath: defaultPath ?? undefined });
  return typeof result === "string" ? result : null;
}
export async function openFolder(path: string): Promise<void> {
  return invoke<void>("open_folder", { path });
}

export interface VibResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
}

/** vib 실행 파일 경로 반환. 없으면 null. */
export async function getVibPath(): Promise<string | null> {
  return invoke<string | null>("get_vib_path");
}

/** vib CLI 실행. */
export async function runVib(
  args: string[],
  cwd?: string,
  env?: Record<string, string>
): Promise<VibResult> {
  return invoke<VibResult>("run_vib", { args, cwd: cwd ?? null, env: env ?? null });
}

// ─── 편의 함수 ─────────────────────────────────────────────────────────────────

export async function vibStart(cwd: string): Promise<VibResult> {
  return runVib(["start"], cwd);
}

export async function doctorJson(cwd: string): Promise<unknown> {
  const res = await runVib(["doctor", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout);
  // vib doctor --json 은 {"ok": true, "data": {...}} envelope 반환
  return parsed.data ?? parsed;
}

export async function doctorPlanJson(cwd: string): Promise<unknown> {
  const res = await runVib(["doctor", "--plan", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

export async function doctorApply(cwd: string, apiKey?: string): Promise<unknown> {
  const env = apiKey ? { ANTHROPIC_API_KEY: apiKey } : undefined;
  const res = await runVib(["doctor", "--apply", "--force", "--json"], cwd, env);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
}

export async function checkpointCreate(cwd: string, message: string): Promise<unknown> {
  const res = await runVib(["checkpoint", message, "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
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

export interface GuardIssue { found: string; next_step: string; path: string }
export interface GuardResult {
  status: string;
  summary: string;
  recommendations: string[];
  issues: GuardIssue[];
}

export async function vibGuard(cwd: string, opts?: { strict?: boolean; sinceMinutes?: number; writeReport?: boolean }): Promise<GuardResult> {
  const args = ["guard", "--json"];
  if (opts?.strict) args.push("--strict");
  if (opts?.sinceMinutes) args.push("--since-minutes", String(opts.sinceMinutes));
  if (opts?.writeReport) args.push("--write-report");
  const res = await runVib(args, cwd);
  const raw = res.stdout.trim();
  if (!raw) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(raw);
  const data = parsed.data ?? parsed;
  const issues: GuardIssue[] = (data.doctor?.issues ?? []).map((i: any) => ({
    found: i.found ?? "",
    next_step: i.next_step ?? "",
    path: i.path ?? "",
  }));
  return {
    status: data.status ?? "unknown",
    summary: data.summary ?? "",
    recommendations: data.recommendations ?? [],
    issues,
  };
}

export async function vibScan(cwd: string): Promise<VibResult> {
  return runVib(["scan"], cwd);
}

export async function vibTransfer(cwd: string, opts?: { handoff?: boolean; compact?: boolean; full?: boolean }): Promise<VibResult> {
  const args = ["transfer"];
  if (opts?.handoff) { args.push("--handoff"); args.push("--no-prompt"); }
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

export async function getEnvKeyStatus(): Promise<Record<string, boolean>> {
  return invoke<Record<string, boolean>>("get_env_key_status");
}
// === ANCHOR: VIB_BRIDGE_END ===
