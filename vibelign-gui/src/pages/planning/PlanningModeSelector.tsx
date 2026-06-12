// === ANCHOR: PLANNINGMODESELECTOR_START ===
import { PLANNING_MODE_OPTIONS, resolvePlanningMode, type PlanningModeOption } from "./PlanningModes";

interface PlanningModeSelectorProps {
  readonly value: PlanningModeOption["id"];
  readonly onChange: (option: PlanningModeOption) => void;
}

// === ANCHOR: PLANNINGMODESELECTOR_PLANNINGMODESELECTOR_START ===
export function PlanningModeSelector({ value, onChange }: PlanningModeSelectorProps) {
  return (
    <div
      style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 900 }}
      title="AI 도우미가 어떻게 답할지 정해요 (한 명씩 바로 / 여럿이 함께 등)"
    >
      <label htmlFor="planning-response-mode">응답 모드</label>
      <select
        id="planning-response-mode"
        value={value}
        onChange={(event) => onChange(resolvePlanningMode(event.target.value))}
        style={{
          border: "2px solid #1A1A1A",
          background: "#FFFFFF",
          color: "#1A1A1A",
          padding: "6px 26px 6px 8px",
          fontSize: 12,
          fontWeight: 900,
        }}
      >
        {PLANNING_MODE_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label} · {option.targetLabel}
          </option>
        ))}
      </select>
    </div>
  );
}
// === ANCHOR: PLANNINGMODESELECTOR_PLANNINGMODESELECTOR_END ===
// === ANCHOR: PLANNINGMODESELECTOR_END ===
