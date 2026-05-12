import { runVib, runVibWithProgress } from "./core";
import type {
  AnchorAutoIntentRun,
  AnchorAutoIntentResult,
  AnchorMetaEntry,
  AnchorSetIntentExtras,
  VibProgressEvent,
} from "./types";

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
