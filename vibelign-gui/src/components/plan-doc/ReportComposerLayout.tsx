import { useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from "react";

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
  readonly workspaceTab?: "report" | "cards";
  readonly onWorkspaceTabChange?: (tab: "report" | "cards") => void;
  readonly companion?: ReactNode;
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
  workspaceTab = "report",
  onWorkspaceTabChange,
  companion,
  exportBox,
  result,
  exportedPath,
  openErr,
  onOpenErr,
  onClose,
}: ReportComposerLayoutProps): ReactNode {
  const inlineShellRef = useRef<HTMLDivElement | null>(null);
  const isNarrowInline = useNarrowInlineLayout(inlineShellRef);
  const canShowTabs = companion !== undefined && onWorkspaceTabChange !== undefined;
  const workspace = (
    <div style={workspacePane}>
      {canShowTabs && (
        <div role="tablist" aria-label="보고서 작성 작업 영역" style={workspaceTabs}>
          <button
            type="button"
            role="tab"
            aria-selected={workspaceTab === "report"}
            onClick={() => onWorkspaceTabChange("report")}
            style={workspaceTabButton(workspaceTab === "report")}
          >
            보고서
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={workspaceTab === "cards"}
            onClick={() => onWorkspaceTabChange("cards")}
            style={workspaceTabButton(workspaceTab === "cards")}
          >
            카드뉴스
          </button>
        </div>
      )}
      <div role="tabpanel" style={workspaceBody}>
        {workspaceTab === "cards" && companion !== undefined ? (
          companion
        ) : (
          <ReportComposerPreview cwd={cwd} result={result} fillHeight={inline} />
        )}
      </div>
    </div>
  );

  if (inline) {
    return (
      <div ref={inlineShellRef} style={inlineShell(isNarrowInline)}>
        <div style={inlineOptionsPane(isNarrowInline)}>
          {controls}
          {exportBox}
        </div>
        {workspace}
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
        {workspace}
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
const workspacePane: CSSProperties = {
  flex: 1,
  minWidth: 0,
  display: "flex",
  flexDirection: "column",
};
const workspaceTabs: CSSProperties = {
  display: "flex",
  gap: 6,
  alignItems: "center",
  marginBottom: 10,
  flexShrink: 0,
};
const workspaceBody: CSSProperties = {
  flex: 1,
  minHeight: 0,
  overflow: "auto",
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

function workspaceTabButton(active: boolean): CSSProperties {
  return {
    border: "2px solid #1A1A1A",
    background: active ? "#F5621E" : "#FFFFFF",
    color: "#1A1A1A",
    padding: "7px 12px",
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: active ? "2px 2px 0 #1A1A1A" : "none",
  };
}

function inlineShell(isNarrow: boolean): CSSProperties {
  return {
    display: "flex",
    flexDirection: isNarrow ? "column" : "row",
    height: "100%",
    gap: isNarrow ? 12 : 16,
    minHeight: 0,
  };
}

function inlineOptionsPane(isNarrow: boolean): CSSProperties {
  return {
    width: isNarrow ? "auto" : 300,
    maxHeight: isNarrow ? 240 : "none",
    flexShrink: 0,
    overflow: "auto",
    padding: isNarrow ? "4px 4px 12px" : "4px 16px 16px 4px",
    borderRight: isNarrow ? "none" : "1px solid #e5e0d0",
    borderBottom: isNarrow ? "1px solid #e5e0d0" : "none",
  };
}

function useNarrowInlineLayout(ref: RefObject<HTMLDivElement | null>): boolean {
  const [isNarrow, setIsNarrow] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (node === null) return;

    const update = () => {
      setIsNarrow(node.getBoundingClientRect().width < 760);
    };
    update();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }

    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, [ref]);

  return isNarrow;
}
