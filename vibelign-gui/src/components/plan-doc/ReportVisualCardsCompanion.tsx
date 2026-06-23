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
  type ReportVisualCardsProviderId,
} from "../../lib/vib/reportVisualCards";
import { GyariProgressBar } from "./GyariProgressBar";
import { ReportVisualCardsPanel } from "./ReportVisualCardsPanel";
import { ReportVisualSketch } from "./ReportVisualSketch";
import { normalizeReportAssistProviderId, type ReportAssistProviderOption } from "./reportAssistProviders";

type ReportVisualCardsCompanionProps = {
  readonly cwd: string;
  readonly planPath: string;
  readonly reportType: ReportType;
  readonly provider: ReportVisualCardsProviderId;
  readonly providerOptions: readonly ReportAssistProviderOption[];
  readonly onProviderChange: (provider: ReportVisualCardsProviderId) => void;
};

export function ReportVisualCardsCompanion({
  cwd,
  planPath,
  reportType,
  provider,
  providerOptions,
  onProviderChange,
}: ReportVisualCardsCompanionProps): ReactNode {
  const [payload, setPayload] = useState<ReportVisualCardsPayload | null>(null);
  const [approvedCards, setApprovedCards] = useState<readonly ReportVisualCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [exportResult, setExportResult] = useState<ReportCardNewsExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);
  const [mode, setMode] = useState<"per-card" | "poster">("per-card");
  const [poster, setPoster] = useState<{ html: string; source: "llm" | "fallback" } | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  // Sketch-first per-card storyboard sketches shown while the slow asset stage runs (per-card
  // mode only), swapped for the final cards on resolve. No poster placeholder: in poster mode a
  // deterministic placeholder looked identical to a prior result, so generation shows only the
  // progress bar.
  const [liveDraft, setLiveDraft] = useState<ReportVisualCardsPayload | null>(null);

  useEffect(() => {
    setPayload(null);
    setApprovedCards([]);
    setExportResult(null);
    setError(null);
    setOpenError(null);
    setPoster(null);
    setLiveDraft(null);
    // Also reset when the model (provider) or the mode changes: a poster/cards made with the
    // previous model — or in the other mode — are stale, so don't keep showing them after the
    // user switches. (Switching poster→per-card otherwise surfaced the poster-run draft cards.)
  }, [planPath, reportType, provider, mode]);

  const requestCards = async (): Promise<void> => {
    setLoading(true);
    setStage(null);
    setError(null);
    setLiveDraft(null);
    let result;
    try {
      result = await requestReportVisualCards(cwd, planPath, reportType, provider, mode, (p) => {
        if (p.stage) setStage(p.stage);
        if (p.draft) setLiveDraft(p.draft);
      });
    } finally {
      setStage(null);
      setLoading(false);
      setLiveDraft(null);
    }
    if (!result.ok) {
      setPayload(null);
      setApprovedCards([]);
      setExportResult(null);
      setPoster(null);
      setError(result.error);
      return;
    }
    setPayload(result.payload);
    setPoster(result.poster ?? null);
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
    const result = await saveReportVisualCards(cwd, { ...payload, cards, ...(poster ? { poster_html: poster.html } : {}) });
    setFinalizing(false);
    setExportResult(result);
    if (!result.ok) setError(result.error);
  };

  const finalizePoster = (): void => {
    if (payload === null || poster === null) return;
    void finalizeCards(payload.cards.map((c) => ({ ...c, approved: true })));
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
        <div style={requestControls}>
          <select
            aria-label="카드뉴스 초안 모델"
            value={provider}
            onChange={(event) => onProviderChange(normalizeReportAssistProviderId(event.target.value))}
            disabled={loading}
            style={select}
          >
            {providerOptions.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
          <select
            aria-label="카드뉴스 생성 방식"
            value={mode}
            onChange={(e) => setMode(e.target.value === "poster" ? "poster" : "per-card")}
            disabled={loading}
            style={select}
          >
            <option value="per-card">카드별 일러스트</option>
            <option value="poster">전체 디자인 통째</option>
          </select>
          <button type="button" onClick={() => void requestCards()} disabled={loading} style={requestButton}>
            {loading ? "카드뉴스 만드는 중..." : "카드뉴스 초안 만들기"}
          </button>
        </div>
      </div>
      <p style={copy}>보고서 메시지를 3-6장 카드로 나누고, 한국어 문구는 편집 가능한 오버레이로 유지합니다.</p>
      {loading && (() => {
        const stageUi = stage ? STAGE_UI[stage] ?? { pct: 8, label: "준비 중" } : { pct: 8, label: "준비 중" };
        return <GyariProgressBar ariaLabel="카드뉴스 생성 진행" pct={stageUi.pct} label={stageUi.label} />;
      })()}
      {loading && liveDraft !== null && mode === "per-card" && (
        <div style={resultBox}>
          <p style={resultTitle}>스토리보드 미리보기 · 일러스트 생성 중</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 8 }}>
            {liveDraft.cards.map((card, index) => (
              <div key={card.id} style={{ border: "2px dashed #1A1A1A", borderRadius: 8, padding: 6, background: "#FFFFFF" }}>
                <ReportVisualSketch card={card} />
                <p style={{ margin: "6px 0 0", fontSize: 12, fontWeight: 700, lineHeight: 1.3 }}>{index + 1}. {card.title}</p>
              </div>
            ))}
          </div>
        </div>
      )}
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
      {poster !== null && (
        <div style={resultBox}>
          <p style={resultTitle}>모델 포스터 프리뷰 · {poster.source === "llm" ? "모델 생성" : "폴백"}</p>
          <iframe
            title="카드뉴스 포스터 프리뷰"
            sandbox=""
            srcDoc={poster.html}
            style={{ width: "100%", height: 520, border: "2px solid #1A1A1A", background: "#FFFFFF" }}
          />
          {mode === "poster" && (
            <div style={resultActions}>
              <button type="button" onClick={finalizePoster} disabled={finalizing} style={requestButton}>
                {finalizing ? "저장 중..." : "카드뉴스 확정"}
              </button>
            </div>
          )}
        </div>
      )}
      {mode === "per-card" && payload !== null && (
        <>
          <p style={countText}>승인된 카드 {approvedCards.length}개</p>
          <ReportVisualCardsPanel
            cwd={cwd}
            payload={payload}
            onExportChange={setApprovedCards}
            onFinalize={(cards) => void finalizeCards(cards)}
          />
          {finalizing && <p style={countText}>카드뉴스 결과물을 저장하는 중...</p>}
        </>
      )}
      {mode === "poster" && payload !== null && poster === null && (
        <p style={countText}>포스터 모드는 모델(Claude 등)을 선택해야 포스터가 생성됩니다.</p>
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

const STAGE_UI: Record<string, { pct: number; label: string }> = {
  draft: { pct: 30, label: "초안 만드는 중" },
  assets: { pct: 60, label: "카드 이미지 그리는 중" },
  poster: { pct: 88, label: "포스터 디자인 중 (조금 걸려요)" },
};

const shell: CSSProperties = {
  minWidth: 0,
  width: "100%",
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
const requestControls: CSSProperties = { display: "grid", gridTemplateColumns: "1fr", flex: "1 1 100%", width: "100%", minWidth: 0, gap: 8 };
const select: CSSProperties = { width: "100%", minWidth: 0, boxSizing: "border-box", border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 8px", fontSize: 12, fontWeight: 800 };
const button: CSSProperties = { maxWidth: "100%", boxSizing: "border-box", border: "2px solid #1A1A1A", background: "#F5621E", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer", boxShadow: "2px 2px 0 #1A1A1A" };
const requestButton: CSSProperties = { ...button, width: "100%" };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer", boxShadow: "2px 2px 0 #1A1A1A" };
const errorText: CSSProperties = { margin: "8px 0 0", color: "#9B1B1B", fontSize: 12 };
const countText: CSSProperties = { margin: "8px 0", fontSize: 12, fontWeight: 800 };
const resultBox: CSSProperties = { marginTop: 10, border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 10 };
const resultTitle: CSSProperties = { margin: 0, fontSize: 12, fontWeight: 900 };
const resultActions: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 };
const pathText: CSSProperties = { margin: "6px 0 8px", color: "#666666", fontSize: 11, overflowWrap: "anywhere" };
// === ANCHOR: REPORT_VISUAL_CARDS_COMPANION_END ===
