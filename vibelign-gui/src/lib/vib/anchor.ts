import { callEngineDirect, runVib, runVibWithProgress } from "./core";
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
  const aliases = extras?.aliases?.map((a) => a.trim()).filter(Boolean);
  const connects = extras?.connects?.map((c) => c.trim()).filter(Boolean);
  const warning = extras?.warning?.trim();
  const description = extras?.description?.trim();
  const parsed = await callEngineDirect<{ anchor_name: string; entry: AnchorMetaEntry }>({
    command: "anchor_set_intent",
    root: cwd,
    anchor_name: anchorName,
    intent,
    connects: connects && connects.length > 0 ? connects : null,
    aliases: aliases && aliases.length > 0 ? aliases : null,
    warning: warning ? warning : null,
    description: description ? description : null,
  });
  return parsed;
}

export async function anchorListMeta(cwd: string): Promise<Record<string, AnchorMetaEntry>> {
  const parsed = await callEngineDirect<{ meta?: Record<string, AnchorMetaEntry> }>({
    command: "anchor_list_meta",
    root: cwd,
  });
  return parsed.meta ?? {};
}
