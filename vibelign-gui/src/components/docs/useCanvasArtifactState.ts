import { useCallback, useEffect, useRef, useState } from "react";
import { readDocsHtml, readDocsVisual, runVib, type DocsHtmlReadResult, type DocsVisualReadResult, type ReadFileResult } from "../../lib/vib";
import { evaluateCanvasArtifactTrust, type CanvasStatus, type DocsTrustState } from "./canvasArtifactTrust";

interface UseCanvasArtifactStateArgs {
  projectDir: string;
  selectedPath: string | null;
  doc: ReadFileResult | null;
}

interface CanvasArtifactState {
  visual: DocsVisualReadResult | null;
  html: DocsHtmlReadResult | null;
  status: CanvasStatus;
  htmlStatus: CanvasStatus;
  trustState: DocsTrustState;
  htmlTrustState: DocsTrustState;
  reason: string;
  htmlReason: string;
  isGenerating: boolean;
  generate: () => Promise<void>;
  cancel: () => void;
  refreshArtifact: () => Promise<void>;
}

function baseState(reason: string): Omit<CanvasArtifactState, "generate" | "cancel" | "refreshArtifact"> {
  return {
    visual: null,
    html: null,
    status: "not_generated",
    htmlStatus: "not_generated",
    trustState: "source-only",
    htmlTrustState: "source-only",
    reason,
    htmlReason: reason,
    isGenerating: false,
  };
}

function isUnsupportedError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : typeof err === "string" ? err : "";
  return /unsupported|excluded/i.test(message);
}

function validateSelectedPath(path: string): void {
  const normalized = path.replaceAll("\\", "/");
  if (normalized.startsWith("-")) {
    throw new Error("Canvas 생성 경로는 '-'로 시작할 수 없습니다.");
  }
  if (normalized.includes("\0") || normalized.split("/").some((segment) => segment === ".." || segment === "")) {
    throw new Error("Canvas 생성 경로가 올바르지 않습니다.");
  }
}

export default function useCanvasArtifactState({ projectDir, selectedPath, doc }: UseCanvasArtifactStateArgs): CanvasArtifactState {
  const epochRef = useRef(0);
  const [state, setState] = useState<Omit<CanvasArtifactState, "generate" | "cancel" | "refreshArtifact">>(
    () => baseState("문서를 선택하면 Canvas 상태를 확인합니다."),
  );

  const applyArtifacts = useCallback((visual: DocsVisualReadResult | null, html: DocsHtmlReadResult | null, currentDoc: ReadFileResult | null) => {
    const trust = evaluateCanvasArtifactTrust(visual, currentDoc);
    const htmlTrust = evaluateCanvasArtifactTrust(html, currentDoc);
    setState({
      visual,
      html,
      status: trust.status === "ready" ? trust.status : htmlTrust.status,
      htmlStatus: htmlTrust.status,
      trustState: trust.trustState === "enhanced-synced" ? trust.trustState : htmlTrust.trustState,
      htmlTrustState: htmlTrust.trustState,
      reason: trust.status === "ready" ? trust.reason : htmlTrust.reason,
      htmlReason: htmlTrust.reason,
      isGenerating: false,
    });
  }, []);

  const refreshArtifact = useCallback(async () => {
    if (!projectDir || !selectedPath || !doc) {
      setState(baseState("문서를 선택하면 Canvas 상태를 확인합니다."));
      return;
    }
    const capturedEpoch = epochRef.current;
    try {
      const [visual, html] = await Promise.all([
        readDocsVisual(projectDir, selectedPath),
        readDocsHtml(projectDir, selectedPath),
      ]);
      if (capturedEpoch !== epochRef.current) return;
      applyArtifacts(visual, html, doc);
    } catch (err: unknown) {
      if (capturedEpoch !== epochRef.current) return;
      setState({
        visual: null,
        html: null,
        status: isUnsupportedError(err) ? "unsupported" : "failed",
        htmlStatus: isUnsupportedError(err) ? "unsupported" : "failed",
        trustState: isUnsupportedError(err) ? "enhanced-stale" : "enhanced-failed",
        htmlTrustState: isUnsupportedError(err) ? "enhanced-stale" : "enhanced-failed",
        reason: err instanceof Error ? err.message : "Canvas artifact를 읽거나 검증하지 못했습니다.",
        htmlReason: err instanceof Error ? err.message : "Raw HTML artifact를 읽거나 검증하지 못했습니다.",
        isGenerating: false,
      });
    }
  }, [applyArtifacts, doc, projectDir, selectedPath]);

  useEffect(() => {
    epochRef.current += 1;
    if (!selectedPath || !doc) {
      setState(baseState(selectedPath ? "원문 문서를 먼저 불러오는 중입니다." : "문서를 선택하면 Canvas 상태를 확인합니다."));
      return;
    }
    void refreshArtifact();
  }, [doc?.source_hash, refreshArtifact, selectedPath]);

  const generate = useCallback(async () => {
    if (!projectDir || !selectedPath || !doc) return;
    const capturedEpoch = epochRef.current + 1;
    epochRef.current = capturedEpoch;
    setState((current) => ({
      ...current,
        status: "generating",
        htmlStatus: "generating",
      trustState: current.trustState,
      reason: "선택한 문서 1건의 Canvas artifact를 생성하는 중입니다.",
      isGenerating: true,
    }));
    try {
      validateSelectedPath(selectedPath);
      const result = await runVib(["docs-build", "--", selectedPath], projectDir);
      if (capturedEpoch !== epochRef.current) return;
      if (!result.ok) {
        throw new Error(result.stderr || result.stdout || `exit ${result.exit_code}`);
      }
      const [visual, html] = await Promise.all([
        readDocsVisual(projectDir, selectedPath),
        readDocsHtml(projectDir, selectedPath),
      ]);
      if (capturedEpoch !== epochRef.current) return;
      applyArtifacts(visual, html, doc);
    } catch (err: unknown) {
      if (capturedEpoch !== epochRef.current) return;
      setState((current) => ({
        ...current,
        status: isUnsupportedError(err) ? "unsupported" : "failed",
        htmlStatus: isUnsupportedError(err) ? "unsupported" : "failed",
        trustState: isUnsupportedError(err) ? "enhanced-stale" : "enhanced-failed",
        htmlTrustState: isUnsupportedError(err) ? "enhanced-stale" : "enhanced-failed",
        reason: err instanceof Error ? err.message : "Canvas artifact 생성에 실패했습니다.",
        htmlReason: err instanceof Error ? err.message : "Raw HTML artifact 생성에 실패했습니다.",
        isGenerating: false,
      }));
    }
  }, [applyArtifacts, doc, projectDir, selectedPath]);

  const cancel = useCallback(() => {
    epochRef.current += 1;
    setState((current) => {
      const trust = evaluateCanvasArtifactTrust(current.visual, doc);
      const htmlTrust = evaluateCanvasArtifactTrust(current.html, doc);
      const status = trust.status === "ready" ? trust.status : htmlTrust.status;
      const trustState = trust.trustState === "enhanced-synced" ? trust.trustState : htmlTrust.trustState;
      const reason = trust.status === "ready" ? trust.reason : htmlTrust.reason;
      return {
        visual: current.visual,
        html: current.html,
        status,
        htmlStatus: htmlTrust.status,
        trustState,
        htmlTrustState: htmlTrust.trustState,
        reason: `생성을 취소했습니다. ${reason}`,
        htmlReason: `생성을 취소했습니다. ${htmlTrust.reason}`,
        isGenerating: false,
      };
    });
  }, [doc]);

  return {
    ...state,
    generate,
    cancel,
    refreshArtifact,
  };
}
