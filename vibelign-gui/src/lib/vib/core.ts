import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type { VibProgressEvent, VibResult } from "./types";

export function normalizeBridgePath(path: string): string {
  return path.replaceAll("\\", "/");
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
  // GUI 백업 화면은 Rust/SQLite DB를 기준으로 목록과 복구를 보여준다.
  // Rust engine이 없으면 Python fallback으로 조용히 저장하지 말고 에러를 노출한다.
  VIBELIGN_REQUIRE_RUST_CHECKPOINT: "1",
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

interface EngineDirectResult {
  ok: boolean;
  response_json: string;
  error: string | null;
}

export async function callEngineDirect<T>(request: Record<string, unknown>): Promise<T> {
  const res = await invoke<EngineDirectResult>("run_engine_request_direct", {
    requestJson: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(res.error ?? "engine direct call failed");
  return JSON.parse(res.response_json) as T;
}
