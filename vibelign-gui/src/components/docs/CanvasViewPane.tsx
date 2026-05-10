import { useMemo } from "react";
import type { DocsVisualArtifact } from "../../lib/vib";
import type { CanvasStatus } from "./canvasArtifactTrust";

interface CanvasViewPaneProps {
  artifact: DocsVisualArtifact | null;
  status: CanvasStatus;
  reason: string;
  layout?: "default" | "split";
}

const CANVAS_BASE_HEIGHT = 760;
const CANVAS_MAX_HEIGHT = 3600;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function compactLabel(value: string, max = 120): string {
  const compact = value.replace(/\s+/g, " ").trim();
  return compact.length <= max ? compact : `${compact.slice(0, max - 1).trim()}…`;
}

function visualSignalHtml(items: string[], empty: string, tone: "decision" | "action" | "risk" | "glossary"): string {
  const cleanItems = items.map((item) => item.trim()).filter(Boolean);
  if (cleanItems.length === 0) return `<p class="empty">${escapeHtml(empty)}</p>`;
  return `<div class="signal-board ${tone}">${cleanItems.map((item, index) => `<article class="signal-card"><span class="signal-index">${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(compactLabel(item, tone === "glossary" ? 90 : 110))}</strong></article>`).join("")}</div>`;
}

function sectionOutlineHtml(artifact: DocsVisualArtifact): string {
  const sections = artifact.sections.filter((section) => section.title.trim());
  if (sections.length === 0) return `<p class="empty">문서 section outline이 없습니다.</p>`;
  return `<div class="source-spine" data-canvas-source-order="sections">${sections.map((section, index) => {
    const previewItems = section.body_preview?.filter((item) => item.trim()).slice(0, 4) ?? [];
    const fallbackItems = section.summary ? [section.summary] : [];
    const items = previewItems.length > 0 ? previewItems : fallbackItems;
    return `<article class="source-stop level-${Math.min(section.level, 4)}"><span>${index + 1}</span><strong>${escapeHtml(compactLabel(section.title, 76))}</strong>${items.length > 0 ? `<ul class="source-preview">${items.map((item) => `<li>${escapeHtml(compactLabel(item, 150))}</li>`).join("")}</ul>` : ""}</article>`;
  }).join("")}</div>`;
}

function cleanMermaidLabel(value: string): string {
  return value
    .trim()
    .replace(/^root\(\((.*)\)\)$/i, "$1")
    .replace(/^[A-Za-z0-9_-]+\[(.*)\]$/, "$1")
    .replace(/^"(.*)"$/, "$1")
    .replace(/^'(.*)'$/, "$1")
    .trim();
}

function renderMindmapVisual(source: string): string | null {
  const lines = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  if (!lines.some((line) => line.trim().toLowerCase() === "mindmap")) return null;
  const nodes = lines
    .map((line) => ({ depth: Math.max(0, Math.floor((line.length - line.trimStart().length) / 2) - 1), label: cleanMermaidLabel(line.trim()) }))
    .filter((item) => item.label && item.label.toLowerCase() !== "mindmap")
    .slice(0, 48);
  if (nodes.length === 0) return null;
  const [root, ...children] = nodes;
  return `
    <div class="mindmap-visual" data-diagram-visual="mindmap">
      <div class="mindmap-root">${escapeHtml(root.label)}</div>
      <div class="mindmap-branches">
        ${children.map((node) => `<div class="mindmap-node depth-${Math.min(node.depth, 3)}">${escapeHtml(node.label)}</div>`).join("")}
      </div>
    </div>
  `;
}

function renderFlowchartVisual(source: string): string | null {
  const lines = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const first = lines.find((line) => line.trim())?.trim().toLowerCase() ?? "";
  if (!first.startsWith("graph") && !first.startsWith("flowchart")) return null;
  const labels = lines
    .flatMap((line) => Array.from(line.matchAll(/\[([^\]]+)\]|\(\(([^)]+)\)\)|\(([^)]+)\)/g)).map((match) => cleanMermaidLabel(match[1] ?? match[2] ?? match[3] ?? "")))
    .filter(Boolean)
    .slice(0, 32);
  if (labels.length === 0) return null;
  return `
    <div class="flow-visual" data-diagram-visual="flowchart">
      ${labels.map((label, index) => `<div class="flow-step"><span class="flow-index">${index + 1}</span><span>${escapeHtml(label)}</span></div>`).join("<div class=\"flow-arrow\">↓</div>")}
    </div>
  `;
}

function renderDiagramVisual(source: string): string {
  return renderMindmapVisual(source) ?? renderFlowchartVisual(source) ?? `<pre class="diagram-fallback"><code>${escapeHtml(source)}</code></pre>`;
}

function renderMermaidBlocks(artifact: DocsVisualArtifact): string {
  const diagrams = artifact.diagram_blocks
    .filter((diagram) => diagram.kind === "mermaid" && diagram.source)
    .slice(0, 3);
  if (diagrams.length === 0) {
    return `<p class="empty">표시할 Mermaid flow가 없습니다.</p>`;
  }
  return diagrams.map((diagram, index) => `
    <article class="diagram">
      <div class="eyebrow">Diagram ${index + 1}${diagram.title ? ` · ${escapeHtml(diagram.title)}` : ""}</div>
      ${renderDiagramVisual(diagram.source ?? "")}
    </article>
  `).join("");
}

function estimateCanvasFrameHeight(artifact: DocsVisualArtifact, layout: "default" | "split" = "default"): number {
  const heuristic = artifact.ai_fields ?? artifact.heuristic_fields;
  const decisions = heuristic?.key_rules.length ?? 0;
  const actions = artifact.action_items.filter((item) => !item.checked).length;
  const warningCount = artifact.warnings ? artifact.warnings.length : 0;
  const risks = heuristic?.edge_cases.length || warningCount;
  const glossary = artifact.glossary.length;
  const sections = artifact.sections.length;
  const diagrams = artifact.diagram_blocks.filter((diagram) => diagram.kind === "mermaid" && diagram.source).length;
  const signalCards = decisions + actions + risks + glossary;
  const sectionColumns = layout === "split" ? 1 : 5;
  const signalColumns = layout === "split" ? 1 : 3;
  const estimatedRows = Math.ceil(sections / sectionColumns) + Math.ceil(signalCards / signalColumns);
  const estimatedHeight = CANVAS_BASE_HEIGHT + diagrams * 140 + estimatedRows * 150;
  if (layout === "split") return Math.max(CANVAS_BASE_HEIGHT, estimatedHeight);

  return Math.min(CANVAS_MAX_HEIGHT, Math.max(CANVAS_BASE_HEIGHT, estimatedHeight));
}

function buildCanvasHtml(artifact: DocsVisualArtifact, status: CanvasStatus, reason: string): string {
  const heuristic = artifact.ai_fields ?? artifact.heuristic_fields;
  const decisions = heuristic?.key_rules ?? [];
  const actions = artifact.action_items.filter((item) => !item.checked).map((item) => item.text);
  const risks = heuristic?.edge_cases.length ? heuristic.edge_cases : artifact.warnings ?? [];
  const glossary = artifact.glossary.map((entry) => `${entry.term}: ${entry.definition}`);
  const overview = heuristic?.tldr_one_liner || artifact.summary || "요약 정보가 없습니다.";

  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(artifact.title)} Canvas</title>
  <style>
    :root { color-scheme: light; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f1df; color: #1a1a1a; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px; background: radial-gradient(circle at top left, #fff6d8, #f7f1df 42%, #eee4ca); }
    main { max-width: 1120px; margin: 0 auto; display: grid; gap: 16px; min-width: 0; }
    .hero, section, .diagram { border: 2px solid #1a1a1a; box-shadow: 4px 4px 0 #1a1a1a; background: #fffdf7; padding: 18px; min-width: 0; overflow: hidden; }
    .hero { background: linear-gradient(135deg, #fff7c7, #e7ddff); }
    h1 { margin: 0 0 10px; font-size: clamp(28px, 5vw, 56px); line-height: 0.95; letter-spacing: -0.05em; }
    h2 { margin: 0 0 12px; font-size: 18px; text-transform: uppercase; letter-spacing: 0.08em; }
    p, li { font-size: 14px; line-height: 1.75; overflow-wrap: anywhere; word-break: break-word; }
    ul { padding-left: 20px; margin: 0; min-width: 0; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .pill { display: inline-flex; border: 2px solid #1a1a1a; background: #4dff91; padding: 4px 9px; font-size: 11px; font-weight: 900; text-transform: uppercase; }
    .visual-map { display: grid; gap: 16px; min-width: 0; }
    .map-panel { display: grid; gap: 14px; align-items: stretch; background: #fffdf7; }
    .map-panel h2 { display: flex; align-items: center; gap: 10px; margin: 0; font-size: clamp(20px, 2.8vw, 34px); line-height: 0.95; letter-spacing: 0.06em; white-space: nowrap; }
    .map-panel h2::after { content: ""; flex: 1; min-width: 48px; border-top: 3px solid #1a1a1a; }
    .signal-board { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: 12px; align-content: start; min-width: 0; }
    .signal-card { min-height: 104px; display: grid; grid-template-rows: auto 1fr; gap: 8px; padding: 12px; border: 2px solid #1a1a1a; box-shadow: 3px 3px 0 #1a1a1a; transform: rotate(-0.35deg); overflow-wrap: anywhere; word-break: break-word; }
    .signal-card:nth-child(even) { transform: rotate(0.35deg); }
    .signal-index { width: fit-content; border: 2px solid #1a1a1a; border-radius: 999px; background: #fff; padding: 2px 8px; font-size: 11px; font-weight: 950; }
    .signal-card strong { font-size: 15px; line-height: 1.35; }
    .decision .signal-card { background: #fff4a8; }
    .action .signal-card { background: #b9fbc0; }
    .risk .signal-card { background: #ffadad; }
    .glossary .signal-card { background: #a0c4ff; }
    .source-spine { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap: 12px; min-width: 0; }
    .source-stop { min-height: 132px; display: grid; grid-template-rows: auto auto 1fr; gap: 8px; border: 2px solid #1a1a1a; box-shadow: 3px 3px 0 #1a1a1a; background: #ffc6ff; padding: 12px; position: relative; overflow-wrap: anywhere; }
    .source-stop span { width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; border: 2px solid #1a1a1a; background: #4dff91; font-weight: 950; }
    .source-stop strong { font-size: 16px; line-height: 1.25; }
    .source-preview { display: grid; gap: 6px; padding-left: 18px; margin: 0; color: #514a40; font-size: 13px; line-height: 1.45; }
    .source-preview li { font-size: 13px; line-height: 1.45; }
    .source-stop.level-3 { background: #e7ddff; }
    .source-stop.level-4 { background: #fff4a8; }
    .empty { color: #6a6254; font-style: italic; }
    pre { margin: 0; overflow-x: auto; padding: 14px; background: #171a13; color: #7dff6b; border: 2px solid #1a1a1a; }
    code { font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; line-height: 1.6; }
    .eyebrow { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.08em; color: #6a4cff; margin-bottom: 8px; }
    .stale { background: #ffd166; border: 2px solid #1a1a1a; padding: 10px 12px; font-weight: 800; }
    .mindmap-visual { display: grid; grid-template-columns: minmax(160px, 0.8fr) minmax(260px, 1.4fr); gap: 18px; align-items: center; }
    .mindmap-root { border: 3px solid #1a1a1a; box-shadow: 4px 4px 0 #1a1a1a; background: #6a4cff; color: white; font-size: 20px; font-weight: 950; line-height: 1.15; padding: 18px; border-radius: 22px; text-align: center; }
    .mindmap-branches { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .mindmap-node { position: relative; border: 2px solid #1a1a1a; box-shadow: 3px 3px 0 #1a1a1a; background: #fff4a8; font-weight: 850; padding: 10px 12px; border-radius: 999px; max-width: 260px; }
    .mindmap-node::before { content: ""; position: absolute; left: -14px; top: 50%; width: 12px; border-top: 2px solid #1a1a1a; }
    .mindmap-node.depth-1 { background: #b9fbc0; }
    .mindmap-node.depth-2 { background: #a0c4ff; }
    .mindmap-node.depth-3 { background: #ffc6ff; }
    .flow-visual { display: flex; flex-direction: column; align-items: stretch; gap: 8px; max-width: 720px; }
    .flow-step { display: flex; align-items: center; gap: 12px; border: 2px solid #1a1a1a; box-shadow: 3px 3px 0 #1a1a1a; background: #e7ddff; padding: 12px 14px; font-size: 15px; font-weight: 850; }
    .flow-index { display: inline-flex; align-items: center; justify-content: center; min-width: 28px; height: 28px; border: 2px solid #1a1a1a; border-radius: 50%; background: #4dff91; font-size: 12px; font-weight: 950; }
    .flow-arrow { font-size: 20px; font-weight: 950; text-align: center; line-height: 1; }
    .diagram-fallback { opacity: 0.9; }
    @media (max-width: 720px) { .mindmap-visual { grid-template-columns: 1fr; } .mindmap-node::before { display: none; } .map-panel h2 { white-space: normal; } }
  </style>
</head>
<body>
  <main>
    ${status === "stale" ? `<div class="stale">STALE Canvas — ${escapeHtml(reason)}</div>` : ""}
    <header class="hero">
      <div class="meta">
        <span class="pill">HTML Canvas</span>
        <span class="pill">schema ${escapeHtml(String(artifact.schema_version))}</span>
        <span class="pill">${escapeHtml(artifact.generated_at.slice(0, 10))}</span>
      </div>
      <h1>${escapeHtml(artifact.title)}</h1>
      <p>${escapeHtml(overview)}</p>
    </header>
    <div class="visual-map" data-canvas-visual-mode="document-control-map">
      <section class="map-panel" aria-label="Outline Source Order"><h2>Outline · Source Order</h2>${sectionOutlineHtml(artifact)}</section>
      <section class="map-panel" aria-label="Flow"><h2>Flow</h2>${renderMermaidBlocks(artifact)}</section>
      <section class="map-panel" aria-label="Decisions"><h2>Decisions</h2>${visualSignalHtml(decisions, "핵심 결정/규칙이 아직 추출되지 않았습니다.", "decision")}</section>
      <section class="map-panel" aria-label="Actions"><h2>Actions</h2>${visualSignalHtml(actions, "미완료 action이 없습니다.", "action")}</section>
      <section class="map-panel" aria-label="Risks"><h2>Risks</h2>${visualSignalHtml(risks, "별도 risk 항목이 없습니다.", "risk")}</section>
      <section class="map-panel" aria-label="Glossary"><h2>Glossary</h2>${visualSignalHtml(glossary, "용어 항목이 없습니다.", "glossary")}</section>
    </div>
  </main>
</body>
</html>`;
}

export default function CanvasViewPane({ artifact, status, reason, layout = "default" }: CanvasViewPaneProps) {
  const html = useMemo(() => artifact ? buildCanvasHtml(artifact, status, reason) : "", [artifact, reason, status]);
  const frameHeight = useMemo(() => artifact ? estimateCanvasFrameHeight(artifact, layout) : CANVAS_BASE_HEIGHT, [artifact, layout]);

  if (status === "generating") {
    return <div className="card" style={{ padding: 18 }}><span className="spinner" /> Canvas artifact 생성 중...</div>;
  }
  if (status === "failed" || status === "unsupported" || status === "not_generated" || !artifact) {
    return <div className="card" style={{ padding: 18, lineHeight: 1.7 }}>{reason}</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <iframe
        title={`${artifact.title} HTML Canvas`}
        srcDoc={html}
        sandbox=""
        loading="lazy"
        referrerPolicy="no-referrer"
        style={{ width: "100%", height: frameHeight, border: "2px solid #1A1A1A", boxShadow: "4px 4px 0 #1A1A1A", background: "#fff" }}
      />
    </div>
  );
}
