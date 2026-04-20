// === ANCHOR: UPDATEBANNER_START ===
import { useEffect, useMemo, useState } from "react";
import type { Update } from "@tauri-apps/plugin-updater";
import {
  checkForAppUpdate,
  formatUpdateDate,
  installAppUpdate,
  relaunchApp,
  shouldCheckForUpdates,
  summarizeUpdateBody,
  type AppUpdateProgress,
} from "../lib/appUpdate";

type BannerStatus =
  | "idle"
  | "checking"
  | "available"
  | "installing"
  | "ready_to_restart"
  | "error"
  | "dismissed";

// === ANCHOR: UPDATEBANNER_PROGRESSLABEL_START ===
function progressLabel(progress: AppUpdateProgress | null): string {
  if (!progress) return "다운로드 준비 중...";
  if (typeof progress.percent === "number") return `다운로드 중... ${progress.percent}%`;
  if (progress.downloadedBytes > 0) return `다운로드 중... ${Math.round(progress.downloadedBytes / 1024)}KB`;
  return "다운로드 중...";
}
// === ANCHOR: UPDATEBANNER_PROGRESSLABEL_END ===

export default function UpdateBanner() {
  const [status, setStatus] = useState<BannerStatus>("idle");
  const [update, setUpdate] = useState<Update | null>(null);
  const [progress, setProgress] = useState<AppUpdateProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shouldCheckForUpdates()) return;

    let cancelled = false;

    // === ANCHOR: UPDATEBANNER_RUN_START ===
    async function run() {
      setStatus("checking");
      setError(null);
      try {
        const next = await checkForAppUpdate();
        if (cancelled) {
          await next?.close();
          return;
        }
        if (!next) {
          setStatus("idle");
          return;
        }
        setUpdate(next);
        setStatus("available");
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        if (/updater|endpoint|signature|pubkey|configured/i.test(message)) {
          setStatus("idle");
          return;
        }
        setError(message);
        setStatus("error");
      }
    }
    // === ANCHOR: UPDATEBANNER_RUN_END ===

    void run();

    return () => {
      cancelled = true;
      void update?.close().catch(() => {});
    };
  }, []);

  const updateSummary = useMemo(() => {
    if (!update) return null;
    return {
      version: update.version,
      currentVersion: update.currentVersion,
      date: formatUpdateDate(update.date),
      body: summarizeUpdateBody(update.body),
    };
  }, [update]);

  // === ANCHOR: UPDATEBANNER_HANDLEINSTALL_START ===
  async function handleInstall() {
    if (!update) return;
    setStatus("installing");
    setProgress(null);
    setError(null);
    try {
      await installAppUpdate(update, setProgress);
      setStatus("ready_to_restart");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }
  // === ANCHOR: UPDATEBANNER_HANDLEINSTALL_END ===

  // === ANCHOR: UPDATEBANNER_HANDLEDISMISS_START ===
  async function handleDismiss() {
    await update?.close().catch(() => {});
    setUpdate(null);
    setProgress(null);
    setError(null);
    setStatus("dismissed");
  }
  // === ANCHOR: UPDATEBANNER_HANDLEDISMISS_END ===

  // === ANCHOR: UPDATEBANNER_HANDLERELAUNCH_START ===
  async function handleRelaunch() {
    try {
      await relaunchApp();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }
  // === ANCHOR: UPDATEBANNER_HANDLERELAUNCH_END ===

  if (status === "idle" || status === "dismissed" || status === "checking") {
    return null;
  }

  return (
    <div
      style={{
        borderBottom: "2px solid #1A1A1A",
        background: status === "error" ? "#3A1717" : "#FFF4CC",
        color: status === "error" ? "#FFD7D7" : "#1A1A1A",
        padding: "10px 14px",
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        fontSize: 11,
        fontWeight: 700,
      }}
    >
      <span style={{ letterSpacing: 0.8, textTransform: "uppercase" }}>
        {status === "available" && "UPDATE AVAILABLE"}
        {status === "installing" && "INSTALLING UPDATE"}
        {status === "ready_to_restart" && "UPDATE READY"}
        {status === "error" && "UPDATE ERROR"}
      </span>

      {status !== "error" && updateSummary && (
        <span style={{ fontWeight: 500 }}>
          v{updateSummary.currentVersion} → v{updateSummary.version}
          {updateSummary.date ? ` · ${updateSummary.date}` : ""}
          {updateSummary.body ? ` · ${updateSummary.body}` : ""}
        </span>
      )}

      {status === "installing" && (
        <span style={{ fontWeight: 500 }}>{progressLabel(progress)}</span>
      )}

      {status === "ready_to_restart" && (
        <span style={{ fontWeight: 500 }}>설치가 끝났어요. 다시 시작하면 새 버전이 적용됩니다.</span>
      )}

      {status === "error" && error && (
        <span style={{ fontWeight: 500, wordBreak: "break-word" }}>{error}</span>
      )}

      <div style={{ flex: 1 }} />

      {status === "available" && (
        <>
          <button className="nav-tab active" onClick={() => void handleInstall()}>
            지금 설치
          </button>
          <button className="nav-tab" onClick={() => void handleDismiss()}>
            나중에
          </button>
        </>
      )}

      {status === "ready_to_restart" && (
        <button className="nav-tab active" onClick={() => void handleRelaunch()}>
          지금 재시작
        </button>
      )}

      {status === "error" && (
        <button className="nav-tab" onClick={() => void handleDismiss()}>
          닫기
        </button>
      )}
    </div>
  );
}
// === ANCHOR: UPDATEBANNER_END ===
