// === ANCHOR: STAGE_HUB_CARDS_START ===
import { STAGE_DEFS, pagesForStage, type Stage, type Page } from "../../lib/nav/stages";

interface StageHubCardsProps {
  onNavigate: (page: Page) => void;
  planningStatus: "none" | "active" | "done";
  backupCount: number;
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

export function StageHubCards({ onNavigate, planningStatus, backupCount }: StageHubCardsProps) {
  return (
    <div style={{ display: "flex", gap: 12, padding: 16 }}>
      {STAGE_DEFS.map((def) => (
        <button
          key={def.key}
          onClick={() => onNavigate(pagesForStage(def.key)[0])}
          style={{
            flex: 1,
            textAlign: "left",
            padding: 16,
            background: "#141414",
            border: "1px solid #2A2A2A",
            borderRadius: 8,
            color: "#ddd",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 20 }}>{def.icon}</div>
          <div style={{ fontWeight: 600, marginTop: 6 }}>{def.label}</div>
          <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>{CARD_DESC[def.key]}</div>
          <div style={{ fontSize: 12, color: def.key === "planning" && planningStatus === "active" ? "#FBBF24" : "#aaa", marginTop: 8 }}>
            {badgeText(def.key, planningStatus, backupCount)}
          </div>
        </button>
      ))}
    </div>
  );
}
// === ANCHOR: STAGE_HUB_CARDS_END ===
