// === ANCHOR: ONBOARDINGCLAUDESETUP_START ===
import { useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  addClaudeToUserPath,
  getOnboardingLogs,
  getOnboardingSnapshot,
  listenOnboardingProgress,
  retryOnboardingVerification,
  startNativeInstall,
  startOnboardingLoginProbe,
  uninstallClaudeCode,
  type OnboardingProgressEvent,
  type OnboardingSnapshot,
} from "../../lib/vib";

// 설치/검증/로그인 등 백그라운드 작업이 도는 동안의 상태들. 이 동안 로그를 1초마다 폴링한다.
const ACTIVE_STATES = new Set<string>([
  "installing_native",
  "installing_wsl",
  "verifying_shells",
  "probing_login",
  "diagnosing",
]);
// 버튼으로 직접 실행할 수 있는 nextAction 들.
const PRIMARY_ACTIONS = new Set<string>([
  "start_install",
  "install_git",
  "retry",
  "retry_with_cmd",
  "open_manual_steps",
  "add_to_path",
  "start_login",
]);

// === ANCHOR: ONBOARDINGCLAUDESETUP_ONBOARDINGCLAUDESETUP_START ===
export function OnboardingClaudeSetup() {
  const [snapshot, setSnapshot] = useState<OnboardingSnapshot | null>(null);
  const [progress, setProgress] = useState<OnboardingProgressEvent | null>(null);
  const [logs, setLogs] = useState("");
  const [logsOpen, setLogsOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  // 현재 스냅샷 로드 + 진행 이벤트 구독(이벤트마다 스냅샷 새로고침).
  useEffect(() => {
    let active = true;
    let unlisten: (() => void) | undefined;
    getOnboardingSnapshot().then((s) => { if (active) setSnapshot(s); }).catch(() => undefined);
    listenOnboardingProgress((event) => {
      if (!active) return;
      setProgress(event);
      getOnboardingSnapshot().then((s) => { if (active) setSnapshot(s); }).catch(() => undefined);
    })
      .then((fn) => { unlisten = fn; })
      .catch(() => undefined);
    return () => { active = false; unlisten?.(); };
  }, []);

  // 활성 단계에서는 설치 스크립트의 실시간 로그를 1초마다 폴링해서 보여준다.
  useEffect(() => {
    const isActive = !!snapshot && ACTIVE_STATES.has(snapshot.state);
    if (!isActive && !snapshot?.logsAvailable) {
      return;
    }
    let cancelled = false;
    const fetchLogs = () => {
      getOnboardingLogs()
        .then((r) => { if (!cancelled) setLogs(r.text ?? ""); })
        .catch(() => undefined);
    };
    fetchLogs();
    if (isActive || snapshot?.lastError) {
      setLogsOpen(true);
    }
    let intervalId: ReturnType<typeof setInterval> | undefined;
    if (isActive) {
      intervalId = setInterval(fetchLogs, 1000);
    }
    return () => { cancelled = true; if (intervalId) clearInterval(intervalId); };
  }, [snapshot?.state, snapshot?.logsAvailable, snapshot?.lastError, progress?.status, progress?.stepId]);

  async function runAction(action: string) {
    setBusy(true);
    try {
      if (action === "start_install") {
        // 공식 설치는 PowerShell 경로가 기본(curl 의존 없음). macOS 는 백엔드가 path_kind 를 무시한다.
        const kind = snapshot?.installPathKind === "native-cmd" ? "native-cmd" : "native-powershell";
        setSnapshot(await startNativeInstall(kind));
      } else if (action === "retry_with_cmd") {
        setSnapshot(await startNativeInstall("native-cmd"));
      } else if (action === "retry") {
        setSnapshot(await retryOnboardingVerification());
      } else if (action === "add_to_path") {
        setSnapshot(await addClaudeToUserPath());
      } else if (action === "start_login") {
        setSnapshot(await startOnboardingLoginProbe());
      } else if (action === "install_git") {
        await openUrl("https://git-scm.com/download/win").catch(() => undefined);
        const refreshed = await getOnboardingSnapshot().catch(() => null);
        if (refreshed) setSnapshot(refreshed);
      } else if (action === "open_manual_steps") {
        const hint = snapshot?.lastError?.code === "path_not_configured" ? snapshot.lastError.detail?.trim() : "";
        if (hint) {
          await navigator.clipboard.writeText(hint).catch(() => undefined);
        }
        await openUrl("https://docs.anthropic.com/en/docs/claude-code/setup").catch(() => undefined);
      }
    } finally {
      setBusy(false);
    }
  }

  async function uninstall() {
    const ok = window.confirm(
      "Claude Code 를 완전히 삭제할까요?\n\n바이너리·설정·PATH 항목까지 모두 정리해요. 되돌릴 수 없어요.",
    );
    if (!ok) {
      return;
    }
    setBusy(true);
    try {
      setSnapshot(await uninstallClaudeCode("all"));
    } finally {
      setBusy(false);
    }
  }

  if (!snapshot) {
    return (
      <div style={{ width: "min(720px, 100%)", marginTop: 12, fontSize: 12, color: "#555" }}>
        Claude Code 상태를 확인하는 중이에요…
      </div>
    );
  }

  const primaryEnabled = PRIMARY_ACTIONS.has(snapshot.nextAction);
  const showUninstall = (snapshot.os === "windows" || snapshot.os === "macos")
    && snapshot.state !== "idle"
    && snapshot.state !== "diagnosing";

  return (
    <div
      style={{
        width: "min(720px, 100%)",
        marginTop: 12,
        border: "2px solid #1A1A1A",
        background: snapshot.state === "success" ? "#F2FFF7" : "#FFF8E8",
        padding: "12px 16px",
        boxShadow: "4px 4px 0 #1A1A1A",
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 800, color: "#666", marginBottom: 5 }}>CLAUDE CODE 설치/관리</div>
      <div style={{ fontSize: 14, fontWeight: 800, color: "#1A1A1A", marginBottom: 4 }}>{snapshot.headline}</div>
      {snapshot.detail && (
        <div style={{ fontSize: 11, color: "#555", lineHeight: 1.6, marginBottom: 8 }}>{snapshot.detail}</div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: progress || snapshot.lastError ? 8 : 0 }}>
        <span className="badge" style={{ fontSize: 10 }}>state: {snapshot.state}</span>
        <span className="badge" style={{ fontSize: 10 }}>os: {snapshot.os}</span>
        <span className="badge" style={{ fontSize: 10 }}>path: {snapshot.installPathKind}</span>
        <span className="badge" style={{ fontSize: 10 }}>next: {snapshot.nextAction}</span>
      </div>

      {progress && (
        <div style={{ fontSize: 11, color: "#555", marginBottom: snapshot.lastError ? 6 : 8 }}>
          진행 상태: {progress.phase} / {progress.stepId} / {progress.status} — {progress.message}
        </div>
      )}

      {snapshot.lastError && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 11, color: "#A14B00", lineHeight: 1.55, fontWeight: 700, marginBottom: snapshot.lastError.detail ? 4 : 0 }}>
            {snapshot.lastError.summary}
          </div>
          {snapshot.lastError.detail && (
            <div style={{ fontSize: 10, color: "#8A5A00", lineHeight: 1.6 }}>{snapshot.lastError.detail}</div>
          )}
        </div>
      )}

      {(logs.trim() || snapshot.logsAvailable || ACTIVE_STATES.has(snapshot.state)) && (
        <div style={{ marginBottom: primaryEnabled || showUninstall ? 8 : 0 }}>
          <button
            type="button"
            onClick={() => setLogsOpen((open) => !open)}
            style={{ fontSize: 10, fontWeight: 700, padding: "4px 10px", border: "2px solid #1A1A1A", background: "#fff", color: "#1A1A1A", cursor: "pointer", marginBottom: logsOpen ? 8 : 0 }}
          >
            {logsOpen ? "설치 로그 숨기기" : "설치 로그 보기"}
          </button>
          {logsOpen && (
            <div
              role="log"
              style={{
                border: "2px solid #1A1A1A",
                background: "#111",
                color: "#4DFF91",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: 10,
                lineHeight: 1.6,
                padding: "10px 12px",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 420,
                minHeight: 200,
                overflowY: "auto",
              }}
            >
              {logs || "로그 수집 중… (설치 스크립트가 첫 줄을 내보낼 때까지 기다리는 중이에요)"}
            </div>
          )}
        </div>
      )}

      {(primaryEnabled || showUninstall) && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {primaryEnabled && snapshot.primaryButtonLabel && (
            <button
              type="button"
              onClick={() => runAction(snapshot.nextAction)}
              disabled={busy}
              style={{ fontSize: 11, fontWeight: 700, padding: "6px 14px", border: "2px solid #1A1A1A", background: busy ? "#DDD" : "#F5621E", color: busy ? "#666" : "#fff", cursor: busy ? "default" : "pointer" }}
            >
              {busy ? "처리 중..." : snapshot.primaryButtonLabel}
            </button>
          )}
          {showUninstall && (
            <button
              type="button"
              onClick={uninstall}
              disabled={busy}
              style={{ fontSize: 10, fontWeight: 700, padding: "6px 12px", border: "2px solid #A14B00", background: "#fff", color: "#A14B00", cursor: busy ? "default" : "pointer" }}
            >
              {snapshot.os === "macos" ? "Claude Code 삭제" : "전체 삭제"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
// === ANCHOR: ONBOARDINGCLAUDESETUP_ONBOARDINGCLAUDESETUP_END ===
// === ANCHOR: ONBOARDINGCLAUDESETUP_END ===
