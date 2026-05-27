// === ANCHOR: WATCH_START ===
import { invoke } from "@tauri-apps/api/core";

// === ANCHOR: WATCH_STARTWATCH_START ===
export async function startWatch(cwd: string): Promise<void> {
  return invoke<void>("start_watch", { cwd });
}
// === ANCHOR: WATCH_STARTWATCH_END ===

// === ANCHOR: WATCH_STOPWATCH_START ===
export async function stopWatch(): Promise<void> {
  return invoke<void>("stop_watch");
}
// === ANCHOR: WATCH_STOPWATCH_END ===

// === ANCHOR: WATCH_WATCHSTATUS_START ===
export async function watchStatus(): Promise<boolean> {
  return invoke<boolean>("watch_status");
}
// === ANCHOR: WATCH_WATCHSTATUS_END ===

// === ANCHOR: WATCH_GETWATCHLOGS_START ===
export async function getWatchLogs(): Promise<string[]> {
  return invoke<string[]>("get_watch_logs");
}
// === ANCHOR: WATCH_GETWATCHLOGS_END ===

// === ANCHOR: WATCH_GETWATCHERRORS_START ===
export async function getWatchErrors(): Promise<string[]> {
  return invoke<string[]>("get_watch_errors");
}
// === ANCHOR: WATCH_GETWATCHERRORS_END ===
// === ANCHOR: WATCH_END ===
