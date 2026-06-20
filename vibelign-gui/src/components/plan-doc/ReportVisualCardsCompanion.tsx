// === ANCHOR: REPORT_VISUAL_CARDS_COMPANION_START ===
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import type { ReportType } from "../../lib/vib/report";
import {
  requestReportVisualCards,
  type ReportVisualCard,
  type ReportVisualCardsPayload,
} from "../../lib/vib/reportVisualCards";
import { ReportVisualCardsPanel } from "./ReportVisualCardsPanel";

type ReportVisualCardsCompanionProps = {
  readonly cwd: string;
  readonly planPath: string;
  readonly reportType: ReportType;
};

export function ReportVisualCardsCompanion({
  cwd,
  planPath,
  reportType,
}: ReportVisualCardsCompanionProps): ReactNode {
  const [payload, setPayload] = useState<ReportVisualCardsPayload | null>(null);
  const [approvedCards, setApprovedCards] = useState<readonly ReportVisualCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPayload(null);
    setApprovedCards([]);
    setError(null);
  }, [planPath, reportType]);

  const requestCards = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    const result = await requestReportVisualCards(cwd, planPath, reportType);
    setLoading(false);
    if (!result.ok) {
      setPayload(null);
      setApprovedCards([]);
      setError(result.error);
      return;
    }
    setPayload(result.payload);
  };

  return (
    <section aria-label="카드뉴스 companion 요청" style={shell}>
      <div style={header}>
        <div>
          <div style={eyebrow}>companion</div>
          <h3 style={title}>카드뉴스 출력</h3>
        </div>
        <button type="button" onClick={() => void requestCards()} disabled={loading} style={button}>
          {loading ? "요청 중..." : "카드뉴스 초안 만들기"}
        </button>
      </div>
      <p style={copy}>보고서 메시지를 3-6장 카드로 나누고, 한국어 문구는 편집 가능한 오버레이로 유지합니다.</p>
      {error !== null && <p role="alert" style={errorText}>{error}</p>}
      {payload !== null && (
        <>
          <p style={countText}>승인된 카드 {approvedCards.length}개</p>
          <ReportVisualCardsPanel payload={payload} onExportChange={setApprovedCards} />
        </>
      )}
    </section>
  );
}

const shell: CSSProperties = { border: "2px solid #1A1A1A", background: "#FEFBF0", padding: 10, marginTop: 12, boxShadow: "2px 2px 0 #1A1A1A" };
const header: CSSProperties = { display: "flex", alignItems: "start", justifyContent: "space-between", gap: 8 };
const eyebrow: CSSProperties = { fontSize: 11, fontWeight: 800, color: "#999999" };
const title: CSSProperties = { margin: 0, fontSize: 16, lineHeight: 1.2 };
const copy: CSSProperties = { margin: "8px 0 0", fontSize: 12, lineHeight: 1.5 };
const button: CSSProperties = { border: "2px solid #1A1A1A", background: "#F5621E", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer", boxShadow: "2px 2px 0 #1A1A1A" };
const errorText: CSSProperties = { margin: "8px 0 0", color: "#9B1B1B", fontSize: 12 };
const countText: CSSProperties = { margin: "8px 0", fontSize: 12, fontWeight: 800 };
// === ANCHOR: REPORT_VISUAL_CARDS_COMPANION_END ===
