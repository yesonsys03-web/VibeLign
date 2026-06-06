// === ANCHOR: ONBOARDINGSTARTPROGRESS_START ===
interface OnboardingStartProgressProps {
  readonly labels: readonly string[];
  readonly statusMessage: string | null;
}

// === ANCHOR: ONBOARDINGSTARTPROGRESS_ONBOARDINGSTARTPROGRESS_START ===
export function OnboardingStartProgress({
  labels,
  statusMessage,
}: OnboardingStartProgressProps) {
  if (labels.length === 0 && !statusMessage) {
    return null;
  }

  return (
    <div style={{ width: "100%", maxWidth: 720, display: "grid", gap: 6, marginTop: -6 }}>
      {labels.map((label) => (
        <div key={label} style={{ fontSize: 12, fontWeight: 800, color: "#1A1A1A" }}>
          {label}
        </div>
      ))}
      {statusMessage && (
        <div role="status" style={{ fontSize: 12, fontWeight: 800, color: "#1A1A1A" }}>
          {statusMessage}
        </div>
      )}
    </div>
  );
}
// === ANCHOR: ONBOARDINGSTARTPROGRESS_ONBOARDINGSTARTPROGRESS_END ===
// === ANCHOR: ONBOARDINGSTARTPROGRESS_END ===
