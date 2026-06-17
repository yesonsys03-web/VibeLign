import { useState, type CSSProperties } from "react";
import { openPath } from "@tauri-apps/plugin-opener";
import { pickFolder } from "../../lib/vib/system";
import {
  copyReportTo,
  generatePlanningReport,
  generateReportOffice,
  generateReportPdf,
  getReportExportDir,
  setReportExportDir,
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
  /** 제공되고 'AI 다듬기'가 켜져 있으면, 인라인 생성 대신 블록 diff 검토 화면으로 보낸다. */
  onReviewRequest?: (reportType: ReportType, format: Format) => void;
}

export function ExportReportModal({ open, planPath, cwd, onClose, onReviewRequest }: ExportReportModalProps) {
  const [reportType, setReportType] = useState<ReportType>("work");
  const [format, setFormat] = useState<Format>("html");
  const [polish, setPolish] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ResultState | null>(null);
  const [openErr, setOpenErr] = useState<string | null>(null);
  // 사용자에게 전달된 최종 저장 위치(.vibelign/reports 내부 사본과 별개로 복사한 곳).
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);

  if (!open) return null;

  // 생성된 보고서를 지정 폴더로 복사한다. dir 가 없으면 기본 폴더(설정값→OS 문서 폴더)를 쓴다.
  const exportTo = async (src: string, dir?: string) => {
    setExporting(true);
    setExportErr(null);
    try {
      const target = dir ?? (await getReportExportDir());
      const dest = await copyReportTo(src, target);
      setExportedPath(dest);
    } catch (e) {
      setExportErr(`저장 위치로 복사하지 못했어요: ${String(e)}`);
    } finally {
      setExporting(false);
    }
  };

  // "다른 위치에 저장": 폴더 선택 → 복사 → 그 폴더를 다음 기본값으로 기억.
  const handleChooseLocation = async () => {
    if (!result || !result.ok) return;
    const dir = await pickFolder().catch(() => null);
    if (!dir) return;
    await exportTo(result.path, dir);
    void setReportExportDir(dir).catch(() => {});
  };

  const handleGenerate = async () => {
    // 다듬기 ON + 리뷰 핸들러 제공 시: 인라인 생성 대신 검토 화면으로 위임한다.
    if (polish && onReviewRequest) {
      onReviewRequest(reportType, format);
      onClose();
      return;
    }
    setGenerating(true);
    setResult(null);
    setOpenErr(null);
    setExportedPath(null);
    setExportErr(null);
    let next: ResultState;
    if (format === "html") {
      const r = await generatePlanningReport(cwd, planPath, reportType, polish);
      next = r.ok
        ? { kind: "html", ok: true, path: r.path, reportType: r.reportType, html: r.html }
        : r;
    } else if (format === "pdf") {
      const r = await generateReportPdf(cwd, planPath, reportType, polish);
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    } else {
      const r = await generateReportOffice(cwd, planPath, reportType, format, polish);
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    }
    setResult(next);
    setGenerating(false);
    // 생성 성공 시 기본 폴더로 자동 복사(내부 .vibelign/reports 사본은 그대로 유지).
    if (next.ok) void exportTo(next.path);
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
              <p style={{ fontSize: 11, color: "#999", marginTop: 8 }}>내부 사본: {result.path}</p>
            </div>
          )}

          {result && result.ok && result.kind === "file" && (
            <p style={{ fontSize: 11, color: "#999", marginTop: 12 }}>내부 사본: {result.path}</p>
          )}

          {result && result.ok && (
            <div style={exportBox}>
              <div style={{ fontSize: 13, color: "#1A1A1A" }}>
                {exporting ? (
                  "저장 위치로 복사 중…"
                ) : exportedPath ? (
                  <>
                    📁 저장 위치: <b style={{ wordBreak: "break-all" }}>{exportedPath}</b>
                  </>
                ) : (
                  "저장 위치를 준비 중…"
                )}
              </div>
              {exportErr && (
                <p role="alert" style={{ color: "#9B1B1B", fontSize: 12, margin: "6px 0 0" }}>
                  {exportErr}
                </p>
              )}
              <button
                type="button"
                onClick={() => void handleChooseLocation()}
                disabled={exporting}
                style={{ ...secondaryBtn, marginTop: 8 }}
              >
                다른 위치에 저장…
              </button>
            </div>
          )}
        </div>

        <div style={footer}>
          {openErr && (
            <span role="alert" style={{ color: "#9B1B1B", fontSize: 12, marginRight: "auto" }}>
              {openErr}
            </span>
          )}
          {result && result.ok && (
            <button
              type="button"
              onClick={() => {
                if (!result.ok) return;
                setOpenErr(null);
                void openPath(exportedPath ?? result.path).catch((e) =>
                  setOpenErr(`파일을 열지 못했어요: ${String(e)}`),
                );
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
const exportBox: CSSProperties = {
  marginTop: 12,
  padding: 12,
  background: "#f6f1e0",
  border: "1px solid #e5e0d0",
  borderRadius: 6,
};
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
