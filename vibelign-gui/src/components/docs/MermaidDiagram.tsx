import { useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface MermaidDiagramProps {
  chart: string;
}

let mermaidInitPromise: Promise<typeof import("mermaid")> | null = null;

const diagramSurfaceStyle = {
  border: "2px solid #1A1A1A",
  boxShadow: "4px 4px 0px #1A1A1A",
  background: "#FFFFFF",
  transform: "none",
  transition: "none",
} as const;

async function loadMermaid() {
  if (!mermaidInitPromise) {
    mermaidInitPromise = import("mermaid").then((module) => {
      const mermaid = module.default;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        logLevel: "fatal",
      });
      return module;
    });
  }
  return mermaidInitPromise;
}

function FallbackCode({ chart, label }: { chart: string; label?: string }) {
  return (
    <div>
      {label ? <div className="alert alert-warn" style={{ marginBottom: 8 }}>{label}</div> : null}
      <pre style={{ background: "#1E2216", color: "#7DFF6B", padding: 16, overflowX: "auto", margin: 0, border: "2px solid #1A1A1A" }}>
        <code style={{ fontFamily: "IBM Plex Mono, monospace" }}>{chart}</code>
      </pre>
    </div>
  );
}

export default function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const reactId = useId();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const diagramId = useMemo(() => `mermaid-${reactId.replace(/[:]/g, "-")}`, [reactId]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!isVisible) return;

    setSvg(null);
    setError(null);

    loadMermaid()
      .then(async (module) => {
        const mermaid = module.default;
        const { svg: rendered } = await mermaid.render(diagramId, chart);
        if (!cancelled) {
          setSvg(rendered);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Mermaid 렌더 실패");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [chart, diagramId, isVisible]);

  useEffect(() => {
    if (!isExpanded) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsExpanded(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isExpanded]);

  return (
    <div ref={containerRef} style={{ marginBottom: 16 }}>
      {!isVisible ? <FallbackCode chart={chart} label="Mermaid 다이어그램을 화면에 보이는 시점에 렌더합니다." /> : null}
      {isVisible && error ? <FallbackCode chart={chart} label={`Mermaid 렌더 실패: ${error}`} /> : null}
      {isVisible && !error && !svg ? <div className="alert alert-warn">Mermaid 다이어그램 렌더 중...</div> : null}
      {isVisible && !error && svg ? (
        <>
          <div
            role="button"
            tabIndex={0}
            onClick={() => setIsExpanded(true)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setIsExpanded(true);
              }
            }}
            style={{
              ...diagramSurfaceStyle,
              padding: 12,
              overflowX: "auto",
              width: "100%",
              textAlign: "left",
              cursor: "zoom-in",
            }}
            title="클릭해서 크게 보기"
          >
            <div dangerouslySetInnerHTML={{ __html: svg }} />
          </div>

          {isExpanded ? createPortal(
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(26, 26, 26, 0.78)",
                zIndex: 9999,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
              }}
              onClick={() => setIsExpanded(false)}
            >
              <div
                style={{
                  ...diagramSurfaceStyle,
                  width: "min(1400px, 96vw)",
                  maxHeight: "92vh",
                  overflow: "auto",
                  padding: 18,
                  cursor: "default",
                }}
                onClick={(event) => event.stopPropagation()}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 900, textTransform: "uppercase", letterSpacing: 1 }}>Diagram Preview</div>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setIsExpanded(false)}>닫기</button>
                </div>
                <div
                  aria-label="Expanded Mermaid diagram"
                  style={{ overflowX: "auto" }}
                  dangerouslySetInnerHTML={{ __html: svg }}
                />
              </div>
            </div>,
            document.body,
          ) : null}
        </>
      ) : null}
    </div>
  );
}
