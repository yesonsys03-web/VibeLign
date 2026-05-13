import { invoke } from "@tauri-apps/api/core";

export async function startWatch(cwd: string): Promise<void> {
  return invoke<void>("start_watch", { cwd });
}

export async function stopWatch(): Promise<void> {
  return invoke<void>("stop_watch");
}

export async function watchStatus(): Promise<boolean> {
  return invoke<boolean>("watch_status");
}

export async function getWatchLogs(): Promise<string[]> {
  return invoke<string[]>("get_watch_logs");
}

export async function getWatchErrors(): Promise<string[]> {
  return invoke<string[]>("get_watch_errors");
}
