import CodeLine from "./CodeLine";

export type DiffLineKind = "context" | "added" | "removed";

export interface DiffLine {
  kind: DiffLineKind;
  oldLineNumber: number | null;
  newLineNumber: number | null;
  text: string;
}

interface CodeDiffViewerProps {
  path: string;
  lines: DiffLine[];
}

export default function CodeDiffViewer({ path, lines }: CodeDiffViewerProps) {
  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", fontWeight: 800 }}>
        Diff Preview · {path}
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {lines.map((line, index) => (
          <CodeLine
            key={index}
            lineNumber={line.kind === "removed" ? line.oldLineNumber : line.newLineNumber}
            text={line.text}
            tone={line.kind === "added" ? "added" : line.kind === "removed" ? "removed" : "normal"}
          />
        ))}
      </div>
    </div>
  );
}
