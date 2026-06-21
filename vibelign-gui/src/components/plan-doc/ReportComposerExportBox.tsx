// === ANCHOR: REPORTCOMPOSEREXPORTBOX_START ===
import type { CSSProperties, ReactNode } from "react";
import { openPath } from "@tauri-apps/plugin-opener";

import type { ReportComposerResultState } from "./useReportComposerGeneration";

type ReportComposerExportBoxProps = {
  readonly result: ReportComposerResultState | null;
  readonly inline: boolean;
  readonly exporting: boolean;
  readonly exportedPath: string | null;
  readonly exportErr: string | null;
  readonly openErr: string | null;
  readonly onOpenErr: (message: string | null) => void;
  readonly onChooseLocation: () => void;
};

// === ANCHOR: REPORTCOMPOSEREXPORTBOX_REPORTCOMPOSEREXPORTBOX_START ===
export function ReportComposerExportBox({
  result,
  inline,
  exporting,
  exportedPath,
  exportErr,
  openErr,
  onOpenErr,
  onChooseLocation,
}: ReportComposerExportBoxProps): ReactNode {
  if (!result || !result.ok) return null;

  return (
    <div style={exportBox}>
      <div style={{ fontSize: 13, color: "#1A1A1A" }}>
        {exporting ? (
          "저장 위치로 복사 중…"
        ) : exportedPath ? (
          <>
            📁 저장 위치: <b style={{ wordBreak: "break-all" }}>{exportedPath}</b>
          </>
        ) : (
          "저장 위치를 준비 중…"
        )}
      </div>
      {exportErr && (
        <p role="alert" style={{ color: "#9B1B1B", fontSize: 12, margin: "6px 0 0" }}>
          {exportErr}
        </p>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
        <button type="button" onClick={onChooseLocation} disabled={exporting} style={secondaryBtn}>
          다른 위치에 저장…
        </button>
        {inline && (
          <button type="button" onClick={() => openResultPath(result, exportedPath, onOpenErr)} style={primaryBtn}>
            파일 열기
          </button>
        )}
      </div>
      {inline && openErr && (
        <p role="alert" style={{ color: "#9B1B1B", fontSize: 12, margin: "6px 0 0" }}>
          {openErr}
        </p>
      )}
    </div>
  );
}
// === ANCHOR: REPORTCOMPOSEREXPORTBOX_REPORTCOMPOSEREXPORTBOX_END ===

// === ANCHOR: REPORTCOMPOSEREXPORTBOX_OPENRESULTPATH_START ===
export function openResultPath(
  result: ReportComposerResultState,
  exportedPath: string | null,
  onOpenErr: (message: string | null) => void,
): void {
  if (!result.ok) return;
  onOpenErr(null);
  void openPath(exportedPath ?? result.path).catch((error) =>
    onOpenErr(`파일을 열지 못했어요: ${String(error)}`),
  );
}
// === ANCHOR: REPORTCOMPOSEREXPORTBOX_OPENRESULTPATH_END ===

export const primaryBtn: CSSProperties = {
  background: "#9B1B1B",
  color: "#fff",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
};

export const secondaryBtn: CSSProperties = {
  background: "#e5e0d0",
  color: "#1A1A1A",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
};

const exportBox: CSSProperties = {
  marginTop: 12,
  padding: 12,
  background: "#f6f1e0",
  border: "1px solid #e5e0d0",
  borderRadius: 6,
};
// === ANCHOR: REPORTCOMPOSEREXPORTBOX_END ===
