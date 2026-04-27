import MarkdownPane from "./MarkdownPane";
import type { RefObject } from "react";

interface DocumentPaneProps {
  path: string;
  content: string;
  containerRef?: RefObject<HTMLDivElement | null>;
}

function extensionFor(path: string): string {
  return path.split(".").pop()?.toLowerCase() ?? "";
}

function formatPlainContent(path: string, content: string): string {
  if (extensionFor(path) !== "json") return content;
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

function isMarkdownPath(path: string): boolean {
  const extension = extensionFor(path);
  return extension === "md" || extension === "markdown";
}

export default function DocumentPane({ path, content, containerRef }: DocumentPaneProps) {
  if (isMarkdownPath(path)) {
    return <MarkdownPane content={content} containerRef={containerRef} />;
  }

  return (
    <div ref={containerRef} className="card" style={{ height: "100%", overflowY: "auto", padding: 24 }}>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 13,
          lineHeight: 1.65,
          color: "#1A1A1A",
        }}
      >
        {formatPlainContent(path, content)}
      </pre>
    </div>
  );
}
