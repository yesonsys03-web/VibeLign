// === ANCHOR: HOME_START ===
import { useState } from "react";
import { GuardResult, vibGuard, listChangedFiles } from "../lib/vib";
import { scopeReport, type ScopeReportResult } from "../lib/home/scopeReport";
import type { PlanningContract } from "../lib/vib";
import { useCardOrder } from "../hooks/useCardOrder";
import { AdvancedHomeCards } from "../components/home/AdvancedHomeCards";
import { GuardResultModal } from "../components/home/GuardResultModal";
import { HomeHeader } from "../components/home/HomeHeader";
import { HomePlanningEntry } from "../components/home/HomePlanningEntry";
import { HomePlanningStart } from "../components/home/HomePlanningStart";
import { ManualCommandDetail } from "../components/home/ManualCommandDetail";
import type { ManualCommand } from "../components/home/ManualCommandList";
import { ManualCommandList } from "../components/home/ManualCommandList";
import { SimpleHome } from "../components/home/SimpleHome";
import { JourneyHowto } from "../components/nav/JourneyHowto";
import type { ActiveGuideStep } from "../lib/nav/guide";
import type { Page } from "../lib/nav/stages";
import pkg from "../../package.json";

type View = "home" | "manual_list" | "manual_detail";

interface HomeProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onNavigate: (page: Page) => void;
  onOpenDoctor?: () => void;
  onOpenSettings?: (reason?: string) => void;
  initialView?: View;
  watchOn?: boolean;
  setWatchOn?: (v: boolean) => void;
  watchError?: string | null;
  onRetryWatch?: () => void;
  hasCheckpoint?: boolean;
  mapMode?: "manual" | "auto";
  setMapMode?: (v: "manual" | "auto") => void;
  planningPrompt?: string;
  planningOutputPath?: string | null;
  planningPending?: boolean;
  onOpenPlanning?: () => void;
  onStartPlanning?: (idea: string) => void;
  readonly onOpenPlanningHistory?: () => void;
  /** guard 실행 결과를 가이드 신호로 올림(spec §3.1). */
  onGuardResult?: (status: "ok" | "issue") => void;
  /** 가이드 현재 단계 — 사용법 따라하기 아코디언 강조용. */
  guideStep?: ActiveGuideStep | null;
  /** 활성 작업 계약 — 범위 비교 리포트용(없으면 리포트 미노출). */
  planningContract?: PlanningContract | null;
}


// ── 컴포넌트 ──────────────────────────────────────────────────────────────────
export default function Home({ projectDir, apiKey, providerKeys, hasAnyAiKey = false, aiKeyStatusLoaded = false, onNavigate, onOpenDoctor, onOpenSettings, initialView = "home", watchOn: watchOnProp, setWatchOn: setWatchOnProp, watchError = null, onRetryWatch, hasCheckpoint = false, mapMode: mapModeProp, setMapMode: setMapModeProp, planningPrompt = "", planningOutputPath = null, planningPending = false, onOpenPlanning, onStartPlanning, onOpenPlanningHistory, onGuardResult, guideStep = null, planningContract = null }: HomeProps) {
  const [view, setView]                   = useState<View>(initialView);
  const [selectedCmd, setSelectedCmd]     = useState<ManualCommand | null>(null);
  const [guardResult, setGuardResult]     = useState<GuardResult | null>(null);
  const [guardModal, setGuardModal] = useState(false);
  const [guardCheckPending, setGuardCheckPending] = useState(false);
  const [guardCheckError, setGuardCheckError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [showNewPlanning, setShowNewPlanning] = useState(false);
  const [scopeReportResult, setScopeReportResult] = useState<ScopeReportResult | null>(null);
  const [watchOnLocal, setWatchOnLocal]   = useState(watchOnProp ?? false);
  const watchOn = watchOnProp ?? watchOnLocal;
  const setWatchOn = (v: boolean) => { setWatchOnLocal(v); setWatchOnProp?.(v); };
  const [mapModeLocal, setMapModeLocal]   = useState<"manual"|"auto">(mapModeProp ?? "manual");
  const mapMode = mapModeProp ?? mapModeLocal;
  const setMapMode = (v: "manual"|"auto") => { setMapModeLocal(v); setMapModeProp?.(v); };

  const { cardOrder, setCardOrder, resetOrder } = useCardOrder();

  // 계약 범위 비교(spec §6) — guard와 같은 순간의 changed-set을 직접 조회.
  // 체크포인트 유무·가이드 v6 구현 여부와 무관(설계 §6 직접 조회 결정).
  // 심플·고급 양 guard 경로 모두에서 호출(stale 방지). 표시는 v1 SimpleHome만(고급 카드 안 표시는 후속).
  async function refreshScopeReport() {
    if (projectDir && planningContract && planningContract.scope.length > 0) {
      try {
        const entries = await listChangedFiles(projectDir);
        setScopeReportResult(scopeReport(planningContract.scope, entries.map((e) => e.path)));
        return;
      } catch {
        // 조회 실패 = 리포트 생략(추측 안내 금지) — 아래 공통 null로
      }
    }
    setScopeReportResult(null);
  }

  async function handleRunGuard() {
    setGuardCheckPending(true);
    setGuardCheckError(null);
    try {
      const result = await vibGuard(projectDir);
      setGuardResult(result);
      onGuardResult?.(result.status === "pass" ? "ok" : "issue");
      await refreshScopeReport();
    } catch (error: unknown) {
      if (error instanceof Error) {
        setGuardCheckError("상태 확인을 끝내지 못했어요. 잠시 뒤 다시 시도해 주세요.");
        return;
      }
      throw error;
    } finally {
      setGuardCheckPending(false);
    }
  }

  // ── 메뉴얼 커맨드 상세 뷰 ────────────────────────────────────────────────────
  if (view === "manual_detail" && selectedCmd) {
    return <ManualCommandDetail command={selectedCmd} onBack={() => setView("manual_list")} />;
  }

  // ── 메뉴얼 커맨드 목록 뷰 ────────────────────────────────────────────────────
  if (view === "manual_list") {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div style={{ flexShrink: 0 }}>
          <JourneyHowto currentStep={guideStep} onNavigate={onNavigate} />
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <ManualCommandList
            onBack={() => setView("home")}
            onSelectCommand={(command) => {
              setSelectedCmd(command);
              setView("manual_detail");
            }}
          />
        </div>
      </div>
    );
  }

  // ── 홈 메인 뷰 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {guardModal && guardResult && (
        <GuardResultModal
          guardResult={guardResult}
          onClose={() => setGuardModal(false)}
          onOpenDoctor={onOpenDoctor}
        />
      )}

      <HomeHeader
        version={pkg.version}
        advancedOpen={advancedOpen}
        onResetOrder={resetOrder}
        onShowSimple={() => setAdvancedOpen(false)}
      />

      <div className="page-content" style={{ padding: "12px 20px 20px" }}>
        {planningPrompt && onOpenPlanning ? (
          <>
            <HomePlanningEntry
              prompt={planningPrompt}
              outputPath={planningOutputPath}
              isPending={planningPending}
              onOpen={onOpenPlanning}
            />
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              {onStartPlanning && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowNewPlanning((v) => !v)} style={{ fontSize: 11 }}>
                  + 새 기획
                </button>
              )}
              {onOpenPlanningHistory && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPlanningHistory} style={{ fontSize: 11 }}>
                  이전 기획 불러오기
                </button>
              )}
            </div>
            {showNewPlanning && onStartPlanning && <HomePlanningStart onStart={onStartPlanning} />}
          </>
        ) : (
          <>
            {onStartPlanning && <HomePlanningStart onStart={onStartPlanning} />}
            {onOpenPlanningHistory && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPlanningHistory} style={{ fontSize: 11 }}>
                이전 기획 불러오기
              </button>
            )}
          </>
        )}
        {!advancedOpen && (
          <SimpleHome
            guardResult={guardResult}
            watchOn={watchOn}
            watchError={watchError}
            hasCheckpoint={hasCheckpoint}
            guardCheckPending={guardCheckPending}
            guardCheckError={guardCheckError}
            scopeReport={scopeReportResult}
            onRetryWatch={() => {
              onRetryWatch?.();
            }}
            onRunGuard={() => {
              void handleRunGuard();
            }}
            onShowAdvanced={() => setAdvancedOpen(true)}
            onNavigateBackups={() => onNavigate("backups")}
            onOpenGuardDetails={() => setGuardModal(true)}
          />
        )}
        {advancedOpen && (
          <AdvancedHomeCards
            projectDir={projectDir}
            apiKey={apiKey}
            providerKeys={providerKeys}
            hasAnyAiKey={hasAnyAiKey}
            aiKeyStatusLoaded={aiKeyStatusLoaded}
            cardOrder={cardOrder}
            onCardOrderChange={setCardOrder}
            onNavigate={onNavigate}
            onOpenSettings={onOpenSettings}
            watchOn={watchOn}
            onWatchChange={setWatchOn}
            mapMode={mapMode}
            onMapModeChange={setMapMode}
            onGuardResult={(result) => {
              setGuardResult(result);
              setGuardModal(true);
              void refreshScopeReport();
            }}
          />
        )}
      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
