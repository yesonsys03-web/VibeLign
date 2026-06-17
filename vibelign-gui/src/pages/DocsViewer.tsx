// === ANCHOR: DOCSVIEWER_START ===
import { useEffect, useMemo, useRef, useState } from "react";
import CanvasGenerateButton from "../components/docs/CanvasGenerateButton";
import CanvasViewPane from "../components/docs/CanvasViewPane";
import DocumentPane from "../components/docs/DocumentPane";
import DocsSidebar from "../components/docs/DocsSidebar";
import RawHtmlCanvasPane from "../components/docs/RawHtmlCanvasPane";
import VisualSummaryPane from "../components/docs/VisualSummaryPane";
import useCanvasArtifactState from "../components/docs/useCanvasArtifactState";
import { extractSections, loadDoc, loadDocsIndex, reloadDocsIndex } from "../lib/docs";
import { addExtraDocSource, listExtraDocSources, pickFolder, removeExtraDocSource, type DocsIndexEntry, type ReadFileResult } from "../lib/vib";

type DocsViewMode = "source" | "easy" | "canvas" | "raw-html" | "split";

interface DocsViewerProps {
  projectDir: string;
  onGenerateReport?: (path: string) => void;
}

export default function DocsViewer({ projectDir, onGenerateReport }: DocsViewerProps) {
  const [docsIndex, setDocsIndex] = useState<DocsIndexEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [doc, setDoc] = useState<ReadFileResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [indexLoading, setIndexLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
  const [rebuildMessage, setRebuildMessage] = useState<string | null>(null);
  const [extraSources, setExtraSources] = useState<string[]>([]);
  const [isAddingSource, setIsAddingSource] = useState(false);
  const [showAddSourcePanel, setShowAddSourcePanel] = useState(false);
  const [addSourceInput, setAddSourceInput] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);
  const markdownPaneRef = useRef<HTMLDivElement | null>(null);
  const layoutRef = useRef<HTMLDivElement | null>(null);
  const [layoutWidth, setLayoutWidth] = useState(0);
  const [viewMode, setViewMode] = useState<DocsViewMode>("source");
  const rawHtmlCanvasEnabled = useMemo(() => {
    try {
      return window.localStorage.getItem("vibelign.docs.rawHtmlCanvas") !== "0";
    } catch {
      return true;
    }
  }, []);

  useEffect(() => {
    // === ANCHOR: DOCSVIEWER_UPDATEWIDTH_START ===
    const updateWidth = () => {
      setLayoutWidth(layoutRef.current?.getBoundingClientRect().width ?? window.innerWidth);
    };
    // === ANCHOR: DOCSVIEWER_UPDATEWIDTH_END ===

    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setIndexLoading(true);
    setIndexError(null);

    const applyEntries = (entries: DocsIndexEntry[]) => {
      setDocsIndex(entries);
      setSelectedPath((current) => {
        if (current && entries.some((entry) => entry.path === current)) {
          return current;
        }
        return entries.find((entry) => entry.path === "PROJECT_CONTEXT.md")?.path ?? entries[0]?.path ?? null;
      });
    };

    const loadIndex = async () => {
      try {
        const entries = await loadDocsIndex(projectDir);
        if (cancelled) return;
        applyEntries(entries);
        setIndexLoading(false);

        try {
          const res = await listExtraDocSources(projectDir);
          if (cancelled) return;
          applyEntries(res.entries);
          setExtraSources(res.sources);
        } catch (err: unknown) {
          if (!cancelled) {
            setRebuildMessage(err instanceof Error ? err.message : typeof err === "string" ? err : "추가 문서 소스를 읽을 수 없어요");
          }
        }
      } catch (primaryErr: unknown) {
        try {
          const res = await listExtraDocSources(projectDir);
          if (cancelled) return;
          applyEntries(res.entries);
          setExtraSources(res.sources);
          setIndexLoading(false);
        } catch (fallbackErr: unknown) {
          if (!cancelled) {
            setDocsIndex([]);
            setExtraSources([]);
            setSelectedPath(null);
            const err = fallbackErr instanceof Error ? fallbackErr : primaryErr;
            setIndexError(err instanceof Error ? err.message : typeof err === "string" ? err : "문서 인덱스를 읽을 수 없어요");
            setIndexLoading(false);
          }
        }
      }
    };

    void loadIndex();

    return () => {
      cancelled = true;
    };
  }, [projectDir]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      setDoc(null);
      setError(null);
      setIsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setIsLoading(true);
    setDoc(null);
    setError(null);

    loadDoc(projectDir, selectedPath)
      .then((result) => {
        if (!cancelled) {
          setDoc(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setDoc(null);
          setError(err instanceof Error ? err.message : "문서를 읽을 수 없어요");
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectDir, selectedPath, refreshTick]);

  const sections = useMemo(() => extractSections(doc?.content ?? ""), [doc?.content]);
  const selectedDoc = useMemo(
    () => docsIndex.find((entry) => entry.path === selectedPath) ?? null,
    [docsIndex, selectedPath],
  );

  const canvas = useCanvasArtifactState({ projectDir, selectedPath, doc });

  const trustTone = useMemo(() => {
    if (canvas.trustState === "enhanced-synced") return { className: "alert-success", label: "CANVAS READY" };
    if (canvas.trustState === "enhanced-stale") return { className: "alert-warn", label: canvas.status === "unsupported" ? "CANVAS UNSUPPORTED" : "CANVAS STALE" };
    if (canvas.trustState === "enhanced-failed") return { className: "alert-error", label: "CANVAS FAILED" };
    return { className: "", label: "SOURCE ONLY" };
  }, [canvas.status, canvas.trustState]);

  const enhancementPartiallyDisabled = useMemo(
    () => canvas.visual?.artifact.warnings?.some((warning) => warning.startsWith("enhancement_partial_disabled:")) ?? false,
    [canvas.visual],
  );
  const isMinimalLayout = layoutWidth > 0 && layoutWidth < 900;
  const splitGridColumns = layoutWidth >= 1100 ? "minmax(0, 1fr) minmax(360px, 0.9fr)" : "minmax(0, 1fr)";
  const showSidebar = !isMinimalLayout;

  // === ANCHOR: DOCSVIEWER_HANDLEREFRESHCURRENT_START ===
  async function handleRefreshCurrent() {
    if (!selectedPath || !projectDir) return;
    setIsRefreshing(true);
    setRebuildMessage(null);
    try {
      setRefreshTick((value) => value + 1);
    } finally {
      setTimeout(() => setIsRefreshing(false), 150);
    }
  }
  // === ANCHOR: DOCSVIEWER_HANDLEREFRESHCURRENT_END ===

  // === ANCHOR: DOCSVIEWER_HANDLEREBUILDINDEX_START ===
  async function handleRebuildIndex() {
    if (!projectDir) return;
    setIsRebuildingIndex(true);
    setRebuildMessage(null);
    setIndexError(null);
    try {
      // Use listExtraDocSources to refresh both entries and extraSources in one call.
      // reloadDocsIndex (the ↻ 인덱스 button) forces a backend rebuild, then we also
      // refresh extra sources so the remove-buttons panel stays in sync.
      await reloadDocsIndex(projectDir); // forces cache invalidation
      const res = await listExtraDocSources(projectDir);
      setDocsIndex(res.entries);
      setExtraSources(res.sources);
      setSelectedPath((current) => {
        if (current && res.entries.some((entry) => entry.path === current)) return current;
        return res.entries.find((entry) => entry.path === "PROJECT_CONTEXT.md")?.path ?? res.entries[0]?.path ?? null;
      });
      setRebuildMessage(`문서 인덱스를 다시 만들었습니다 (${res.entries.length}개).`);
    } catch (err: unknown) {
      setIndexError(err instanceof Error ? err.message : "문서 인덱스를 다시 만드는 데 실패했습니다.");
    } finally {
      setIsRebuildingIndex(false);
    }
  }
  // === ANCHOR: DOCSVIEWER_HANDLEREBUILDINDEX_END ===

  // === ANCHOR: DOCSVIEWER_RELATIVIZE_START ===
  function relativizeInsideProject(root: string, abs: string): string | null {
    const n = (s: string) => s.replaceAll("\\", "/").replace(/\/+$/, "");
    const r = n(root), a = n(abs);
    const windowsLike = /^[A-Za-z]:\//.test(r) || /^[A-Za-z]:\//.test(a) || r.startsWith("//") || a.startsWith("//");
    const compareRoot = windowsLike ? r.toLowerCase() : r;
    const compareAbs = windowsLike ? a.toLowerCase() : a;
    if (compareAbs === compareRoot) return null;
    if (compareAbs.startsWith(compareRoot + "/")) return a.slice(r.length + 1);
    return null;
  }
  // === ANCHOR: DOCSVIEWER_RELATIVIZE_END ===

  // === ANCHOR: DOCSVIEWER_HANDLEADDSOURCE_START ===
  async function handleBrowseForSource() {
    // 네이티브 선택기로 숨김 폴더를 고를 수 없을 때를 위한 보조 수단.
    // 가시 폴더를 고르고 싶으면 여기서 선택하면 input 에 상대 경로가 채워진다.
    if (!projectDir) return;
    const picked = await pickFolder(projectDir);
    if (!picked) return;
    const rel = relativizeInsideProject(projectDir, picked);
    if (!rel) {
      setRebuildMessage("프로젝트 루트 안쪽 폴더만 추가할 수 있어요.");
      return;
    }
    setAddSourceInput(rel);
  }

  async function handleAddSource() {
    if (!projectDir) return;
    const rel = addSourceInput.trim();
    if (!rel) {
      setRebuildMessage("경로를 입력하거나 탐색으로 폴더를 선택하세요.");
      return;
    }
    setIsAddingSource(true);
    setRebuildMessage(null);
    try {
      const res = await addExtraDocSource(projectDir, rel);
      setDocsIndex(res.entries);
      setExtraSources(res.sources);
      setRebuildMessage(`추가 문서 소스 등록: ${rel} (${res.entries.length}개 문서)`);
      setShowAddSourcePanel(false);
      setAddSourceInput("");
    } catch (err: unknown) {
      setRebuildMessage(err instanceof Error ? err.message : "소스 추가에 실패했습니다.");
    } finally {
      setIsAddingSource(false);
    }
  }
  // === ANCHOR: DOCSVIEWER_HANDLEADDSOURCE_END ===

  // === ANCHOR: DOCSVIEWER_HANDLEREMOVESOURCE_START ===
  async function handleRemoveSource(source: string) {
    if (!projectDir) return;
    setRebuildMessage(null);
    try {
      const res = await removeExtraDocSource(projectDir, source);
      setDocsIndex(res.entries);
      setExtraSources(res.sources);
      setRebuildMessage(`추가 문서 소스 제거: ${source}`);
    } catch (err: unknown) {
      setRebuildMessage(err instanceof Error ? err.message : "소스 제거에 실패했습니다.");
    }
  }
  // === ANCHOR: DOCSVIEWER_HANDLEREMOVESOURCE_END ===

  // === ANCHOR: DOCSVIEWER_HANDLEPHASESELECT_START ===
  function handlePhaseSelect(sectionId: string) {
    const container = markdownPaneRef.current;
    if (!container) return;
    const target = container.querySelector<HTMLElement>(`[data-doc-heading-id="${sectionId}"]`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  // === ANCHOR: DOCSVIEWER_HANDLEPHASESELECT_END ===

  if (indexLoading) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div className="page-header" style={{ padding: "12px 20px" }}>
          <span className="page-title">DOCS VIEWER</span>
          <span style={{ fontSize: 11, color: "#666", fontWeight: 700 }}>LOADING</span>
        </div>

        <div className="page-content" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ width: "min(480px, 100%)", textAlign: "center" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "IBM Plex Mono, monospace", fontSize: 12, fontWeight: 700 }}>
              <span className="spinner" />
              문서 인덱스를 불러오는 중...
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "12px 20px" }}>
        <span className="page-title">DOCS VIEWER</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleRebuildIndex()} disabled={isRebuildingIndex || canvas.isGenerating || isRefreshing} title="문서 인덱스를 다시 스캔해 사이드바 목록을 갱신해요">
            {isRebuildingIndex ? "인덱스 갱신 중..." : "↻ 인덱스"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => { setShowAddSourcePanel((v) => !v); setRebuildMessage(null); }} disabled={isAddingSource || isRebuildingIndex} title="추가 문서 소스 폴더를 등록해요 (숨김 폴더 포함)">
            {isAddingSource ? "추가 중..." : showAddSourcePanel ? "× 취소" : "+ 소스 추가"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleRefreshCurrent()} disabled={isRefreshing || canvas.isGenerating || !selectedPath}>
            {isRefreshing ? "새로고침 중..." : "Refresh"}
          </button>
          <span style={{ fontSize: 11, color: "#666", fontWeight: 700 }}>PHASE 10</span>
        </div>
      </div>

      {showAddSourcePanel ? (
        <div className="card" style={{ margin: "0 20px 12px 20px", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
            추가 문서 소스 등록
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <input
              type="text"
              value={addSourceInput}
              onChange={(e) => setAddSourceInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void handleAddSource(); if (e.key === "Escape") setShowAddSourcePanel(false); }}
              placeholder="예: .omc/plans"
              autoFocus
              disabled={isAddingSource}
              style={{ flex: "1 1 320px", minWidth: 200, padding: "6px 10px", fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}
            />
            <button className="btn btn-ghost btn-sm" onClick={() => void handleBrowseForSource()} disabled={isAddingSource} title="네이티브 폴더 선택기 (숨김 폴더는 OS 기본 단축키로 표시 필요)">
              탐색
            </button>
            <button className="btn btn-sm" onClick={() => void handleAddSource()} disabled={isAddingSource || !addSourceInput.trim()}>
              {isAddingSource ? "등록 중..." : "등록"}
            </button>
          </div>
          <div style={{ fontSize: 11, color: "#666", marginTop: 6, lineHeight: 1.5 }}>
            프로젝트 루트 기준 상대 경로. 숨김 폴더(.omc/plans 등)는 직접 입력하세요.
          </div>
        </div>
      ) : null}

      <div
        ref={layoutRef}
        className="page-content"
        style={{ display: "grid", gridTemplateColumns: showSidebar ? "280px minmax(0, 1fr)" : "minmax(0, 1fr)", gap: 16 }}
      >
        {showSidebar ? <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <DocsSidebar
            docs={docsIndex}
            query={query}
            selectedPath={selectedPath}
            onQueryChange={setQuery}
            onSelect={setSelectedPath}
            onGenerateReport={onGenerateReport}
          />

          <div className="card">
            <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
              Section Jump
            </div>
            {sections.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {sections.slice(0, 12).map((section) => (
                  <button
                    key={section.id}
                    className="btn btn-ghost btn-sm"
                    style={{ textAlign: "left", justifyContent: "flex-start", paddingLeft: 10 + (section.level - 1) * 10, textTransform: "none", letterSpacing: 0 }}
                    onClick={() => document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                  >
                    {section.text}
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "#666", lineHeight: 1.6 }}>선택한 문서에서 heading을 찾으면 여기서 바로 이동할 수 있습니다.</div>
            )}
          </div>

          <div className="terminal" style={{ marginBottom: 0 }}>
            <div className="terminal-header">
              <div className="terminal-dot red" />
              <div className="terminal-dot yellow" />
              <div className="terminal-dot green" />
            </div>
            <div><span className="terminal-prompt">project</span>: {projectDir}</div>
            <div><span className="terminal-prompt">docs</span>: {docsIndex.length}</div>
            <div><span className="terminal-prompt">path</span>: {doc?.path ?? selectedPath ?? "none"}</div>
            <div><span className="terminal-prompt">source_hash</span>: {doc?.source_hash ?? "pending"}</div>
          </div>

          <div className="card">
            <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
              추가 문서 소스
            </div>
            {extraSources.length === 0 ? (
              <div style={{ fontSize: 12, color: "#666", lineHeight: 1.6 }}>
                등록된 추가 소스 없음
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {extraSources.map((source) => (
                  <div key={source} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 11, flex: 1, wordBreak: "break-all", color: "#8B4DFF", fontWeight: 600 }}>{source}</span>
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ fontSize: 10, padding: "2px 6px" }}
                      onClick={() => void handleRemoveSource(source)}
                      title={`${source} 제거`}
                    >
                      제거
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div> : null}

        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          {indexError ? (
            <div className="alert alert-error">문서 인덱스 로딩 실패: {indexError}</div>
          ) : null}
          {error ? (
            <div className="alert alert-error">문서 로딩 실패: {error}</div>
          ) : null}
          <div className="card docs-view-tabs" style={{ padding: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(["source", "easy", "canvas"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                className={`btn btn-ghost btn-sm docs-view-tab ${viewMode === mode ? "active" : ""}`.trim()}
                onClick={() => setViewMode(mode)}
              >
                {mode === "source" ? "Source" : mode === "easy" ? "Easy" : "Canvas"}
              </button>
            ))}
            {rawHtmlCanvasEnabled ? (
              <button
                type="button"
                className={`btn btn-ghost btn-sm docs-view-tab ${viewMode === "raw-html" ? "active" : ""}`.trim()}
                onClick={() => setViewMode("raw-html")}
              >
                Raw HTML
              </button>
            ) : null}
            <button
              type="button"
              className={`btn btn-ghost btn-sm docs-view-tab ${viewMode === "split" ? "active" : ""}`.trim()}
              onClick={() => setViewMode("split")}
            >
              Split
            </button>
          </div>
          <div className={`alert ${trustTone.className}`.trim()} style={trustTone.className ? undefined : { background: "#E8E4D8", color: "#1A1A1A" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
              <span>{trustTone.label}</span>
              <span style={{ fontSize: 11 }}>{canvas.status}</span>
            </div>
            <div style={{ marginTop: 6, fontWeight: 600, lineHeight: 1.5 }}>{canvas.reason}</div>
            <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <CanvasGenerateButton status={canvas.status} onGenerate={() => void canvas.generate()} onCancel={canvas.cancel} disabled={!selectedPath || !doc || isRefreshing} />
              <span style={{ fontSize: 11, opacity: 0.8 }}>fancy layer가 실패해도 원문 문서는 계속 읽을 수 있습니다.</span>
            </div>
          </div>
          {rebuildMessage ? <div className="alert alert-warn">{rebuildMessage}</div> : null}
          {isLoading ? (
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "IBM Plex Mono, monospace", fontSize: 12, fontWeight: 700 }}>
                <span className="spinner" />
                문서를 불러오는 중...
              </div>
            </div>
          ) : null}

          {!isLoading && !indexError && !error && doc && selectedDoc ? (
            <>
              <div className="card" style={{ padding: "14px 16px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
                  Open-Time Validation
                </div>
                <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 4 }}>{selectedDoc.title}</div>
                <div style={{ fontSize: 12, color: "#555" }}>{selectedDoc.category} · {selectedDoc.path}</div>
                {canvas.visual ? (
                  <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, fontSize: 11 }}>
                    <div><strong>sections</strong><div>{canvas.visual.artifact.sections.length}</div></div>
                    <div><strong>actions</strong><div>{canvas.visual.artifact.action_items.length}</div></div>
                    <div><strong>diagrams</strong><div>{canvas.visual.artifact.diagram_blocks.length}</div></div>
                  </div>
                ) : null}
              </div>
              {viewMode === "source" ? (
                <DocumentPane path={doc.path} content={doc.content} containerRef={markdownPaneRef} />
              ) : null}
              {viewMode === "easy" ? (
                canvas.visual ? (
                  <VisualSummaryPane
                    artifact={canvas.visual.artifact}
                    trustState={canvas.trustState}
                    onPhaseSelect={handlePhaseSelect}
                    projectRoot={projectDir}
                    relativePath={selectedPath ?? ""}
                    onArtifactRefresh={() => void canvas.refreshArtifact()}
                  />
                ) : <div className="card">Easy View는 Canvas artifact 생성 후 표시됩니다.</div>
              ) : null}
              {viewMode === "canvas" ? (
                <CanvasViewPane artifact={canvas.visual?.artifact ?? null} status={canvas.status} reason={canvas.reason} />
              ) : null}
              {viewMode === "raw-html" ? (
                <RawHtmlCanvasPane html={canvas.html} status={canvas.htmlStatus} reason={canvas.htmlReason} />
              ) : null}
              {viewMode === "split" ? (
                <div style={{ display: "grid", gridTemplateColumns: splitGridColumns, gap: 12, alignItems: "start" }}>
                  <DocumentPane path={doc.path} content={doc.content} containerRef={markdownPaneRef} />
                  <CanvasViewPane artifact={canvas.visual?.artifact ?? null} status={canvas.status} reason={canvas.reason} layout="split" />
                </div>
              ) : null}
              {enhancementPartiallyDisabled ? (
                <div className="alert alert-warn">문서가 길어서 일부 enhancement만 축약했습니다. 그래도 summary pane과 원문 문서는 계속 표시됩니다.</div>
              ) : null}
            </>
          ) : (!isLoading && !indexError && !error ? <div className="card">열 문서를 선택하세요.</div> : null)}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: DOCSVIEWER_END ===
