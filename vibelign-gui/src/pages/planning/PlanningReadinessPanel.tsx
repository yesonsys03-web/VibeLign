import type { CSSProperties } from "react";
import type { ReadinessReport, ReadinessVerdict } from "../../lib/vib/types";
import { readinessSummary } from "./PlanningReadiness";

const ICON: Record<ReadinessVerdict, string> = { green: "🟢", red: "🔴", na: "⚪" };
const CHECK_LABELS: ReadonlyArray<readonly [string, keyof ReadinessReport["requirements"][number]["checks"]]> = [
  ["발동", "trigger"],
  ["데이터", "data"],
  ["판정", "logic"],
  ["수용", "acceptance"],
  ["엣지", "edge"],
  ["플랫폼", "platform"],
];

interface PlanningReadinessPanelProps {
  readonly report: ReadinessReport | null | undefined;
}

export function PlanningReadinessPanel({ report }: PlanningReadinessPanelProps) {
  if (!report) {
    return null;
  }
  if (report.status === "unavailable") {
    return (
      <div style={panelStyle}>
        <strong style={{ fontSize: 12 }}>구현 준비 상태: 확인 못 함</strong>
        <p style={{ fontSize: 11, margin: "6px 0 0", opacity: 0.8 }}>
          활성 AI(claude/codex/agy)를 찾지 못해 판정하지 못했어요. 저장은 정상 완료됐어요.
        </p>
      </div>
    );
  }
  const summary = readinessSummary(report);
  return (
    <div style={panelStyle}>
      <strong style={{ fontSize: 12 }}>
        구현 준비 상태: 🟢 {summary.green} / 🔴 {summary.red}
        {summary.coreRedCount > 0 ? `  (핵심 구멍 ${summary.coreRedCount})` : ""}
      </strong>
      <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
        {report.requirements.map((requirement, index) => (
          <div key={`${requirement.title}-${index}`} style={{ fontSize: 11, borderTop: "1px solid #1A1A1A22", paddingTop: 6 }}>
            <div style={{ fontWeight: 700 }}>
              {requirement.core ? "★ " : ""}
              {requirement.title || "(제목 없음)"}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 2 }}>
              {CHECK_LABELS.map(([label, key]) => (
                <span key={key} title={requirement.checks[key].note}>
                  {label}
                  {ICON[requirement.checks[key].verdict]}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const panelStyle: CSSProperties = {
  border: "2px solid #1A1A1A",
  background: "#FEFBF0",
  padding: "12px 14px",
};
