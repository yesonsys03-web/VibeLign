import { useEffect, useState } from "react";
import type { DocsHtmlReadResult } from "../../lib/vib";
import type { CanvasStatus } from "./canvasArtifactTrust";

const RAW_HTML_BASE_HEIGHT = 900;

// onLoad 측정 실패 시 fallback. iframe 안 콘텐츠가 추정보다 길면 잘려 보이는 사용자
// 보고 (2026-05-13) 의 원인이라 onLoad 의 scrollHeight 가 진짜 답 — 본 함수는 첫
// 프레임의 placeholder 만 결정.
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
  const markup = html?.artifact.html ?? "";
  const [measuredHeight, setMeasuredHeight] = useState<number | null>(null);

  useEffect(() => {
    // 새 markup 으로 바뀌면 측정값 초기화 — 다음 iframe load 시 다시 측정.
    setMeasuredHeight(null);
  }, [markup]);

  if (status === "generating") {
    return <div className="card" style={{ padding: 18 }}><span className="spinner" /> Raw HTML artifact 생성 중...</div>;
  }
  if (status === "failed" || status === "unsupported") {
    return <div className="card" style={{ padding: 18, lineHeight: 1.7 }}>{reason}</div>;
  }
  if (!html) {
    return <div className="card" style={{ padding: 18, lineHeight: 1.7 }}>Raw HTML artifact가 아직 없습니다. Generate Canvas를 눌러 선택한 문서 1건만 생성하세요.</div>;
  }

  const fallbackHeight = estimateRawHtmlFrameHeight(markup);
  const frameHeight = measuredHeight ?? fallbackHeight;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {status === "stale" ? <div className="alert alert-warn">STALE Raw HTML Canvas — {reason}</div> : null}
      <iframe
        title={`${html.artifact.title} Raw HTML Canvas`}
        srcDoc={markup}
        // `allow-same-origin` 만 추가 — scripts/forms/etc 는 여전히 disabled. Raw HTML
        // artifact 는 vibelign 내부 docs (markdown → HTML) 변환 결과라 trusted.
        sandbox="allow-same-origin"
        loading="lazy"
        referrerPolicy="no-referrer"
        onLoad={(event) => {
          try {
            const doc = event.currentTarget.contentDocument;
            if (!doc) return;
            const docHeight = Math.max(
              doc.documentElement?.scrollHeight ?? 0,
              doc.body?.scrollHeight ?? 0,
            );
            if (docHeight > 0) {
              // margin 24px 추가 — body padding 등으로 약간의 여백 확보.
              setMeasuredHeight((prev) => (prev === docHeight + 24 ? prev : docHeight + 24));
            }
          } catch {
            // sandbox 또는 cross-origin 으로 contentDocument 접근 불가 — estimate fallback 유지.
          }
        }}
        style={{ width: "100%", height: frameHeight, border: "2px solid #1A1A1A", boxShadow: "4px 4px 0 #1A1A1A", background: "#fff" }}
      />
    </div>
  );
}
