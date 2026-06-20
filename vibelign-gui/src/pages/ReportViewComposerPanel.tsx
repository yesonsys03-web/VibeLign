import type { ReactNode } from "react";

import { ReportComposer } from "../components/plan-doc/ReportComposer";
import type { ReportComposerReviewRequest } from "../components/plan-doc/useReportComposerGeneration";

type ReportViewComposerPanelProps = {
  readonly reportFor: string;
  readonly projectDir: string;
  readonly fromDoc: boolean;
  readonly onBack: () => void;
  readonly onReviewRequest: ReportComposerReviewRequest;
};

export function ReportViewComposerPanel({
  reportFor,
  projectDir,
  fromDoc,
  onBack,
  onReviewRequest,
}: ReportViewComposerPanelProps): ReactNode {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "16px 20px", minHeight: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <button type="button" className="nav-tab" onClick={onBack}>
          ← 목록으로
        </button>
        <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>📄 보고서 작성</h2>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReportComposer
          key={`${reportFor}:${fromDoc ? "doc" : "plan"}`}
          planPath={reportFor}
          cwd={projectDir}
          layout="inline"
          defaultType={fromDoc ? "doc" : "work"}
          onClose={onBack}
          onReviewRequest={onReviewRequest}
        />
      </div>
    </div>
  );
}
