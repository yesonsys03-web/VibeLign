// === ANCHOR: PLANNINGACTIONBAR_START ===
interface PlanningActionBarProps {
  readonly canSave: boolean;
  readonly canView: boolean;
  readonly hasSavedPlan: boolean;
  readonly isSaving: boolean;
  /** 저장 후 백그라운드로 준비상태·계약을 분석 중 — "분석 중" 표시. */
  readonly isEnriching?: boolean;
  readonly onOpenSavedPlan: () => void;
  readonly onSave: () => void;
  readonly onStartWork: () => void;
  readonly onToggleMarkdown: () => void;
  /** 기획 확정 후 디자인 미리보기로 진입할 수 있을 때 제공. 없으면 버튼 미표시. */
  readonly onDesignPreview?: () => void;
}

// === ANCHOR: PLANNINGACTIONBAR_PLANNINGACTIONBAR_START ===
export function PlanningActionBar({
  canSave,
  canView,
  hasSavedPlan,
  isSaving,
  isEnriching = false,
  onOpenSavedPlan,
  onSave,
  onStartWork,
  onToggleMarkdown,
  onDesignPreview,
}: PlanningActionBarProps) {
  return (
    // 저장 버튼은 항상 눈에 띄어야 한다 — 긴 세션에서 스크롤로 사라지지 않게 하단 고정.
    <div
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        position: "sticky",
        bottom: 0,
        zIndex: 5,
        background: "var(--bg)",
        padding: "10px 0",
      }}
    >
      <button
        className="btn btn-black"
        type="button"
        onClick={onSave}
        disabled={!canSave}
        style={{ fontSize: 12, opacity: canSave ? 1 : 0.5 }}
      >
        {isSaving ? "저장중" : hasSavedPlan ? "기획안 다시 저장" : "기획안으로 저장"}
      </button>
      <button
        className="btn btn-black"
        type="button"
        onClick={onToggleMarkdown}
        disabled={!canView}
        style={{ fontSize: 12, opacity: canView ? 1 : 0.5 }}
      >
        기획안 보기
      </button>
      {hasSavedPlan && (
        <button className="btn btn-black" type="button" onClick={onOpenSavedPlan} style={{ fontSize: 12 }}>
          저장 파일 열기
        </button>
      )}
      {hasSavedPlan && (
        <button className="btn btn-black" type="button" onClick={onStartWork} style={{ fontSize: 12 }}>
          AI 작업 시작
        </button>
      )}
      {hasSavedPlan && onDesignPreview && (
        <button className="btn btn-ghost" type="button" onClick={onDesignPreview} style={{ fontSize: 12 }}>
          🎨 디자인 먼저 정하기
        </button>
      )}
      {isEnriching && (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "#92400E" }}>
          <span className="spinner" /> 준비 상태·작업 계약 분석 중… (잠시 뒤 문서에 반영돼요)
        </span>
      )}
    </div>
  );
}
// === ANCHOR: PLANNINGACTIONBAR_PLANNINGACTIONBAR_END ===
// === ANCHOR: PLANNINGACTIONBAR_END ===
