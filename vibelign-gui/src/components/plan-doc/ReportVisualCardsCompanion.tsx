// === ANCHOR: REPORT_VISUAL_CARDS_COMPANION_START ===
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { openPath } from "@tauri-apps/plugin-opener";

import type { ReportType } from "../../lib/vib/report";
import {
  requestReportVisualCards,
  saveReportVisualCards,
  type ReportVisualCard,
  type ReportCardNewsExportResult,
  type ReportVisualCardsPayload,
} from "../../lib/vib/reportVisualCards";
import { ReportVisualCardsPanel } from "./ReportVisualCardsPanel";

type ReportVisualCardsCompanionProps = {
  readonly cwd: string;
  readonly planPath: string;
  readonly reportType: ReportType;
};

export function ReportVisualCardsCompanion({
  cwd,
  planPath,
  reportType,
}: ReportVisualCardsCompanionProps): ReactNode {
  const [payload, setPayload] = useState<ReportVisualCardsPayload | null>(null);
  const [approvedCards, setApprovedCards] = useState<readonly ReportVisualCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [exportResult, setExportResult] = useState<ReportCardNewsExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  useEffect(() => {
    setPayload(null);
    setApprovedCards([]);
    setExportResult(null);
    setError(null);
    setOpenError(null);
  }, [planPath, reportType]);

  const requestCards = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    const result = await requestReportVisualCards(cwd, planPath, reportType);
    setLoading(false);
    if (!result.ok) {
      setPayload(null);
      setApprovedCards([]);
      setExportResult(null);
      setError(result.error);
      return;
    }
    setPayload(result.payload);
    setExportResult(null);
  };

  const finalizeCards = async (cards: readonly ReportVisualCard[]): Promise<void> => {
    if (payload === null) return;
    if (cards.length === 0) {
      setError("확정할 승인 카드가 없습니다. 먼저 카드를 승인하세요.");
      return;
    }
    setFinalizing(true);
    setError(null);
    setOpenError(null);
    const result = await saveReportVisualCards(cwd, { ...payload, cards });
    setFinalizing(false);
    setExportResult(result);
    if (!result.ok) setError(result.error);
  };

  const openHtml = async (path: string): Promise<void> => {
    setOpenError(null);
    if (!isProjectCardNewsHtml(cwd, path)) {
      setOpenError("카드뉴스 HTML 경로가 현재 프로젝트의 결과물 폴더가 아니에요.");
      return;
    }
    try {
      await openPath(path);
    } catch (error) {
      if (error instanceof Error) {
        setOpenError(`카드뉴스 HTML을 열지 못했어요: ${error.message}`);
        return;
      }
      throw error;
    }
  };

  const openPromptDir = async (path: string): Promise<void> => {
    setOpenError(null);
    if (!isProjectCardNewsPromptDir(cwd, path)) {
      setOpenError("프롬프트 폴더가 현재 프로젝트의 카드뉴스 결과물 폴더가 아니에요.");
      return;
    }
    try {
      await openPath(path);
    } catch (error) {
      if (error instanceof Error) {
        setOpenError(`프롬프트 폴더를 열지 못했어요: ${error.message}`);
        return;
      }
      throw error;
    }
  };

  return (
    <section aria-label="카드뉴스 companion 요청" style={shell}>
      <div style={header}>
        <div>
          <div style={eyebrow}>companion</div>
          <h3 style={title}>카드뉴스 출력</h3>
        </div>
        <button type="button" onClick={() => void requestCards()} disabled={loading} style={button}>
          {loading ? "요청 중..." : "카드뉴스 초안 만들기"}
        </button>
      </div>
      <p style={copy}>보고서 메시지를 3-6장 카드로 나누고, 한국어 문구는 편집 가능한 오버레이로 유지합니다.</p>
      {error !== null && <p role="alert" style={errorText}>{error}</p>}
      {exportResult !== null && exportResult.ok && (
        <div style={resultBox}>
          <p style={resultTitle}>카드뉴스 결과물 {exportResult.cardCount}장</p>
          <p style={pathText}>{exportResult.htmlPath}</p>
          <div style={resultActions}>
            <button type="button" onClick={() => void openHtml(exportResult.htmlPath)} style={button}>
              HTML 열기
            </button>
            {exportResult.promptDir.length > 0 && (
              <button type="button" onClick={() => void openPromptDir(exportResult.promptDir)} style={secondaryButton}>
                프롬프트 폴더 열기
              </button>
            )}
          </div>
          {exportResult.promptDir.length > 0 && <p style={pathText}>{exportResult.promptDir}</p>}
          {openError !== null && <p role="alert" style={errorText}>{openError}</p>}
        </div>
      )}
      {payload !== null && (
        <>
          <p style={countText}>승인된 카드 {approvedCards.length}개</p>
          <ReportVisualCardsPanel
            payload={payload}
            onExportChange={setApprovedCards}
            onFinalize={(cards) => void finalizeCards(cards)}
          />
          {finalizing && <p style={countText}>카드뉴스 결과물을 저장하는 중...</p>}
        </>
      )}
    </section>
  );
}

function isProjectCardNewsHtml(cwd: string, path: string): boolean {
  const normalizedCwd = cwd.replaceAll("\\", "/").replace(/\/+$/, "");
  const normalizedPath = path.replaceAll("\\", "/");
  const expectedPrefix = `${normalizedCwd}/.vibelign/reports/card-news/`;
  return normalizedPath.startsWith(expectedPrefix) && normalizedPath.endsWith(".html") && !normalizedPath.includes("/../");
}

function isProjectCardNewsPromptDir(cwd: string, path: string): boolean {
  const normalizedCwd = cwd.replaceAll("\\", "/").replace(/\/+$/, "");
  const normalizedPath = path.replaceAll("\\", "/").replace(/\/+$/, "");
  const expectedPrefix = `${normalizedCwd}/.vibelign/reports/card-news/prompts/`;
  return normalizedPath.startsWith(expectedPrefix) && !normalizedPath.includes("/../");
}

const shell: CSSProperties = {
  minWidth: 0,
  maxWidth: "100%",
  boxSizing: "border-box",
  border: "2px solid #1A1A1A",
  background: "#FEFBF0",
  padding: 16,
  boxShadow: "4px 4px 0 #1A1A1A",
};
const header: CSSProperties = { display: "flex", flexWrap: "wrap", alignItems: "start", justifyContent: "space-between", gap: 8 };
const eyebrow: CSSProperties = { fontSize: 11, fontWeight: 800, color: "#999999" };
const title: CSSProperties = { margin: 0, fontSize: 16, lineHeight: 1.2 };
const copy: CSSProperties = { margin: "8px 0 0", fontSize: 12, lineHeight: 1.5 };
const button: CSSProperties = { border: "2px solid #1A1A1A", background: "#F5621E", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer", boxShadow: "2px 2px 0 #1A1A1A" };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer", boxShadow: "2px 2px 0 #1A1A1A" };
const errorText: CSSProperties = { margin: "8px 0 0", color: "#9B1B1B", fontSize: 12 };
const countText: CSSProperties = { margin: "8px 0", fontSize: 12, fontWeight: 800 };
const resultBox: CSSProperties = { marginTop: 10, border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 10 };
const resultTitle: CSSProperties = { margin: 0, fontSize: 12, fontWeight: 900 };
const resultActions: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 };
const pathText: CSSProperties = { margin: "6px 0 8px", color: "#666666", fontSize: 11, overflowWrap: "anywhere" };
// === ANCHOR: REPORT_VISUAL_CARDS_COMPANION_END ===
