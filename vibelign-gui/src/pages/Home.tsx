// === ANCHOR: HOME_START ===
import { useState } from "react";
import { GuardResult, vibGuard } from "../lib/vib";
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
import pkg from "../../package.json";

type View = "home" | "manual_list" | "manual_detail";

interface HomeProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onNavigate: (page: "backups") => void;
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
}


// ── 컴포넌트 ──────────────────────────────────────────────────────────────────
export default function Home({ projectDir, apiKey, providerKeys, hasAnyAiKey = false, aiKeyStatusLoaded = false, onNavigate, onOpenDoctor, onOpenSettings, initialView = "home", watchOn: watchOnProp, setWatchOn: setWatchOnProp, watchError = null, onRetryWatch, hasCheckpoint = false, mapMode: mapModeProp, setMapMode: setMapModeProp, planningPrompt = "", planningOutputPath = null, planningPending = false, onOpenPlanning, onStartPlanning, onOpenPlanningHistory }: HomeProps) {
  const [view, setView]                   = useState<View>(initialView);
  const [selectedCmd, setSelectedCmd]     = useState<ManualCommand | null>(null);
  const [guardResult, setGuardResult]     = useState<GuardResult | null>(null);
  const [guardModal, setGuardModal] = useState(false);
  const [guardCheckPending, setGuardCheckPending] = useState(false);
  const [guardCheckError, setGuardCheckError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [watchOnLocal, setWatchOnLocal]   = useState(watchOnProp ?? false);
  const watchOn = watchOnProp ?? watchOnLocal;
  const setWatchOn = (v: boolean) => { setWatchOnLocal(v); setWatchOnProp?.(v); };
  const [mapModeLocal, setMapModeLocal]   = useState<"manual"|"auto">(mapModeProp ?? "manual");
  const mapMode = mapModeProp ?? mapModeLocal;
  const setMapMode = (v: "manual"|"auto") => { setMapModeLocal(v); setMapModeProp?.(v); };

  const { cardOrder, setCardOrder, resetOrder } = useCardOrder();

  async function handleRunGuard() {
    setGuardCheckPending(true);
    setGuardCheckError(null);
    try {
      const result = await vibGuard(projectDir);
      setGuardResult(result);
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
      <ManualCommandList
        onBack={() => setView("home")}
        onSelectCommand={(command) => {
          setSelectedCmd(command);
          setView("manual_detail");
        }}
      />
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
          <HomePlanningEntry
            prompt={planningPrompt}
            outputPath={planningOutputPath}
            isPending={planningPending}
            onOpen={onOpenPlanning}
          />
        ) : onStartPlanning ? (
          <HomePlanningStart onStart={onStartPlanning} />
        ) : null}
        {onOpenPlanningHistory && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPlanningHistory} style={{ fontSize: 11 }}>
            이전 기획 불러오기
          </button>
        )}
        {!advancedOpen && (
          <SimpleHome
            guardResult={guardResult}
            watchOn={watchOn}
            watchError={watchError}
            hasCheckpoint={hasCheckpoint}
            guardCheckPending={guardCheckPending}
            guardCheckError={guardCheckError}
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
            }}
          />
        )}
      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
