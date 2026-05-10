import type { DocsHtmlReadResult } from "../../lib/vib";
import type { CanvasStatus } from "./canvasArtifactTrust";

const RAW_HTML_BASE_HEIGHT = 900;

function estimateRawHtmlFrameHeight(markup: string): number {
  const headings = Array.from(markup.matchAll(/<h[1-6]\b/gi)).length;
  const paragraphs = Array.from(markup.matchAll(/<p\b/gi)).length;
  const listItems = Array.from(markup.matchAll(/<li\b/gi)).length;
  const codeBlocks = Array.from(markup.matchAll(/<pre\b/gi)).length;
  const lineCount = markup.split(/\r\n|\r|\n/).length;
  return RAW_HTML_BASE_HEIGHT + headings * 72 + paragraphs * 88 + listItems * 46 + codeBlocks * 180 + lineCount * 6;
}

interface RawHtmlCanvasPaneProps {
  html: DocsHtmlReadResult | null;
  status: CanvasStatus;
  reason: string;
}

export default function RawHtmlCanvasPane({ html, status, reason }: RawHtmlCanvasPaneProps) {
  if (status === "generating") {
    return <div className="card" style={{ padding: 18 }}><span className="spinner" /> Raw HTML artifact 생성 중...</div>;
  }
  if (status === "failed" || status === "unsupported") {
    return <div className="card" style={{ padding: 18, lineHeight: 1.7 }}>{reason}</div>;
  }
  if (!html) {
    return <div className="card" style={{ padding: 18, lineHeight: 1.7 }}>Raw HTML artifact가 아직 없습니다. Generate Canvas를 눌러 선택한 문서 1건만 생성하세요.</div>;
  }

  const frameHeight = estimateRawHtmlFrameHeight(html.artifact.html);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {status === "stale" ? <div className="alert alert-warn">STALE Raw HTML Canvas — {reason}</div> : null}
      <iframe
        title={`${html.artifact.title} Raw HTML Canvas`}
        srcDoc={html.artifact.html}
        sandbox=""
        loading="lazy"
        referrerPolicy="no-referrer"
        style={{ width: "100%", height: frameHeight, border: "2px solid #1A1A1A", boxShadow: "4px 4px 0 #1A1A1A", background: "#fff" }}
      />
    </div>
  );
}
