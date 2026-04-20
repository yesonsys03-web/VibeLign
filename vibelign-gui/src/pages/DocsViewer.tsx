// === ANCHOR: DOCSVIEWER_START ===
import { useEffect, useMemo, useRef, useState } from "react";
import DocsSidebar from "../components/docs/DocsSidebar";
import MarkdownPane from "../components/docs/MarkdownPane";
import VisualSummaryPane from "../components/docs/VisualSummaryPane";
import { extractSections, loadDoc, reloadDocsIndex } from "../lib/docs";
import { addExtraDocSource, listExtraDocSources, pickFolder, readDocsVisual, removeExtraDocSource, runVib, type DocsIndexEntry, type DocsVisualReadResult, type ReadFileResult } from "../lib/vib";

export type DocsTrustState = "markdown-only" | "enhanced-synced" | "enhanced-stale" | "enhanced-failed";

interface DocsViewerProps {
  projectDir: string;
}

export default function DocsViewer({ projectDir }: DocsViewerProps) {
  const [docsIndex, setDocsIndex] = useState<DocsIndexEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [doc, setDoc] = useState<ReadFileResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [indexLoading, setIndexLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [visual, setVisual] = useState<DocsVisualReadResult | null>(null);
  const [trustState, setTrustState] = useState<DocsTrustState>("markdown-only");
  const [trustReason, setTrustReason] = useState<string>("artifact 없음 — markdown만 표시합니다.");
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
  const [rebuildMessage, setRebuildMessage] = useState<string | null>(null);
  const [extraSources, setExtraSources] = useState<string[]>([]);
  const [isAddingSource, setIsAddingSource] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const markdownPaneRef = useRef<HTMLDivElement | null>(null);
  const layoutRef = useRef<HTMLDivElement | null>(null);
  const [layoutWidth, setLayoutWidth] = useState(0);

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

    listExtraDocSources(projectDir)
      .then((res) => {
        if (cancelled) return;
        setDocsIndex(res.entries);
        setExtraSources(res.sources);
        setSelectedPath((current) => {
          if (current && res.entries.some((entry) => entry.path === current)) {
            return current;
          }
          return res.entries.find((entry) => entry.path === "PROJECT_CONTEXT.md")?.path ?? res.entries[0]?.path ?? null;
        });
        setIndexLoading(false);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setDocsIndex([]);
          setExtraSources([]);
          setSelectedPath(null);
          setIndexError(err instanceof Error ? err.message : typeof err === "string" ? err : "문서 인덱스를 읽을 수 없어요");
          setIndexLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectDir]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      setDoc(null);
      setVisual(null);
      setError(null);
      setTrustState("markdown-only");
      setTrustReason("문서를 선택하면 trust 상태를 계산합니다.");
      setIsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setIsLoading(true);
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

  useEffect(() => {
    let cancelled = false;
    if (!projectDir || !selectedPath || !doc) {
      setVisual(null);
      setTrustState("markdown-only");
      setTrustReason("artifact 없음 — markdown만 표시합니다.");
      return () => {
        cancelled = true;
      };
    }

    setVisual(null);
    setTrustState("markdown-only");
    setTrustReason("artifact를 확인 중입니다...");
    setRebuildMessage(null);

    readDocsVisual(projectDir, selectedPath)
      .then((result) => {
        if (cancelled) return;
        if (!result) {
          setVisual(null);
          setTrustState("markdown-only");
          setTrustReason("artifact가 아직 없어 markdown만 표시합니다.");
          return;
        }

        setVisual(result);

        if (result.artifact.schema_version !== result.contract.schema_version) {
          setTrustState("enhanced-stale");
          setTrustReason(`schema_version 불일치: artifact ${result.artifact.schema_version} / contract ${result.contract.schema_version}`);
          return;
        }

        if (result.artifact.generator_version !== result.contract.generator_version) {
          setTrustState("enhanced-stale");
          setTrustReason(`generator_version 불일치: artifact ${result.artifact.generator_version} / contract ${result.contract.generator_version}`);
          return;
        }

        if (result.artifact.source_hash !== doc.source_hash) {
          setTrustState("enhanced-stale");
          setTrustReason("authoritative markdown hash와 artifact hash가 달라 stale 상태입니다.");
          return;
        }

        setTrustState("enhanced-synced");
        setTrustReason("open-time validation 통과 — 현재 enhancement는 최신 markdown와 동기화되었습니다.");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setVisual(null);
        setTrustState("enhanced-failed");
        setTrustReason(err instanceof Error ? err.message : "artifact를 읽거나 검증하지 못했습니다.");
      });

    return () => {
      cancelled = true;
    };
  }, [projectDir, selectedPath, doc, refreshTick]);

  const trustTone = useMemo(() => {
    if (trustState === "enhanced-synced") return { className: "alert-success", label: "ENHANCED SYNCED" };
    if (trustState === "enhanced-stale") return { className: "alert-warn", label: "ENHANCED STALE" };
    if (trustState === "enhanced-failed") return { className: "alert-error", label: "ENHANCED FAILED" };
    return { className: "", label: "MARKDOWN ONLY" };
  }, [trustState]);

  const enhancementPartiallyDisabled = useMemo(
    () => visual?.artifact.warnings?.some((warning) => warning.startsWith("enhancement_partial_disabled:")) ?? false,
    [visual],
  );
  const isMinimalLayout = layoutWidth > 0 && layoutWidth < 900;
  const showSidebar = !isMinimalLayout;
  const showVisualPane = Boolean(visual && trustState !== "enhanced-failed");

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

  // === ANCHOR: DOCSVIEWER_HANDLEREBUILDARTIFACT_START ===
  async function handleRebuildArtifact() {
    if (!selectedPath || !projectDir) return;
    setIsRebuilding(true);
    setRebuildMessage(null);
    try {
      const result = await runVib(["docs-build", selectedPath], projectDir);
      if (!result.ok) {
        throw new Error(result.stderr || result.stdout || `exit ${result.exit_code}`);
      }
      setRebuildMessage("docs visual artifact를 다시 생성했고 최신 문서/artifact를 다시 읽었습니다.");
      setRefreshTick((value) => value + 1);
    } catch (err: unknown) {
      setRebuildMessage(err instanceof Error ? err.message : "artifact 재생성에 실패했습니다.");
    } finally {
      setIsRebuilding(false);
    }
  }
  // === ANCHOR: DOCSVIEWER_HANDLEREBUILDARTIFACT_END ===

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
    if (a === r) return null;
    if (a.startsWith(r + "/")) return a.slice(r.length + 1);
    return null;
  }
  // === ANCHOR: DOCSVIEWER_RELATIVIZE_END ===

  // === ANCHOR: DOCSVIEWER_HANDLEADDSOURCE_START ===
  async function handleAddSource() {
    if (!projectDir) return;
    // 1차: 상대 경로 직접 입력(네이티브 선택기는 숨김 폴더가 안 보여서
    // .omc/plans 같은 기본 유스케이스가 막힘). 비우고 확인하면 탐색기 폴백.
    const typed = window.prompt(
      "등록할 상대 경로를 입력하세요 (예: .omc/plans). 비워두면 폴더 탐색기로 열립니다.",
      "",
    );
    if (typed === null) return;
    setIsAddingSource(true);
    setRebuildMessage(null);
    try {
      let rel = typed.trim();
      if (!rel) {
        const picked = await pickFolder(projectDir);
        if (!picked) { setIsAddingSource(false); return; }
        const derived = relativizeInsideProject(projectDir, picked);
        if (!derived) {
          setRebuildMessage("프로젝트 루트 안쪽 폴더만 추가할 수 있어요.");
          return;
        }
        rel = derived;
      }
      const res = await addExtraDocSource(projectDir, rel);
      setDocsIndex(res.entries);
      setExtraSources(res.sources);
      setRebuildMessage(`추가 문서 소스 등록: ${rel} (${res.entries.length}개 문서)`);
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
          <button className="btn btn-ghost btn-sm" onClick={() => void handleRebuildIndex()} disabled={isRebuildingIndex || isRebuilding || isRefreshing} title="문서 인덱스를 다시 스캔해 사이드바 목록을 갱신해요">
            {isRebuildingIndex ? "인덱스 갱신 중..." : "↻ 인덱스"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleAddSource()} disabled={isAddingSource || isRebuildingIndex} title="추가 문서 소스 폴더를 등록해요">
            {isAddingSource ? "추가 중..." : "+ 소스 추가"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleRefreshCurrent()} disabled={isRefreshing || isRebuilding || !selectedPath}>
            {isRefreshing ? "새로고침 중..." : "Refresh"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleRebuildArtifact()} disabled={isRebuilding || isRefreshing || !selectedPath}>
            {isRebuilding ? "재생성 중..." : "Rebuild"}
          </button>
          <span style={{ fontSize: 11, color: "#666", fontWeight: 700 }}>PHASE 10</span>
        </div>
      </div>

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
          <div className={`alert ${trustTone.className}`.trim()} style={trustTone.className ? undefined : { background: "#E8E4D8", color: "#1A1A1A" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
              <span>{trustTone.label}</span>
              <span style={{ fontSize: 11 }}>{trustState}</span>
            </div>
            <div style={{ marginTop: 6, fontWeight: 600, lineHeight: 1.5 }}>{trustReason}</div>
            {trustState !== "enhanced-synced" ? (
              <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <button className="btn btn-ghost btn-sm" onClick={() => void handleRebuildArtifact()} disabled={isRebuilding || !selectedPath}>
                  {isRebuilding ? "재생성 중..." : "artifact 다시 만들기"}
                </button>
                <span style={{ fontSize: 11, opacity: 0.8 }}>fancy layer가 실패해도 markdown 원문은 계속 읽을 수 있습니다.</span>
              </div>
            ) : null}
          </div>
          {rebuildMessage ? <div className="alert alert-warn">{rebuildMessage}</div> : null}
          {isLoading ? (
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "IBM Plex Mono, monospace", fontSize: 12, fontWeight: 700 }}>
                <span className="spinner" />
                markdown 문서를 불러오는 중...
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
                {visual ? (
                  <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, fontSize: 11 }}>
                    <div><strong>sections</strong><div>{visual?.artifact.sections.length}</div></div>
                    <div><strong>actions</strong><div>{visual?.artifact.action_items.length}</div></div>
                    <div><strong>diagrams</strong><div>{visual?.artifact.diagram_blocks.length}</div></div>
                  </div>
                ) : null}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: showVisualPane && !isMinimalLayout ? "minmax(0, 1.2fr) minmax(320px, 0.8fr)" : "minmax(0, 1fr)", gap: 12, alignItems: "start" }}>
                <div style={{ minHeight: 0 }}>
                  <MarkdownPane content={doc.content} containerRef={markdownPaneRef} />
                </div>
                {showVisualPane && visual ? (
                  <div style={{ minWidth: 0 }}>
                    <VisualSummaryPane
                      artifact={visual.artifact}
                      trustState={trustState}
                      onPhaseSelect={handlePhaseSelect}
                      projectRoot={projectDir}
                      relativePath={selectedPath ?? ""}
                      onArtifactRefresh={() => setRefreshTick((t) => t + 1)}
                    />
                  </div>
                ) : null}
              </div>
              {enhancementPartiallyDisabled ? (
                <div className="alert alert-warn">문서가 길어서 일부 enhancement만 축약했습니다. 그래도 summary pane과 원문 markdown는 계속 표시됩니다.</div>
              ) : null}
            </>
          ) : (!isLoading && !indexError && !error ? <div className="card">열 문서를 선택하세요.</div> : null)}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: DOCSVIEWER_END ===
