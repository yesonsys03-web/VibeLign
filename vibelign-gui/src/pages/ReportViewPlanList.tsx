import type { CSSProperties, ReactNode } from "react";

import type { PlanningSessionSummary } from "../lib/vib/types";

type ReportViewPlanListProps = {
  readonly plans: readonly PlanningSessionSummary[] | null;
  readonly reviewBusy: boolean;
  readonly reviewErr: string | null;
  readonly exportErr: string | null;
  readonly exportedPath: string | null;
  readonly onStart?: () => void;
  readonly onSelectPlan: (path: string) => void;
};

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}

export function ReportViewPlanList({
  plans,
  reviewBusy,
  reviewErr,
  exportErr,
  exportedPath,
  onStart,
  onSelectPlan,
}: ReportViewPlanListProps): ReactNode {
  if (plans !== null && plans.length === 0 && !reviewBusy && !exportedPath) {
    return <ReportViewEmptyState onStart={onStart} />;
  }

  return (
    <div style={{ height: "100%", overflow: "auto", padding: "16px 20px" }}>
      <h2 style={title}>📄 보고서 작성</h2>
      <p style={description}>
        저장된 기획안을 업무 보고서(PDF·Word·PPT)로 내보내세요. 보고서 종류와 포맷을 골라 바로 생성합니다.
      </p>
      {reviewBusy && <p style={mutedText}>다듬기 모델 준비 중…</p>}
      {reviewErr && <p role="alert" style={errorText}>{reviewErr}</p>}
      {exportErr && <p role="alert" style={errorText}>{exportErr}</p>}
      {exportedPath && (
        <p style={successText}>📁 저장 위치: <b style={{ wordBreak: "break-all" }}>{exportedPath}</b></p>
      )}
      {plans === null && <div style={mutedText}>불러오는 중…</div>}
      <div style={planList}>
        {plans?.map((plan) => (
          <ReportViewPlanRow key={plan.sessionId} plan={plan} onSelectPlan={onSelectPlan} />
        ))}
      </div>
    </div>
  );
}

function ReportViewEmptyState({ onStart }: { readonly onStart?: () => void }): ReactNode {
  return (
    <div style={emptyState}>
      <div style={{ fontSize: 32 }}>📄</div>
      <div style={{ fontSize: 14 }}>보고서로 만들 기획안이 아직 없어요.</div>
      <div style={{ fontSize: 12, color: "#666" }}>
        기획방에서 기획안을 먼저 만들면 여기서 보고서로 내보낼 수 있어요.
      </div>
      {onStart && (
        <button className="nav-tab" style={{ marginTop: 4 }} onClick={onStart}>
          기획 시작하기 →
        </button>
      )}
    </div>
  );
}

function ReportViewPlanRow({
  plan,
  onSelectPlan,
}: {
  readonly plan: PlanningSessionSummary;
  readonly onSelectPlan: (path: string) => void;
}): ReactNode {
  return (
    <div style={planRow}>
      <div style={{ overflow: "hidden" }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>{plan.title || "(제목 없음)"}</div>
        <div style={planPathText}>{plan.outputPath ? fileName(plan.outputPath) : ""}</div>
      </div>
      <button
        type="button"
        onClick={() => {
          if (plan.outputPath) onSelectPlan(plan.outputPath);
        }}
        style={makeReportButton}
      >
        📄 보고서 만들기
      </button>
    </div>
  );
}

const title: CSSProperties = { fontSize: 18, fontWeight: 800, margin: "0 0 4px" };
const description: CSSProperties = { fontSize: 13, color: "#666", margin: "0 0 16px" };
const mutedText: CSSProperties = { fontSize: 13, color: "#888" };
const errorText: CSSProperties = { fontSize: 13, color: "#9B1B1B" };
const successText: CSSProperties = { fontSize: 13, color: "#2f6f46" };
const planList: CSSProperties = { display: "flex", flexDirection: "column", gap: 8 };
const emptyState: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "100%",
  gap: 12,
  color: "#888",
};
const planRow: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  border: "1px solid #e5e0d0",
  borderRadius: 8,
  padding: "12px 14px",
  gap: 12,
};
const planPathText: CSSProperties = {
  fontSize: 12,
  color: "#888",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};
const makeReportButton: CSSProperties = {
  flexShrink: 0,
  background: "#9B1B1B",
  color: "#fff",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
  fontWeight: 700,
};
