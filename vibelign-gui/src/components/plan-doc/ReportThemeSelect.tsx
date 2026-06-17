// === ANCHOR: REPORTTHEMESELECT_START ===
import { REPORT_THEME_GROUPS, REPORT_THEME_OPTIONS } from "../../lib/vib/reportThemes";

interface ReportThemeSelectProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
}

export function ReportThemeSelect({ value, onChange }: ReportThemeSelectProps) {
  return (
    <label>
      디자인 테마{" "}
      <select
        aria-label="디자인 테마"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {REPORT_THEME_GROUPS.map((group) => (
          <optgroup key={group} label={group}>
            {REPORT_THEME_OPTIONS.filter((theme) => theme.group === group).map((theme) => (
              <option key={theme.id} value={theme.id}>
                {theme.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  );
}
// === ANCHOR: REPORTTHEMESELECT_END ===
