// === ANCHOR: RUN_START ===
// 실행해보기(Run & Preview) 러너 — src-tauri/commands/run_preview.rs 의 invoke 래퍼.
// 타입은 백엔드 serde(camelCase) 계약과 1:1. watch.ts 패턴을 따른다.
import { invoke } from "@tauri-apps/api/core";

export type RunProjectKind = "electron" | "web" | "unknown";

/** run_detect 결과. program/preview 상세는 UI 가 안 써서 생략(invoke 가 추가 필드는 무시). */
export interface RunRecipe {
  kind: RunProjectKind;
  commandLabel: string;
}

export interface RunStartInfo {
  runId: number;
  commandLabel: string;
  kind: RunProjectKind;
  needsInstall: boolean;
}

export interface RunStatusInfo {
  running: boolean;
  runId: number;
  /** 탭 복귀 시 [미리보기 열기] 복원용(run-preview-ready 는 fire-once). */
  previewUrl: string | null;
  /** 현재 단계("installing"/"running") — 복원이 install/실행을 구분해 표시. */
  status: RunStatusKind | null;
}

export type RunPhase = "install" | "run";
export type RunStatusKind = "installing" | "running" | "done" | "failed" | "stopped";

export interface RunOutputEvent {
  runId: number;
  phase: RunPhase;
  stream: "stdout" | "stderr";
  line: string;
}

export interface RunStatusEvent {
  runId: number;
  status: RunStatusKind;
  exitCode: number | null;
}

export interface RunPreviewReadyEvent {
  runId: number;
  url: string;
}

/** package.json → 실행 레시피(없으면 null). 실행 전 타입 표시용. */
export async function runDetect(cwd: string): Promise<RunRecipe | null> {
  return invoke<RunRecipe | null>("run_detect", { cwd });
}

/** dev 실행 시작 — node_modules 없으면 install 후 실행. 동시 1개(작업방과도 §5). */
export async function runStart(cwd: string): Promise<RunStartInfo> {
  return invoke<RunStartInfo>("run_start", { cwd });
}

/** 실행 중지(트리 kill). 반환: 점유 중이던 실행이 있었는지. */
export async function runStop(): Promise<boolean> {
  return invoke<boolean>("run_stop");
}

/** 현재 실행 상태 — 탭 복귀 시 복원용. */
export async function runStatus(): Promise<RunStatusInfo> {
  return invoke<RunStatusInfo>("run_status");
}

/** 미리보기 webview 별도 창 열기/포커스. url 은 run-preview-ready 의 값. */
export async function openPreview(url: string): Promise<void> {
  return invoke<void>("open_preview", { url });
}

/** 미리보기 창 닫기. */
export async function closePreview(): Promise<void> {
  return invoke<void>("close_preview");
}
// === ANCHOR: RUN_END ===
