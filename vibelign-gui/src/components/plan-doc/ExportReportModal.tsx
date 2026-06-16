import { useState, type CSSProperties } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  generatePlanningReport,
  type ReportResult,
  type ReportType,
} from "../../lib/vib/report";

const TYPES: { id: ReportType; label: string }[] = [
  { id: "work", label: "업무 보고" },
  { id: "proposal", label: "제안서" },
  { id: "result", label: "결과 보고" },
];

export interface ExportReportModalProps {
  open: boolean;
  planPath: string;
  cwd: string;
  onClose: () => void;
}

export function ExportReportModal({ open, planPath, cwd, onClose }: ExportReportModalProps) {
  const [reportType, setReportType] = useState<ReportType>("work");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ReportResult | null>(null);

  if (!open) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setResult(null);
    const r = await generatePlanningReport(cwd, planPath, reportType);
    setResult(r);
    setGenerating(false);
  };

  return (
    <div role="dialog" aria-label="보고서로 내보내기" style={overlay}>
      <div style={box}>
        <div style={header}>
          <span>📄 보고서로 내보내기</span>
          <button type="button" onClick={onClose} aria-label="닫기" style={iconBtn}>
            ✕
          </button>
        </div>

        <div style={contentArea}>
          <div style={{ marginBottom: 12 }}>
            {TYPES.map((t) => (
              <label key={t.id} style={{ marginRight: 16 }}>
                <input
                  type="radio"
                  name="report-type"
                  value={t.id}
                  checked={reportType === t.id}
                  onChange={() => setReportType(t.id)}
                />{" "}
                {t.label}
              </label>
            ))}
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            style={primaryBtn}
          >
            {generating ? "생성 중…" : "보고서 생성"}
          </button>

          {result && !result.ok && (
            <p role="alert" style={{ color: "#9B1B1B", marginTop: 12 }}>
              {result.error}
            </p>
          )}

          {result && result.ok && (
            <div style={{ marginTop: 12 }}>
              <iframe
                title="보고서 미리보기"
                srcDoc={result.html}
                sandbox=""
                style={{ width: "100%", height: 420, border: "1px solid #ddd" }}
              />
              <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>저장됨: {result.path}</p>
            </div>
          )}
        </div>

        <div style={footer}>
          {result && result.ok && (
            <button
              type="button"
              onClick={() => {
                if (result.ok) void openUrl("file://" + result.path).catch(() => {});
              }}
              style={primaryBtn}
            >
              파일 열기
            </button>
          )}
          <button type="button" onClick={onClose} style={secondaryBtn}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.45)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};
const box: CSSProperties = {
  background: "#FEFBF0",
  width: "min(680px, 92vw)",
  maxHeight: "88vh",
  display: "flex",
  flexDirection: "column",
  borderRadius: 8,
  overflow: "hidden",
};
const header: CSSProperties = {
  background: "#1A1A1A",
  color: "#FEFBF0",
  padding: "12px 16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontWeight: 700,
};
const contentArea: CSSProperties = { padding: 16, overflow: "auto" };
const footer: CSSProperties = {
  padding: 12,
  display: "flex",
  gap: 8,
  justifyContent: "flex-end",
  borderTop: "1px solid #e5e0d0",
};
const iconBtn: CSSProperties = {
  background: "transparent",
  color: "#FEFBF0",
  border: "none",
  cursor: "pointer",
  fontSize: 16,
};
const primaryBtn: CSSProperties = {
  background: "#9B1B1B",
  color: "#fff",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
};
const secondaryBtn: CSSProperties = {
  background: "#e5e0d0",
  color: "#1A1A1A",
  border: "none",
  padding: "8px 14px",
  borderRadius: 6,
  cursor: "pointer",
};
