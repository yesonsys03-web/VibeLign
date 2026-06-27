// === ANCHOR: REPORTQUALITYSCOREPREVIEW_START ===
import type { CSSProperties } from "react";

import type { ReportQualityStatus } from "../../lib/vib/reportQuality";
import type { ReportQualityScorePreview } from "./reportQualityScoreProjection";

export type ReportQualityScorePreviewProps = {
  readonly currentScore: number;
  readonly preview: ReportQualityScorePreview;
};

// === ANCHOR: REPORTQUALITYSCOREPREVIEW_STATUSTEXT_START ===
function statusText(status: ReportQualityStatus): string {
  switch (status) {
    case "ok":
      return "생성 가능";
    case "warn":
      return "검토 필요";
    case "block":
      return "생성 중단";
    default:
      return status satisfies never;
  }
}
// === ANCHOR: REPORTQUALITYSCOREPREVIEW_STATUSTEXT_END ===

// === ANCHOR: REPORTQUALITYSCOREPREVIEW_REPORTQUALITYSCOREPREVIEWVIEW_START ===
export function ReportQualityScorePreviewView({ currentScore, preview }: ReportQualityScorePreviewProps) {
  const changed = preview.score !== currentScore || preview.addressedCount > 0;
  return (
    <section aria-label="선택 후 재채점" style={box}>
      <div style={label}>선택 후 재채점</div>
      <div style={scoreLine}>
        <strong>{currentScore}점</strong>
        <span aria-hidden="true">→</span>
        <strong>{preview.score}점</strong>
        <span style={statusBadge}>{statusText(preview.status)}</span>
      </div>
      <p aria-live="polite" style={copy}>
        {changed
          ? `선택 반영 ${preview.addressedCount}개, 남은 점검 ${preview.remainingCount}개입니다.`
          : "추천을 선택하거나 답변을 저장하면 점수가 다시 계산됩니다."}
      </p>
    </section>
  );
}
// === ANCHOR: REPORTQUALITYSCOREPREVIEW_REPORTQUALITYSCOREPREVIEWVIEW_END ===

const box: CSSProperties = { border: "2px solid var(--black)", background: "var(--bg)", padding: 10, display: "grid", gap: 6 };
const label: CSSProperties = { fontSize: 11, fontWeight: 900, color: "var(--gray-dark)" };
const scoreLine: CSSProperties = { display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, fontSize: 18, lineHeight: 1.2 };
const statusBadge: CSSProperties = { border: "1px solid var(--black)", background: "var(--white)", padding: "2px 6px", fontSize: 11, fontWeight: 900 };
const copy: CSSProperties = { margin: 0, fontSize: 12, lineHeight: 1.5 };
// === ANCHOR: REPORTQUALITYSCOREPREVIEW_END ===
