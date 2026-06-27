// === ANCHOR: ONBOARDING_INTRO_VIDEO_START ===
import { openUrl } from "@tauri-apps/plugin-opener";

import type { CSSProperties, ReactElement } from "react";

const INTRO_VIDEO_URL =
  "https://www.dropbox.com/scl/fi/oogxeoym0q75v3myii1ul/VibeLign_video.mp4?rlkey=shmym4gtk6awdfl1q3e45l91q&st=jtfq13a8&raw=1";
const THREADS_PROFILE_URL = "https://www.threads.com/@jongjatdon";

const sectionStyle: CSSProperties = {
  width: "min(860px, 100%)",
  display: "grid",
  gap: 8,
  padding: 10,
  border: "2px solid #1A1A1A",
  boxShadow: "4px 4px 0 #1A1A1A",
  background: "#FFFFFF",
};

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  alignItems: "baseline",
  flexWrap: "wrap",
};

const titleStyle: CSSProperties = {
  appearance: "none",
  border: 0,
  padding: 0,
  background: "transparent",
  fontSize: 12,
  fontWeight: 900,
  color: "#1A1A1A",
  cursor: "pointer",
  textAlign: "left",
  textDecoration: "underline",
};

const statusStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 800,
  color: "#555",
};

const videoStyle: CSSProperties = {
  display: "block",
  width: "100%",
  aspectRatio: "16 / 9",
  height: "auto",
  background: "#1A1A1A",
  border: "2px solid #1A1A1A",
  objectFit: "contain",
};

function logOpenProfileError(error: unknown): void {
  if (error instanceof Error) {
    console.warn("Failed to open Threads profile", error.message);
    return;
  }

  console.warn("Failed to open Threads profile", String(error));
}

export function OnboardingIntroVideo(): ReactElement {
  return (
    <section aria-label="VibeLign 온보딩 영상" style={sectionStyle}>
      <div style={headerStyle}>
        <button
          onClick={() => {
            void openUrl(THREADS_PROFILE_URL).catch(logOpenProfileError);
          }}
          style={titleStyle}
          title="Threads 프로필 열기"
          type="button"
        >
          VibeLign 시작 영상
        </button>
        <span style={statusStyle}>자동 반복 재생</span>
      </div>
      <video
        aria-label="VibeLign 온보딩 영상 플레이어"
        autoPlay
        controls
        loop
        muted
        playsInline
        preload="metadata"
        src={INTRO_VIDEO_URL}
        style={videoStyle}
      />
    </section>
  );
}
// === ANCHOR: ONBOARDING_INTRO_VIDEO_END ===
