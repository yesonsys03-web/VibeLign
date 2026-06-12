// === ANCHOR: STAGE_HUB_CARDS_START ===
import { STAGE_DEFS, pagesForStage, type Stage, type Page } from "../../lib/nav/stages";
import { cardStepState, hubCardTarget, journeyStep, type ActiveGuideStep } from "../../lib/nav/guide";

export interface PlanningSummary {
  total: number;
  /** 저장된 기획안(완료/확정) 수. */
  saved: number;
  /** 미저장(진행중) 수. */
  draft: number;
  /** 저장됐지만 대화가 더 진행돼 갱신 필요한 수(saved 부분집합). */
  stale: number;
}

interface StageHubCardsProps {
  onNavigate: (page: Page) => void;
  planningStatus: "none" | "active" | "done";
  /** 다중 기획안 현황 — total>0 이면 단일 상태 대신 집계 배지를 보인다. */
  planningSummary?: PlanningSummary;
  backupCount: number;
  /** 가이드 현재 단계. null = 가이드 꺼짐/로딩 전(기존 표시 그대로). */
  currentStep?: ActiveGuideStep | null;
}

const CARD_DESC: Record<Stage, string> = {
  planning: "아이디어를 기획안으로",
  develop: "코드 보기·탐색",
  maintain: "안전 점검·복원",
};

export function badgeText(
  stage: Stage,
  planningStatus: StageHubCardsProps["planningStatus"],
  backupCount: number,
  planningSummary?: PlanningSummary,
): string {
  if (stage === "planning" && planningSummary) {
    const { saved, draft, stale } = planningSummary;
    // "기획안" = 저장된 plan doc(기획안 탭과 동일 정의). 저장본이 있을 때만 "기획안 N개".
    if (saved > 0) {
      let text = `기획안 ${saved}개`;
      if (stale > 0) text += ` · ${stale} 갱신필요`;
      if (draft > 0) text += ` · 초안 ${draft}개`;
      return text;
    }
    // 저장본 없음 — 미저장 초안만 있으면 "기획안"이라 부르지 않는다(탭이 비어 있으므로).
    if (draft > 0) return `기획 초안 ${draft}개`;
  }
  if (stage === "planning") {
    return planningStatus === "active" ? "● 진행 중" : planningStatus === "done" ? "완료" : "대기";
  }
  if (stage === "maintain") return `백업 ${backupCount}개`;
  return "열기"; // develop: 기존 신호 없음
}

export function StageHubCards({ onNavigate, planningStatus, planningSummary, backupCount, currentStep = null }: StageHubCardsProps) {
  return (
    <div style={{ display: "flex", gap: 12, padding: 16 }}>
      {STAGE_DEFS.map((def) => {
        const guideState = currentStep ? cardStepState(def.key, currentStep) : null;
        return (
          <button
            key={def.key}
            // "지금 할 차례" 카드는 현재 가이드 단계의 목적지로(예: 3️⃣ → 백업 탭), 평상시엔 첫 탭.
            // 단 기획안이 1개 이상이면 기획 카드는 기획안 목록(plan-doc)으로 — 다중 기획안 관리 진입.
            onClick={() => {
              const fallback =
                def.key === "planning" && (planningSummary?.saved ?? 0) > 0 ? "plan-doc" : pagesForStage(def.key)[0];
              onNavigate(hubCardTarget(def.key, currentStep, fallback));
            }}
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
                <span style={{ marginLeft: 8, fontSize: 13, background: "#FBBF24", color: "#000", padding: "1px 6px", borderRadius: 4, fontWeight: 700 }}>
                  지금 할 차례
                </span>
              )}
              {guideState === "done" && <span style={{ marginLeft: 8, fontSize: 13, color: "#4DFF91" }}>✓ 완료</span>}
              {guideState === "upcoming" && <span style={{ marginLeft: 8, fontSize: 13, color: "#666" }}>다음</span>}
            </div>
            <div style={{ fontSize: 14, color: "#888", marginTop: 4 }}>{CARD_DESC[def.key]}</div>
            {guideState === "now" && currentStep && (
              <div style={{ fontSize: 14, color: "#FBBF24", marginTop: 6 }}>
                → {journeyStep(currentStep).icon} {journeyStep(currentStep).shortAction}
              </div>
            )}
            <div
              style={{
                fontSize: 14,
                color:
                  def.key === "planning" &&
                  (planningStatus === "active" || (planningSummary?.draft ?? 0) > 0 || (planningSummary?.stale ?? 0) > 0)
                    ? "#FBBF24"
                    : "#aaa",
                marginTop: 8,
              }}
            >
              {badgeText(def.key, planningStatus, backupCount, planningSummary)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
// === ANCHOR: STAGE_HUB_CARDS_END ===
