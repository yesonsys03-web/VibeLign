// === ANCHOR: REPORTTHEMESELECT_START ===
import { REPORT_THEME_GROUPS, REPORT_THEME_OPTIONS } from "../../lib/vib/reportThemes";

interface ReportThemeSelectProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
}

export function ReportThemeSelect({ value, onChange }: ReportThemeSelectProps) {
  return (
    <div>
      {/* 종류·형식 사이드 버튼과 통일 — 그룹 라벨 헤더 + 브루탈리즘 input-field 스타일. */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "#1A1A1A", marginBottom: 6 }}>디자인 테마</div>
      <select
        className="input-field"
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
    </div>
  );
}
// === ANCHOR: REPORTTHEMESELECT_END ===
