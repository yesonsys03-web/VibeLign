// === ANCHOR: PDFPREVIEW_START ===
import { useEffect, useRef, useState } from "react";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { readReportPdfBytes } from "../../lib/vib/report";

export interface PdfPreviewProps {
  /** 프로젝트 루트(컨테인먼트 검증 기준). */
  cwd: string;
  /** 미리볼 .pdf 절대 경로(생성된 내부 사본). */
  path: string;
}

/**
 * 생성된 보고서 PDF 를 pdf.js 로 인앱 렌더한다. 무거운 라이브러리는 동적 import 라
 * PDF 미리보기를 열 때만 로드된다(앱 시작·다른 탭에 영향 없음). 모든 페이지를
 * 캔버스로 그려 세로로 쌓는다.
 */
// === ANCHOR: PDFPREVIEW_PDFPREVIEW_START ===
export function PdfPreview({ cwd, path }: PdfPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const container = containerRef.current;
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

        const buf = await readReportPdfBytes(cwd, path);
        if (cancelled) return;
        // cMapUrl/standardFontDataUrl 은 vite-plugin-static-copy 가 /pdfjs/ 로 제공한다.
        // 없으면 비임베드 표준폰트(Helvetica 등)·CID 폰트가 로딩 실패해 텍스트가 안 그려진다.
        const doc = await pdfjs.getDocument({
          data: new Uint8Array(buf),
          cMapUrl: "/pdfjs/cmaps/",
          cMapPacked: true,
          standardFontDataUrl: "/pdfjs/standard_fonts/",
        }).promise;
        if (cancelled) return;

        if (container) container.innerHTML = "";
        // 캔버스 가로폭을 컨테이너에 맞추고, 고해상도 화면에선 dpr 만큼 키워 선명하게.
        const width = container?.clientWidth ?? 800;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);

        for (let i = 1; i <= doc.numPages; i++) {
          if (cancelled) return;
          const page = await doc.getPage(i);
          const base = page.getViewport({ scale: 1 });
          const scale = Math.max(0.2, (width - 24) / base.width);
          const viewport = page.getViewport({ scale: scale * dpr });

          const canvas = document.createElement("canvas");
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          canvas.style.width = "100%";
          canvas.style.height = "auto";
          canvas.style.display = "block";
          canvas.style.margin = "0 auto 12px";
          canvas.style.boxShadow = "0 1px 6px rgba(0,0,0,0.25)";
          canvas.style.background = "#fff";
          const ctx = canvas.getContext("2d");
          if (!ctx || !container) continue;
          container.appendChild(canvas);
          await page.render({ canvasContext: ctx, viewport }).promise;
        }
        if (!cancelled) setLoading(false);
      } catch (e) {
        if (!cancelled) {
          setError(`PDF 미리보기를 표시하지 못했어요: ${String(e)}`);
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [cwd, path]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      {loading && (
        <p style={{ fontSize: 13, color: "#888", margin: "0 0 8px" }}>PDF 미리보기 불러오는 중…</p>
      )}
      {error && (
        <p role="alert" style={{ fontSize: 13, color: "#9B1B1B", margin: "0 0 8px" }}>
          {error}
        </p>
      )}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflow: "auto",
          background: "#525659",
          border: "1px solid #ddd",
          borderRadius: 4,
          padding: 12,
        }}
      />
    </div>
  );
}
// === ANCHOR: PDFPREVIEW_PDFPREVIEW_END ===
// === ANCHOR: PDFPREVIEW_END ===
