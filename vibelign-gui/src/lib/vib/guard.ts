import { runVib } from "./core";
import type { GuardIssue, GuardResult, VibResult } from "./types";

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

export async function doctorApply(cwd: string, aiEnv?: Record<string, string>): Promise<unknown> {
  const res = await runVib(["doctor", "--apply", "--force", "--json"], cwd, aiEnv);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  return JSON.parse(res.stdout);
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
