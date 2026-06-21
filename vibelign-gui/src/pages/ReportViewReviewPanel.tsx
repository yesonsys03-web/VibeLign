// === ANCHOR: REPORTVIEWREVIEWPANEL_START ===
import type { ReactNode } from "react";

import { ReportDiffReview } from "../components/report-review/ReportDiffReview";
import type { EmitPayload } from "../lib/vib/reportModel";

type ReportViewReviewPanelProps = {
  readonly payload: EmitPayload;
  readonly onConfirm: (rejectBlocks: [number, number][]) => void;
  readonly onCancel: () => void;
};

// === ANCHOR: REPORTVIEWREVIEWPANEL_REPORTVIEWREVIEWPANEL_START ===
export function ReportViewReviewPanel({ payload, onConfirm, onCancel }: ReportViewReviewPanelProps): ReactNode {
  return (
    <div style={{ height: "100%", overflow: "auto", padding: "16px 20px" }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>📝 다듬기 검토</h2>
      <p style={{ fontSize: 13, color: "#666", margin: "0 0 8px" }}>
        AI가 다듬은 문장을 블록마다 확인하고 수락/거부하세요. 숫자가 바뀐 블록은 자동으로 원문이 유지됩니다.
      </p>
      <ReportDiffReview payload={payload} onConfirm={onConfirm} onCancel={onCancel} />
    </div>
  );
}
// === ANCHOR: REPORTVIEWREVIEWPANEL_REPORTVIEWREVIEWPANEL_END ===
// === ANCHOR: REPORTVIEWREVIEWPANEL_END ===
