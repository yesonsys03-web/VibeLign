import { designChipState } from "../../lib/nav/designChip";
import type { DesignJobStatus } from "../../lib/design-preview/useDesignJob";
import type { Page } from "../../lib/nav/stages";

interface Props {
  readonly status: DesignJobStatus;
  readonly page: Page;
  readonly onOpen: () => void;
}

export function DesignJobChip({ status, page, onOpen }: Props) {
  const s = designChipState(status, page);
  if (!s.visible) return null;
  const bg = s.tone === "error" ? "#FEE2E2" : s.tone === "done" ? "#DCFCE7" : "#F5F1E3";
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        margin: "0 12px 8px",
        padding: "6px 12px",
        border: "2px solid #1A1A1A",
        background: bg,
        fontSize: 13,
        fontWeight: 800,
        cursor: "pointer",
        alignSelf: "flex-start",
      }}
    >
      {s.tone === "busy" && <span className="spinner" />}
      {s.label}
    </button>
  );
}
