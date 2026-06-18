// === ANCHOR: EXPORTREPORTMODAL_START ===
import { type CSSProperties } from "react";
import type { ReportType } from "../../lib/vib/report";
import type { ReportFontSizes } from "../../lib/vib/reportFontSizes";
import { ReportComposer } from "./ReportComposer";

type Format = "html" | "pdf" | "docx" | "pptx";

export interface ExportReportModalProps {
  open: boolean;
  planPath: string;
  cwd: string;
  onClose: () => void;
  /** 제공되고 'AI 다듬기'가 켜져 있으면, 인라인 생성 대신 블록 diff 검토 화면으로 보낸다. */
  onReviewRequest?: (
    reportType: ReportType,
    format: Format,
    theme: string,
    author: string,
    pageNumbers: boolean,
    fontSizes: ReportFontSizes,
  ) => void;
  /** 모달이 열릴 때 초기 선택될 보고서 종류(문서 우클릭 진입 시 "doc"). 기본 "work". */
  defaultType?: ReportType;
}

// === ANCHOR: EXPORTREPORTMODAL_EXPORTREPORTMODAL_START ===
export function ExportReportModal({ open, planPath, cwd, onClose, onReviewRequest, defaultType }: ExportReportModalProps) {
  if (!open) return null;
  return (
    <div role="dialog" aria-label="보고서로 내보내기" style={overlay}>
      <ReportComposer
        planPath={planPath}
        cwd={cwd}
        layout="modal"
        onClose={onClose}
        onReviewRequest={onReviewRequest}
        defaultType={defaultType}
      />
    </div>
  );
}
// === ANCHOR: EXPORTREPORTMODAL_EXPORTREPORTMODAL_END ===

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.45)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};
// === ANCHOR: EXPORTREPORTMODAL_END ===
