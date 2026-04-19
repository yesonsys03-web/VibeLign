import { relaunch } from "@tauri-apps/plugin-process";
import { check, type DownloadEvent, type Update } from "@tauri-apps/plugin-updater";

export interface AppUpdateProgress {
  downloadedBytes: number;
  totalBytes: number | null;
  percent: number | null;
}

export function shouldCheckForUpdates(): boolean {
  return !import.meta.env.DEV && import.meta.env.VITE_APP_UPDATER_ENABLED === "true";
}

export async function checkForAppUpdate(): Promise<Update | null> {
  return check();
}

export async function installAppUpdate(
  update: Update,
  onProgress?: (progress: AppUpdateProgress) => void,
): Promise<void> {
  let downloadedBytes = 0;
  let totalBytes: number | null = null;

  await update.downloadAndInstall((event: DownloadEvent) => {
    if (event.event === "Started") {
      totalBytes = typeof event.data.contentLength === "number" ? event.data.contentLength : null;
      downloadedBytes = 0;
    }

    if (event.event === "Progress") {
      downloadedBytes += event.data.chunkLength;
    }

    if (event.event !== "Finished") {
      onProgress?.({
        downloadedBytes,
        totalBytes,
        percent: totalBytes && totalBytes > 0 ? Math.min(100, Math.round((downloadedBytes / totalBytes) * 100)) : null,
      });
      return;
    }

    onProgress?.({
      downloadedBytes,
      totalBytes,
      percent: 100,
    });
  });
}

export async function relaunchApp(): Promise<void> {
  await relaunch();
}

export function formatUpdateDate(date?: string): string | null {
  if (!date) return null;
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function summarizeUpdateBody(body?: string): string | null {
  const normalized = body?.trim();
  if (!normalized) return null;
  const compact = normalized.replace(/\s+/g, " ");
  return compact.length > 180 ? `${compact.slice(0, 177)}...` : compact;
}
