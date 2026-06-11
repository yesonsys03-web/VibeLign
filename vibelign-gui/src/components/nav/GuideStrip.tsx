// === ANCHOR: GUIDE_STRIP_START ===
import { journeyStep, type ActiveGuideStep } from "../../lib/nav/guide";
import { PAGE_LABELS, type Page } from "../../lib/nav/stages";

interface GuideStripProps {
  enabled: boolean;
  /** null = 신호 로딩 전 — 가이드 부분 미렌더(spec §4-4) */
  step: ActiveGuideStep | null;
  /** 현재 탭 — 이미 단계 목적지에 있으면 "~으로 이동 →" 버튼을 숨긴다. */
  currentPage?: Page | null;
  hasCheckpoint: boolean;
  planningPending: boolean;
  /** AI 도구 0개 "확정 탐지" 시에만 true — 탐지 실패·미완은 false(분기 미노출, spec §3.2) */
  aiToolMissing?: boolean;
  /** 첫 사이클 완주 축하 표시 중 — App이 6️⃣→4️⃣ 전환에서 1회 켠다(spec §3.2) */
  celebrating?: boolean;
  onNavigate: (page: Page) => void;
  onStepChange: (next: ActiveGuideStep) => void;
  onDisable: () => void;
  /** 도구 미보유 분기의 "설치 도움받기" 목적지 — 설정('AI 도구 설정') */
  onOpenSettings?: () => void;
  onCelebrateDismiss?: () => void;
}

/**
 * 탭바 아래 안내 줄 — 좌측 가이드(지금 할 일) + 우측 기존 상태 신호. A안 상태 스트립을 대체·통합.
 * 시인성(spec §3.2): 가이드 활성 시 13px + #FBBF24 강조·세로 패딩 6px, off 시 기존 얇은 줄(3px·11px).
 * 작업 탭 안에서 초보자에게 보이는 유일한 안내 표면이라 두 탭바 아래에서 묻히면 안 된다.
 */
export function GuideStrip({
  enabled,
  step,
  currentPage = null,
  hasCheckpoint,
  planningPending,
  aiToolMissing = false,
  celebrating = false,
  onNavigate,
  onStepChange,
  onDisable,
  onOpenSettings,
  onCelebrateDismiss,
}: GuideStripProps) {
  const def = enabled && step ? journeyStep(step) : null;
  if (celebrating) {
    // 첫 사이클 완주 축하(spec §3.2) — 이 순간만큼은 가이드 줄 대신 완료 마디를 보여준다.
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "6px 12px",
          fontSize: 13,
          color: "#4DFF91",
          background: "#0E0E0E",
          borderBottom: "1px solid #1A1A1A",
        }}
      >
        <span>
          🎉 <b>첫 사이클 완주!</b> 기획부터 저장까지 해냈어요 — 이 흐름 그대로 반복하면 돼요
        </span>
        <button
          className="nav-tab"
          style={{ fontSize: 12, padding: "0 6px", color: "#888" }}
          onClick={() => onCelebrateDismiss?.()}
        >
          ×
        </button>
      </div>
    );
  }
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: def ? "6px 12px" : "3px 12px",
        fontSize: 11,
        color: "#888",
        background: "#0E0E0E",
        borderBottom: "1px solid #1A1A1A",
      }}
    >
      {def && step && (
        <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <span style={{ color: "#ccc" }}>
            🧭 지금:{" "}
            <span style={{ color: "#FBBF24", fontWeight: 700 }}>
              {def.icon} {def.label}
            </span>{" "}
            — {def.shortAction}
          </span>
          {def.targetPage && def.targetPage !== currentPage && (
            <button
              // 가이드의 주행동 버튼 — 강조색은 guide-accent(hover 포함), 테두리로 버튼임을 드러낸다.
              className="nav-tab guide-accent"
              style={{ fontSize: 12, padding: "1px 8px", border: "1px solid #FBBF24", borderRadius: 4 }}
              onClick={() => onNavigate(def.targetPage as Page)}
            >
              {PAGE_LABELS[def.targetPage]}으로 이동 →
            </button>
          )}
          {step === 4 && (
            <button
              className="nav-tab guide-accent"
              style={{ fontSize: 12, padding: "0 8px" }}
              title="외부 AI 작업이 끝났거나 멈췄으면 확인 단계로"
              onClick={() => {
                // 외부 AI 작업 종료는 신호로 100% 감지 불가, 비-git 프로젝트는 변경이 항상
                // 0으로 읽혀 자동 전환이 아예 없음 → 수동 출구(spec §3.2 affordance).
                // "끝났거나 멈췄거나" — 중도 중단자도 자기 안내로 느끼게(완주 전제 금지).
                // override 후 5️⃣ 목적지로 이동.
                onStepChange(5);
                const verify = journeyStep(5);
                if (verify.targetPage) onNavigate(verify.targetPage as Page);
              }}
            >
              AI 작업이 끝났거나 멈췄나요? 확인하러 가기 →
            </button>
          )}
          {step === 4 && aiToolMissing && onOpenSettings && (
            <button
              className="nav-tab guide-accent"
              style={{ fontSize: 12, padding: "0 8px" }}
              title="설정의 'AI 도구 설정'에서 설치를 도와드려요"
              onClick={onOpenSettings}
            >
              {/* 도구 미보유 입문자 분기(spec §3.2) — 4️⃣는 앱 밖으로 나가는 유일한 지점이라 최대 이탈 절벽 */}
              AI 도구가 아직 없나요? 설치 도움받기 →
            </button>
          )}
          {(step === 4 || step === 5) && (
            <button
              className="nav-tab"
              style={{ fontSize: 12, padding: "0 8px", color: "#888" }}
              title="마지막으로 저장한 시점으로 코드를 되돌릴 수 있어요"
              onClick={() => onNavigate("backups")}
            >
              {/* 포기 비상구(spec §3.2) — undo 발견이 6️⃣ 뒤에 숨지 않게. 회색톤 = 주행동 방해 금지. */}
              잘 안 됐나요? 되돌리기 →
            </button>
          )}
          <button
            className="nav-tab"
            style={{ fontSize: 12, padding: "0 6px", color: "#888" }}
            title="이전 단계"
            disabled={step === 2}
            onClick={() => step > 2 && onStepChange((step - 1) as ActiveGuideStep)}
          >
            ‹
          </button>
          <button
            className="nav-tab"
            style={{ fontSize: 12, padding: "0 6px", color: "#888" }}
            title="다음 단계"
            disabled={step === 6}
            onClick={() => step < 6 && onStepChange((step + 1) as ActiveGuideStep)}
          >
            ›
          </button>
          <button
            className="nav-tab"
            style={{ fontSize: 12, padding: "0 6px", color: "#888" }}
            title="가이드 끄기 (설정에서 다시 켤 수 있어요)"
            onClick={onDisable}
          >
            ×
          </button>
        </span>
      )}
      <div style={{ flex: 1 }} />
      <span style={{ color: hasCheckpoint ? "#aaa" : "#666" }}>
        {hasCheckpoint ? "✓ 백업 데이터 있음" : "백업 데이터 없음"}
      </span>
      {planningPending && <span style={{ color: "#FBBF24" }}>● 기획 진행 중</span>}
    </div>
  );
}
// === ANCHOR: GUIDE_STRIP_END ===
