import type { CreatePlanningTemplateResponse } from "../../lib/vib";

interface PlanningPersonaStatusProps {
  readonly result: CreatePlanningTemplateResponse;
}

export function PlanningPersonaStatus({ result }: PlanningPersonaStatusProps) {
  if (!result.adapter && !result.llmStatus) {
    return null;
  }
  const isOk = result.llmStatus === "ok";
  const message = isOk
    ? "지오가 기획안을 한 번 검토했어요."
    : "AI 연결은 아직 준비되지 않았지만, 기본 기획안은 저장했어요.";

  return (
    <div
      role="status"
      style={{
        border: "2px solid #1A1A1A",
        background: isOk ? "#EAF8EF" : "#FFF5D6",
        padding: "10px 12px",
        fontSize: 12,
        fontWeight: 800,
      }}
    >
      {message}
    </div>
  );
}
