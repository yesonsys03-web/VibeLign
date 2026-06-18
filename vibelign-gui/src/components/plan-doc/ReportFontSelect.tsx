// === ANCHOR: REPORT_FONT_SELECT_START ===
import type { CSSProperties } from "react";
import { REPORT_FONT_OPTIONS, type ReportFonts } from "../../lib/vib/reportFonts";

export interface ReportFontSelectProps {
  readonly value: ReportFonts;
  readonly onChange: (value: ReportFonts) => void;
}

const SLOTS = [
  { slot: "heading" as const, label: "제목 폰트" },
  { slot: "body" as const, label: "본문 폰트" },
];

export function ReportFontSelect({ value, onChange }: ReportFontSelectProps) {
  return (
    <fieldset style={fieldset}>
      <legend style={legend}>폰트 종류</legend>
      <div style={grid}>
        {SLOTS.map(({ slot, label }) => (
          <label key={slot} style={labelStyle}>
            <span>{label}</span>
            <select
              aria-label={label}
              value={value[slot] ?? ""}
              onChange={(e) => onChange({ ...value, [slot]: e.target.value || undefined })}
              style={select}
            >
              <option value="">테마 기본값</option>
              {REPORT_FONT_OPTIONS.map((f) => (
                <option key={f.id} value={f.id}>{f.label}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

const fieldset: CSSProperties = {
  border: "2px solid #1A1A1A", padding: 10, margin: 0, background: "#FFFFFF",
  boxSizing: "border-box", minInlineSize: 0, width: "100%",
};
const legend: CSSProperties = { padding: "0 6px", fontSize: 12, fontWeight: 800 };
const grid: CSSProperties = {
  display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8,
};
const labelStyle: CSSProperties = { display: "grid", gap: 4, fontSize: 12, fontWeight: 700 };
const select: CSSProperties = {
  width: "100%", minWidth: 0, boxSizing: "border-box",
  border: "2px solid #1A1A1A", padding: "6px 8px", fontSize: 13, fontWeight: 700,
};
// === ANCHOR: REPORT_FONT_SELECT_END ===
