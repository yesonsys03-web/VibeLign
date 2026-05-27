interface CodeLineProps {
  lineNumber: number | null;
  text: string;
  tone?: "normal" | "added" | "removed";
}

export default function CodeLine({ lineNumber, text, tone = "normal" }: CodeLineProps) {
  const background = tone === "added" ? "#D9FFE2" : tone === "removed" ? "#FFE0E0" : "transparent";
  const color = tone === "removed" ? "#8A1F1F" : "#1A1A1A";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "64px minmax(0, 1fr)", background, color }}>
      <div style={{ padding: "0 10px", textAlign: "right", userSelect: "none", color: "#888", borderRight: "1px solid #DDD" }}>
        {lineNumber ?? ""}
      </div>
      <pre style={{ margin: 0, padding: "0 10px", whiteSpace: "pre", overflow: "visible", fontFamily: "IBM Plex Mono, monospace" }}>
        {text || " "}
      </pre>
    </div>
  );
}
