// === ANCHOR: REPORTCOMPOSERPREVIEW_START ===
import type { CSSProperties, ReactNode } from "react";

import { PdfPreview } from "./PdfPreview";
import type { ReportComposerResultState } from "./useReportComposerGeneration";

type ReportComposerPreviewProps = {
  readonly cwd: string;
  readonly result: ReportComposerResultState | null;
  readonly fillHeight: boolean;
};

// === ANCHOR: REPORTCOMPOSERPREVIEW_REPORTCOMPOSERPREVIEW_START ===
export function ReportComposerPreview({ cwd, result, fillHeight }: ReportComposerPreviewProps): ReactNode {
  if (result && result.ok && result.kind === "html") {
    return (
      <div style={fillHeight ? filledHtmlBox : htmlBox}>
        <iframe title="보고서 미리보기" srcDoc={result.html} sandbox="" style={fillHeight ? filledFrame : frame} />
        <p style={pathText}>내부 사본: {result.path}</p>
      </div>
    );
  }
  if (result && result.ok && result.kind === "file") {
    if (/\.pdf$/i.test(result.path)) {
      return <PdfReportPreview cwd={cwd} path={result.path} fillHeight={fillHeight} />;
    }
    return <p style={filePathText}>내부 사본: {result.path}</p>;
  }
  return fillHeight ? (
    <div style={emptyPreview}>
      왼쪽에서 옵션을 고르고 '보고서 생성'을 누르면<br />여기에 미리보기가 표시됩니다.
    </div>
  ) : null;
}
// === ANCHOR: REPORTCOMPOSERPREVIEW_REPORTCOMPOSERPREVIEW_END ===

type PdfReportPreviewProps = {
  readonly cwd: string;
  readonly path: string;
  readonly fillHeight: boolean;
};

// === ANCHOR: REPORTCOMPOSERPREVIEW_PDFREPORTPREVIEW_START ===
function PdfReportPreview({ cwd, path, fillHeight }: PdfReportPreviewProps): ReactNode {
  if (fillHeight) {
    return (
      <div style={filledPdfBox}>
        <div style={filledPdfPreview}>
          <PdfPreview cwd={cwd} path={path} />
        </div>
        <p style={pathText}>내부 사본: {path}</p>
      </div>
    );
  }
  return (
    <div style={pdfBox}>
      <div style={pdfPreview}>
        <PdfPreview cwd={cwd} path={path} />
      </div>
      <p style={pathText}>내부 사본: {path}</p>
    </div>
  );
}
// === ANCHOR: REPORTCOMPOSERPREVIEW_PDFREPORTPREVIEW_END ===

const htmlBox: CSSProperties = { marginTop: 12 };
const filledHtmlBox: CSSProperties = { display: "flex", flexDirection: "column", height: "100%" };
const frame: CSSProperties = { width: "100%", height: 420, border: "1px solid #ddd" };
const filledFrame: CSSProperties = { flex: 1, width: "100%", border: "1px solid #ddd", background: "#fff" };
const pathText: CSSProperties = { fontSize: 11, color: "#999", marginTop: 8 };
const filePathText: CSSProperties = { fontSize: 11, color: "#999", marginTop: 12 };
const pdfBox: CSSProperties = { marginTop: 12 };
const pdfPreview: CSSProperties = { height: 420 };
const filledPdfBox: CSSProperties = { display: "flex", flexDirection: "column", height: "100%", minHeight: 0 };
const filledPdfPreview: CSSProperties = { flex: 1, minHeight: 0 };
const emptyPreview: CSSProperties = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#999",
  fontSize: 13,
  border: "1px dashed #ddd",
  borderRadius: 8,
  textAlign: "center",
  padding: 24,
};
// === ANCHOR: REPORTCOMPOSERPREVIEW_END ===
