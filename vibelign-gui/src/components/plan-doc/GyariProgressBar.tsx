// === ANCHOR: GYARI_PROGRESS_BAR_START ===
import type { CSSProperties } from "react";

/** Shared START→GOAL progress track with the 갸리 자동차 loader, used by card-news generation
 *  and AI assistance so long waits stay lively. `pct` positions the car (0–100). */
export function GyariProgressBar({
  pct,
  label,
  ariaLabel,
}: {
  readonly pct: number;
  readonly label: string;
  readonly ariaLabel: string;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div aria-label={ariaLabel} style={progressWrap}>
      <div style={progressTrack}>
        <span style={{ ...progressMarker, left: 8 }} aria-hidden>START</span>
        <span style={{ ...progressMarker, right: 8 }} aria-hidden>🏁 GOAL</span>
        <span
          className="gyari-loader"
          style={{ position: "absolute", left: `calc(${clamped}% - 26px)`, transition: "left .5s ease", zIndex: 1 }}
          aria-hidden
        />
      </div>
      <p style={progressLabel}>{label}...</p>
    </div>
  );
}

const progressWrap: CSSProperties = { marginTop: 10 };
const progressTrack: CSSProperties = { position: "relative", height: 56, border: "2px solid #1A1A1A", background: "#FEFBF0", overflow: "hidden" };
const progressLabel: CSSProperties = { margin: "4px 0 0", fontSize: 12, fontWeight: 800 };
const progressMarker: CSSProperties = { position: "absolute", top: "50%", transform: "translateY(-50%)", fontSize: 11, fontWeight: 900, letterSpacing: "0.06em", color: "#B7AE9E" };
// === ANCHOR: GYARI_PROGRESS_BAR_END ===
