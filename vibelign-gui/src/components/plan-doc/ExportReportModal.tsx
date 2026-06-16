import { useState, type CSSProperties } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  generatePlanningReport,
  generateReportOffice,
  generateReportPdf,
  type ReportType,
} from "../../lib/vib/report";

type Format = "html" | "pdf" | "docx" | "pptx";
type ResultState =
  | { kind: "html"; ok: true; path: string; reportType: string; html: string }
  | { kind: "file"; ok: true; path: string }
  | { ok: false; error: string };

const TYPES: { id: ReportType; label: string }[] = [
  { id: "work", label: "업무 보고" },
  { id: "proposal", label: "제안서" },
  { id: "result", label: "결과 보고" },
];

const FORMATS: { id: Format; label: string }[] = [
  { id: "html", label: "HTML 미리보기" },
  { id: "pdf", label: "PDF 파일" },
  { id: "docx", label: "Word 파일" },
  { id: "pptx", label: "PPT 파일" },
];

export interface ExportReportModalProps {
  open: boolean;
  planPath: string;
  cwd: string;
  onClose: () => void;
}

export function ExportReportModal({ open, planPath, cwd, onClose }: ExportReportModalProps) {
  const [reportType, setReportType] = useState<ReportType>("work");
  const [format, setFormat] = useState<Format>("html");
  const [polish, setPolish] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ResultState | null>(null);

  if (!open) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setResult(null);
    if (format === "html") {
      const r = await generatePlanningReport(cwd, planPath, reportType, polish);
      setResult(
        r.ok ? { kind: "html", ok: true, path: r.path, reportType: r.reportType, html: r.html } : r,
      );
    } else if (format === "pdf") {
      const r = await generateReportPdf(cwd, planPath, reportType, polish);
      setResult(r.ok ? { kind: "file", ok: true, path: r.path } : r);
    } else {
      const r = await generateReportOffice(cwd, planPath, reportType, format, polish);
      setResult(r.ok ? { kind: "file", ok: true, path: r.path } : r);
    }
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

          <div style={{ marginBottom: 12 }}>
            {FORMATS.map((f) => (
              <label key={f.id} style={{ marginRight: 16 }}>
                <input
                  type="radio"
                  name="export-format"
                  value={f.id}
                  checked={format === f.id}
                  onChange={() => setFormat(f.id)}
                />{" "}
                {f.label}
              </label>
            ))}
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>
              <input
                type="checkbox"
                checked={polish}
                onChange={(e) => setPolish(e.target.checked)}
              />{" "}
              AI 어조 다듬기 (무료)
            </label>
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

          {result && result.ok && result.kind === "html" && (
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

          {result && result.ok && result.kind === "file" && (
            <p style={{ fontSize: 12, color: "#666", marginTop: 12 }}>저장됨: {result.path}</p>
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
