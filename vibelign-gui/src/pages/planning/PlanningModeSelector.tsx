import { PLANNING_MODE_OPTIONS, resolvePlanningMode, type PlanningModeOption } from "./PlanningModes";

interface PlanningModeSelectorProps {
  readonly value: PlanningModeOption["id"];
  readonly onChange: (option: PlanningModeOption) => void;
}

export function PlanningModeSelector({ value, onChange }: PlanningModeSelectorProps) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 900 }}>
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
          fontSize: 11,
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
