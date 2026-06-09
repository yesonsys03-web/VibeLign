// === ANCHOR: PLANNINGACTIONBAR_START ===
interface PlanningActionBarProps {
  readonly canSave: boolean;
  readonly canView: boolean;
  readonly hasSavedPlan: boolean;
  readonly isSaving: boolean;
  readonly onOpenSavedPlan: () => void;
  readonly onSave: () => void;
  readonly onStartWork: () => void;
  readonly onToggleMarkdown: () => void;
}

// === ANCHOR: PLANNINGACTIONBAR_PLANNINGACTIONBAR_START ===
export function PlanningActionBar({
  canSave,
  canView,
  hasSavedPlan,
  isSaving,
  onOpenSavedPlan,
  onSave,
  onStartWork,
  onToggleMarkdown,
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
    </div>
  );
}
// === ANCHOR: PLANNINGACTIONBAR_PLANNINGACTIONBAR_END ===
// === ANCHOR: PLANNINGACTIONBAR_END ===
