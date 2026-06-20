import type { CSSProperties, ReactNode } from "react";

import type { ReportType } from "../../lib/vib/report";
import type { ReportFontSizes } from "../../lib/vib/reportFontSizes";
import { ReportFontSizeControls } from "./ReportFontSizeControls";
import { ReportFontSelect } from "./ReportFontSelect";
import type { ReportFonts } from "../../lib/vib/reportFonts";
import { ReportThemeSelect } from "./ReportThemeSelect";
import type { ReportComposerFormat, ReportComposerResultState } from "./useReportComposerGeneration";

export const REPORT_TYPES: readonly { readonly id: ReportType; readonly label: string }[] = [
  { id: "work", label: "업무 보고" },
  { id: "proposal", label: "제안서" },
  { id: "result", label: "결과 보고" },
  { id: "doc", label: "문서 그대로" },
];

const REPORT_FORMATS: readonly { readonly id: ReportComposerFormat; readonly label: string }[] = [
  { id: "html", label: "HTML 미리보기" },
  { id: "pdf", label: "PDF 파일" },
  { id: "docx", label: "Word 파일" },
  { id: "pptx", label: "PPT 파일" },
];

type ReportComposerControlsProps = {
  readonly reportType: ReportType;
  readonly format: ReportComposerFormat;
  readonly theme: string;
  readonly author: string;
  readonly fontSizes: ReportFontSizes;
  readonly fonts: ReportFonts;
  readonly pageNumbers: boolean;
  readonly polish: boolean;
  readonly generating: boolean;
  readonly result: ReportComposerResultState | null;
  readonly onReportTypeChange: (reportType: ReportType) => void;
  readonly onFormatChange: (format: ReportComposerFormat) => void;
  readonly onThemeChange: (theme: string) => void;
  readonly onAuthorChange: (author: string) => void;
  readonly onFontSizesChange: (fontSizes: ReportFontSizes) => void;
  readonly onFontsChange: (fonts: ReportFonts) => void;
  readonly onPageNumbersChange: (pageNumbers: boolean) => void;
  readonly onPolishChange: (polish: boolean) => void;
  readonly onGenerate: () => void;
};

function storePreference(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    if (!(error instanceof Error)) throw error;
  }
}

export function ReportComposerControls({
  reportType,
  format,
  theme,
  author,
  fontSizes,
  fonts,
  pageNumbers,
  polish,
  generating,
  result,
  onReportTypeChange,
  onFormatChange,
  onThemeChange,
  onAuthorChange,
  onFontSizesChange,
  onFontsChange,
  onPageNumbersChange,
  onPolishChange,
  onGenerate,
}: ReportComposerControlsProps): ReactNode {
  return (
    <>
      <div role="radiogroup" aria-label="보고서 종류" style={{ marginBottom: 12 }}>
        <div style={groupLabel}>종류</div>
        {REPORT_TYPES.map((t) => (
          <label key={t.id} className="btn btn-ghost btn-sm" style={sideBtn(reportType === t.id)}>
            <input
              type="radio"
              name="report-type"
              value={t.id}
              checked={reportType === t.id}
              onChange={() => onReportTypeChange(t.id)}
              style={srOnly}
            />
            {t.label}
          </label>
        ))}
      </div>

      <div role="radiogroup" aria-label="내보내기 형식" style={{ marginBottom: 12 }}>
        <div style={groupLabel}>형식</div>
        {REPORT_FORMATS.map((f) => (
          <label key={f.id} className="btn btn-ghost btn-sm" style={sideBtn(format === f.id)}>
            <input
              type="radio"
              name="export-format"
              value={f.id}
              checked={format === f.id}
              onChange={() => onFormatChange(f.id)}
              style={srOnly}
            />
            {f.label}
          </label>
        ))}
      </div>

      <div style={{ marginBottom: 12 }}>
        <ReportThemeSelect
          value={theme}
          onChange={(nextTheme) => {
            onThemeChange(nextTheme);
            storePreference("vibelign_report_theme", nextTheme);
          }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <ReportFontSizeControls value={fontSizes} onChange={onFontSizesChange} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <ReportFontSelect value={fonts} onChange={onFontsChange} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={groupLabel}>작성자</div>
        <input
          type="text"
          className="input-field"
          aria-label="작성자"
          value={author}
          placeholder="(선택) 이름"
          onChange={(e) => {
            onAuthorChange(e.target.value);
            storePreference("vibelign_report_author", e.target.value);
          }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={groupLabel}>옵션</div>
        <label className="btn btn-ghost btn-sm" style={sideBtn(pageNumbers)}>
          <input
            type="checkbox"
            checked={pageNumbers}
            onChange={(e) => onPageNumbersChange(e.target.checked)}
            style={srOnly}
          />
          <span aria-hidden="true" style={{ width: 16, display: "inline-block" }}>{pageNumbers ? "✓" : ""}</span>
          페이지 번호 (Word·PDF)
        </label>
        <label className="btn btn-ghost btn-sm" style={sideBtn(polish)}>
          <input
            type="checkbox"
            checked={polish}
            onChange={(e) => onPolishChange(e.target.checked)}
            style={srOnly}
          />
          <span aria-hidden="true" style={{ width: 16, display: "inline-block" }}>{polish ? "✓" : ""}</span>
          AI 어조 다듬기 (무료)
        </label>
      </div>

      <button type="button" onClick={onGenerate} disabled={generating} style={primaryBtn}>
        {generating ? "생성 중…" : "보고서 생성"}
      </button>

      {result && !result.ok && (
        <p role="alert" style={{ color: "#9B1B1B", marginTop: 12 }}>
          {result.error}
        </p>
      )}
    </>
  );
}

const groupLabel: CSSProperties = { fontSize: 12, fontWeight: 700, color: "#1A1A1A", marginBottom: 6 };
const srOnly: CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap",
  border: 0,
};
const primaryBtn: CSSProperties = {
  background: "#9B1B1B",
  color: "#fff",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
};

function sideBtn(active: boolean): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    width: "100%",
    justifyContent: "flex-start",
    textAlign: "left",
    marginBottom: 3,
    textTransform: "none",
    letterSpacing: 0,
    cursor: "pointer",
    background: active ? "#1A1A1A" : undefined,
    color: active ? "#fff" : undefined,
    boxShadow: "inset 4px 0 0 #9B1B1B, var(--shadow-sm)",
  };
}
