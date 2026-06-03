// === ANCHOR: CODEFILEVIEWER_START ===
import type { CodeFileReadResult, CodeFileDiffResult } from "../../lib/vib/types";
import CodeLine from "./CodeLine";
import DiffLine from "./DiffLine";

interface CodeFileViewerProps {
  selectedPath: string | null;
  file: CodeFileReadResult | null;
  diff: CodeFileDiffResult | null;
  diffMode: boolean;
  onToggleDiffMode: () => void;
  isLoading: boolean;
  error: string | null;
}

export default function CodeFileViewer({
  selectedPath, file, diff, diffMode, onToggleDiffMode, isLoading, error,
}: CodeFileViewerProps) {
  if (!selectedPath) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>왼쪽 트리에서 코드 파일을 선택하세요.</div>;
  }
  if (isLoading) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>코드 파일을 읽는 중입니다…</div>;
  }
  if (error) {
    return <div className="alert-error" style={{ margin: 16 }}>{error}</div>;
  }
  if (!file) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>표시할 코드가 없습니다.</div>;
  }

  const hasBaseline = diff !== null && diff.baseline_source !== "none";
  const toggleDisabled = !hasBaseline;
  const toggleTitle = toggleDisabled ? "비교할 기준선이 없습니다" : (diffMode ? "평면 뷰로 전환" : "Diff 뷰로 전환");
  const badge = hasBaseline ? `+${diff!.added} −${diff!.removed}` : "";

  const lines = file.content.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();

  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", display: "flex", gap: 10, alignItems: "center" }}>
        <strong style={{ overflowWrap: "anywhere" }}>{file.path}</strong>
        <button
          type="button"
          onClick={onToggleDiffMode}
          disabled={toggleDisabled}
          title={toggleTitle}
          style={{
            fontSize: 11, padding: "3px 8px",
            background: diffMode && hasBaseline ? "rgba(46,160,67,0.18)" : "transparent",
            border: "1px solid #333", borderRadius: 4,
            cursor: toggleDisabled ? "not-allowed" : "pointer",
            opacity: toggleDisabled ? 0.5 : 1,
          }}
        >
          Diff {badge && <span style={{ marginLeft: 6, color: "#888" }}>{badge}</span>}
        </button>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#666" }}>
          {file.language} · {file.line_count} lines · {file.size_bytes} bytes
        </span>
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {diffMode && diff && hasBaseline
          ? diff.lines.map((line, i) => <DiffLine key={i} line={line} />)
          : lines.map((line, index) => <CodeLine key={index} lineNumber={index + 1} text={line} />)}
      </div>
    </div>
  );
}
// === ANCHOR: CODEFILEVIEWER_END ===
