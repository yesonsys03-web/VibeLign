// === ANCHOR: REPORT_FONT_SIZE_CONTROLS_START ===
import type { CSSProperties } from "react";
import {
  REPORT_FONT_SIZE_FIELDS,
  REPORT_FONT_SIZE_MAX,
  REPORT_FONT_SIZE_MIN,
  parseReportFontSizeInput,
  type ReportFontSizes,
} from "../../lib/vib/reportFontSizes";

export interface ReportFontSizeControlsProps {
  readonly value: ReportFontSizes;
  readonly onChange: (value: ReportFontSizes) => void;
}

export function ReportFontSizeControls({ value, onChange }: ReportFontSizeControlsProps) {
  return (
    <fieldset style={fieldset}>
      <legend style={legend}>폰트 크기</legend>
      <div style={grid}>
        {REPORT_FONT_SIZE_FIELDS.map((field) => (
          <label key={field.key} style={label}>
            <span>{field.label}</span>
            <input
              aria-label={`${field.label} 폰트 크기`}
              type="number"
              min={REPORT_FONT_SIZE_MIN}
              max={REPORT_FONT_SIZE_MAX}
              step={1}
              placeholder={field.placeholder}
              value={value[field.key] ?? ""}
              onChange={(event) => {
                onChange({ ...value, [field.key]: parseReportFontSizeInput(event.target.value) });
              }}
              style={input}
            />
          </label>
        ))}
      </div>
      <button type="button" onClick={() => onChange({})} style={resetButton}>
        테마 기본값
      </button>
    </fieldset>
  );
}

const fieldset: CSSProperties = {
  border: "2px solid #1A1A1A",
  padding: 10,
  margin: 0,
  background: "#FFFFFF",
  boxSizing: "border-box",
  minInlineSize: 0,
  width: "100%",
};

const legend: CSSProperties = {
  padding: "0 6px",
  fontSize: 12,
  fontWeight: 800,
};

const grid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(76px, 1fr))",
  gap: 8,
};

const label: CSSProperties = {
  display: "grid",
  gap: 4,
  fontSize: 12,
  fontWeight: 700,
};

const input: CSSProperties = {
  width: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  border: "2px solid #1A1A1A",
  padding: "6px 8px",
  fontSize: 13,
  fontWeight: 700,
};

const resetButton: CSSProperties = {
  marginTop: 8,
  border: "1px solid #1A1A1A",
  background: "#FEFBF0",
  padding: "5px 10px",
  fontSize: 11,
  fontWeight: 800,
  cursor: "pointer",
};
// === ANCHOR: REPORT_FONT_SIZE_CONTROLS_END ===
