import type { CSSProperties, ReactNode } from "react";

import { ReportComposerPreview } from "./ReportComposerPreview";
import {
  openResultPath,
  primaryBtn,
  secondaryBtn,
} from "./ReportComposerExportBox";
import type { ReportComposerResultState } from "./useReportComposerGeneration";

type ReportComposerLayoutProps = {
  readonly cwd: string;
  readonly inline: boolean;
  readonly controls: ReactNode;
  readonly exportBox: ReactNode;
  readonly result: ReportComposerResultState | null;
  readonly exportedPath: string | null;
  readonly openErr: string | null;
  readonly onOpenErr: (message: string | null) => void;
  readonly onClose: () => void;
};

export function ReportComposerLayout({
  cwd,
  inline,
  controls,
  exportBox,
  result,
  exportedPath,
  openErr,
  onOpenErr,
  onClose,
}: ReportComposerLayoutProps): ReactNode {
  if (inline) {
    return (
      <div style={{ display: "flex", height: "100%", gap: 16, minHeight: 0 }}>
        <div style={inlineOptionsPane}>
          {controls}
          {exportBox}
        </div>
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <ReportComposerPreview cwd={cwd} result={result} fillHeight />
        </div>
      </div>
    );
  }

  return (
    <div style={box}>
      <div style={header}>
        <span>📄 보고서로 내보내기</span>
        <button type="button" onClick={onClose} aria-label="닫기" style={iconBtn}>
          ✕
        </button>
      </div>

      <div style={contentArea}>
        {controls}
        <ReportComposerPreview cwd={cwd} result={result} fillHeight={false} />
        {exportBox}
      </div>

      <div style={footer}>
        {openErr && (
          <span role="alert" style={{ color: "#9B1B1B", fontSize: 12, marginRight: "auto" }}>
            {openErr}
          </span>
        )}
        {result && result.ok && (
          <button
            type="button"
            onClick={() => {
              openResultPath(result, exportedPath, onOpenErr);
            }}
            style={primaryBtn}
          >
            파일 열기
          </button>
        )}
        <button type="button" onClick={onClose} style={secondaryBtn}>
          닫기
        </button>
      </div>
    </div>
  );
}

const box: CSSProperties = {
  background: "#FEFBF0",
  width: "min(680px, 92vw)",
  maxHeight: "88vh",
  display: "flex",
  flexDirection: "column",
  borderRadius: 8,
  overflow: "hidden",
};
const header: CSSProperties = {
  background: "#1A1A1A",
  color: "#FEFBF0",
  padding: "12px 16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontWeight: 700,
};
const contentArea: CSSProperties = { padding: 16, overflow: "auto" };
const inlineOptionsPane: CSSProperties = {
  width: 300,
  flexShrink: 0,
  overflow: "auto",
  padding: "4px 16px 16px 4px",
  borderRight: "1px solid #e5e0d0",
};
const footer: CSSProperties = {
  padding: 12,
  display: "flex",
  gap: 8,
  justifyContent: "flex-end",
  borderTop: "1px solid #e5e0d0",
};
const iconBtn: CSSProperties = {
  background: "transparent",
  color: "#FEFBF0",
  border: "none",
  cursor: "pointer",
  fontSize: 16,
};
