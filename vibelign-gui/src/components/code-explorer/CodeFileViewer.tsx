import type { CodeFileReadResult } from "../../lib/vib";
import CodeLine from "./CodeLine";

interface CodeFileViewerProps {
  selectedPath: string | null;
  file: CodeFileReadResult | null;
  isLoading: boolean;
  error: string | null;
}

export default function CodeFileViewer({ selectedPath, file, isLoading, error }: CodeFileViewerProps) {
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

  const lines = file.content.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();

  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", display: "flex", gap: 10, alignItems: "center" }}>
        <strong style={{ overflowWrap: "anywhere" }}>{file.path}</strong>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#666" }}>{file.language} · {file.line_count} lines · {file.size_bytes} bytes</span>
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {lines.map((line, index) => <CodeLine key={index} lineNumber={index + 1} text={line} />)}
      </div>
    </div>
  );
}
