// === ANCHOR: STAGE_HUB_CARDS_START ===
import { STAGE_DEFS, pagesForStage, type Stage, type Page } from "../../lib/nav/stages";
import { cardStepState, hubCardTarget, journeyStep, type ActiveGuideStep } from "../../lib/nav/guide";

interface StageHubCardsProps {
  onNavigate: (page: Page) => void;
  planningStatus: "none" | "active" | "done";
  backupCount: number;
  /** 가이드 현재 단계. null = 가이드 꺼짐/로딩 전(기존 표시 그대로). */
  currentStep?: ActiveGuideStep | null;
}

const CARD_DESC: Record<Stage, string> = {
  planning: "아이디어를 기획안으로",
  develop: "코드 보기·탐색",
  maintain: "안전 점검·복원",
};

function badgeText(stage: Stage, planningStatus: StageHubCardsProps["planningStatus"], backupCount: number): string {
  if (stage === "planning") {
    return planningStatus === "active" ? "● 진행 중" : planningStatus === "done" ? "완료" : "대기";
  }
  if (stage === "maintain") return `백업 ${backupCount}개`;
  return "열기"; // develop: 기존 신호 없음
}

export function StageHubCards({ onNavigate, planningStatus, backupCount, currentStep = null }: StageHubCardsProps) {
  return (
    <div style={{ display: "flex", gap: 12, padding: 16 }}>
      {STAGE_DEFS.map((def) => {
        const guideState = currentStep ? cardStepState(def.key, currentStep) : null;
        return (
          <button
            key={def.key}
            // "지금 할 차례" 카드는 현재 가이드 단계의 목적지로(예: 3️⃣ → 백업 탭), 평상시엔 첫 탭.
            onClick={() => onNavigate(hubCardTarget(def.key, currentStep, pagesForStage(def.key)[0]))}
            style={{
              flex: 1,
              textAlign: "left",
              padding: 16,
              background: guideState === "now" ? "#1a1813" : "#141414",
              border: guideState === "now" ? "2px solid #FBBF24" : "1px solid #2A2A2A",
              borderRadius: 8,
              color: "#ddd",
              cursor: "pointer",
            }}
          >
            <div style={{ fontSize: 20 }}>{def.icon}</div>
            <div style={{ fontWeight: 600, marginTop: 6 }}>
              {def.label}
              {guideState === "now" && (
                <span style={{ marginLeft: 8, fontSize: 11, background: "#FBBF24", color: "#000", padding: "1px 6px", borderRadius: 4, fontWeight: 700 }}>
                  지금 할 차례
                </span>
              )}
              {guideState === "done" && <span style={{ marginLeft: 8, fontSize: 11, color: "#4DFF91" }}>✓ 완료</span>}
              {guideState === "upcoming" && <span style={{ marginLeft: 8, fontSize: 11, color: "#666" }}>다음</span>}
            </div>
            <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>{CARD_DESC[def.key]}</div>
            {guideState === "now" && currentStep && (
              <div style={{ fontSize: 12, color: "#FBBF24", marginTop: 6 }}>
                → {journeyStep(currentStep).icon} {journeyStep(currentStep).shortAction}
              </div>
            )}
            <div style={{ fontSize: 12, color: def.key === "planning" && planningStatus === "active" ? "#FBBF24" : "#aaa", marginTop: 8 }}>
              {badgeText(def.key, planningStatus, backupCount)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
// === ANCHOR: STAGE_HUB_CARDS_END ===
