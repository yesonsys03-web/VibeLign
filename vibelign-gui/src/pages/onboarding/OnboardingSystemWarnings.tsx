// === ANCHOR: ONBOARDINGSYSTEMWARNINGS_START ===
import { openUrl } from "@tauri-apps/plugin-opener";

import type { OnboardingSnapshot } from "../../lib/vib";

interface OnboardingSystemWarningsProps {
  readonly gitInstalled: boolean | null;
  readonly xcodeCltInstalled: boolean | null;
  readonly onboardingSnapshot: OnboardingSnapshot | null;
}

// === ANCHOR: ONBOARDINGSYSTEMWARNINGS_ONBOARDINGSYSTEMWARNINGS_START ===
export function OnboardingSystemWarnings({
  gitInstalled,
  xcodeCltInstalled,
  onboardingSnapshot,
}: OnboardingSystemWarningsProps) {
  return (
    <section>
      {gitInstalled === false && (() => {
        const ua = navigator.userAgent.toLowerCase();
        const isWin = ua.includes("win");
        const isMac = ua.includes("mac");
        const installCmd = isWin ? null : isMac ? "brew install git" : "sudo apt install git";
        const downloadUrl = isWin
          ? "https://git-scm.com/download/win"
          : isMac
          ? "https://git-scm.com/download/mac"
          : "https://git-scm.com/download/linux";
        return (
          <div style={{ border: "2px solid #FFD166", background: "#FFD16611", padding: "10px 14px", marginBottom: 8, fontSize: 11 }}>
            <div style={{ fontWeight: 800, color: "#B8860B", marginBottom: 6 }}>⚠ Git이 설치되지 않았어요</div>
            <div style={{ color: "#555", marginBottom: 8, lineHeight: 1.55 }}>
              일부 기능(시크릿 검사 등)에 Git이 필요해요. 핵심 기능은 Git 없이도 사용 가능합니다.
            </div>
            {installCmd && (
              <div style={{ fontFamily: "IBM Plex Mono, monospace", background: "#1A1A1A", color: "#4DFF91", padding: "6px 10px", fontSize: 10, marginBottom: 8 }}>
                $ {installCmd}
              </div>
            )}
            <button
              type="button"
              onClick={() => {
                void openUrl(downloadUrl).catch((error: unknown) => {
                  console.warn("Failed to open Git download URL", error);
                });
              }}
              style={{ fontSize: 10, fontWeight: 700, padding: "4px 12px", border: "2px solid #1A1A1A", background: "#FFD166", color: "#1A1A1A", cursor: "pointer" }}
            >
              Git 다운로드 ↗
            </button>
          </div>
        );
      })()}

      {onboardingSnapshot?.os === "macos" && xcodeCltInstalled === false && (
        <div style={{ border: "2px solid #FFD166", background: "#FFD16611", padding: "10px 14px", marginBottom: 8, fontSize: 11 }}>
          <div style={{ fontWeight: 800, color: "#B8860B", marginBottom: 6 }}>⚠ Xcode Command Line Tools 가 없을 수 있어요</div>
          <div style={{ color: "#555", marginBottom: 8, lineHeight: 1.55 }}>
            설치가 잘 되면 무시해도 괜찮아요. 만약 install.sh 가 `git` 또는 `curl` 을 못 찾으면 아래 명령을 터미널에서 한 번 실행해 주세요.
          </div>
          <div style={{ fontFamily: "IBM Plex Mono, monospace", background: "#1A1A1A", color: "#4DFF91", padding: "6px 10px", fontSize: 10 }}>
            $ xcode-select --install
          </div>
        </div>
      )}
    </section>
  );
}
// === ANCHOR: ONBOARDINGSYSTEMWARNINGS_ONBOARDINGSYSTEMWARNINGS_END ===
// === ANCHOR: ONBOARDINGSYSTEMWARNINGS_END ===
