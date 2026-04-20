// === ANCHOR: APPUPDATE_START ===
import { relaunch } from "@tauri-apps/plugin-process";
import { check, type DownloadEvent, type Update } from "@tauri-apps/plugin-updater";

export interface AppUpdateProgress {
  downloadedBytes: number;
  totalBytes: number | null;
  percent: number | null;
}

// === ANCHOR: APPUPDATE_SHOULDCHECKFORUPDATES_START ===
export function shouldCheckForUpdates(): boolean {
  return !import.meta.env.DEV && import.meta.env.VITE_APP_UPDATER_ENABLED === "true";
}
// === ANCHOR: APPUPDATE_SHOULDCHECKFORUPDATES_END ===

// === ANCHOR: APPUPDATE_CHECKFORAPPUPDATE_START ===
export async function checkForAppUpdate(): Promise<Update | null> {
  return check();
}
// === ANCHOR: APPUPDATE_CHECKFORAPPUPDATE_END ===

// === ANCHOR: APPUPDATE_INSTALLAPPUPDATE_START ===
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
// === ANCHOR: APPUPDATE_INSTALLAPPUPDATE_END ===

// === ANCHOR: APPUPDATE_RELAUNCHAPP_START ===
export async function relaunchApp(): Promise<void> {
  await relaunch();
}
// === ANCHOR: APPUPDATE_RELAUNCHAPP_END ===

// === ANCHOR: APPUPDATE_FORMATUPDATEDATE_START ===
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
// === ANCHOR: APPUPDATE_FORMATUPDATEDATE_END ===

// === ANCHOR: APPUPDATE_SUMMARIZEUPDATEBODY_START ===
export function summarizeUpdateBody(body?: string): string | null {
  const normalized = body?.trim();
  if (!normalized) return null;
  const compact = normalized.replace(/\s+/g, " ");
  return compact.length > 180 ? `${compact.slice(0, 177)}...` : compact;
}
// === ANCHOR: APPUPDATE_SUMMARIZEUPDATEBODY_END ===
// === ANCHOR: APPUPDATE_END ===
