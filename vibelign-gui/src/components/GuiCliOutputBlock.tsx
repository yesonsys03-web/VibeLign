// === ANCHOR: GUI_CLI_OUTPUT_BLOCK_START ===
import { useEffect, useState } from "react";

/** CLI stdout/stderr와 동일한 본문을 그대로 보여 주는 터미널 스타일 블록 (줄바꿈·공백 유지). */
export function GuiCliOutputBlock({
  text,
  placeholder,
  variant = "default",
}: {
  text: string;
  placeholder: string;
  variant?: "default" | "error" | "warn";
}) {
  const [folded, setFolded] = useState(false);
  const trimmed = text.trim();

  useEffect(() => {
    setFolded(false);
  }, [text]);

  if (!trimmed) {
    if (!placeholder) return null;
    return (
      <div style={{ fontSize: 15, color: "#555", marginBottom: 6, lineHeight: 1.35 }}>
        {placeholder}
      </div>
    );
  }
  const color = variant === "error" ? "#FF4D4D" : variant === "warn" ? "#A05A00" : "#1A1A1A";
  return (
    <div style={{ margin: "0 0 8px 0" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setFolded((f) => !f)}
          style={{ fontSize: 9, fontWeight: 700, padding: "2px 10px", border: "2px solid #1A1A1A", cursor: "pointer" }}
        >
          {folded ? "펼치기" : "접기"}
        </button>
      </div>
      {!folded && (
        <pre
          style={{
            margin: 0,
            padding: "8px 10px",
            maxHeight: 280,
            overflowY: "auto",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 10,
            lineHeight: 1.45,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "#fff",
            border: "2px solid #1A1A1A",
            color,
            boxSizing: "border-box",
          }}
        >
          {text}
        </pre>
      )}
      {folded && (
        <div style={{ fontSize: 10, color: "#888", fontWeight: 600, padding: "4px 2px 0" }}>결과가 접혀 있어요.</div>
      )}
    </div>
  );
}
export default GuiCliOutputBlock;
// === ANCHOR: GUI_CLI_OUTPUT_BLOCK_END ===
