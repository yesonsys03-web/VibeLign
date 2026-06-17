// === ANCHOR: EXPORTREPORTMODAL_START ===
import { useState, type CSSProperties } from "react";
import { openPath } from "@tauri-apps/plugin-opener";
import { confirm as tauriConfirm } from "@tauri-apps/plugin-dialog";
import { pickFolder } from "../../lib/vib/system";
import {
  copyReportTo,
  emitReportModel,
  generatePlanningReport,
  generateReportOffice,
  generateReportPdf,
  getReportExportDir,
  setReportExportDir,
  type ReportType,
} from "../../lib/vib/report";
import { isPolishable, type EmitPayload } from "../../lib/vib/reportModel";

// AI 다듬기는 블록마다 순차로 LLM 을 1회 호출한다(머신·provider 에 따라 블록당 ~15~20초).
// 이 수를 넘으면 수 분~수십 분이 걸려 사실상 멈춘 듯 보이므로 생성 전 경고한다.
// 기획안 보고서는 블록이 6~7개라 절대 걸리지 않고, 일반 문서(--type doc)에만 작동한다.
const POLISH_WARN_BLOCKS = 20;
const SECONDS_PER_BLOCK_EST = 15;

// === ANCHOR: EXPORTREPORTMODAL_COUNTPOLISHABLEBLOCKS_START ===
function countPolishableBlocks(payload: EmitPayload): number {
  return payload.base.sections.reduce((n, s) => n + s.blocks.filter(isPolishable).length, 0);
}
// === ANCHOR: EXPORTREPORTMODAL_COUNTPOLISHABLEBLOCKS_END ===

type Format = "html" | "pdf" | "docx" | "pptx";
type ResultState =
  | { kind: "html"; ok: true; path: string; reportType: string; html: string }
  | { kind: "file"; ok: true; path: string }
  | { ok: false; error: string };

const TYPES: { id: ReportType; label: string }[] = [
  { id: "work", label: "업무 보고" },
  { id: "proposal", label: "제안서" },
  { id: "result", label: "결과 보고" },
  { id: "doc", label: "문서 그대로" },
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
  onReviewRequest?: (reportType: ReportType, format: Format, theme: string, author: string, pageNumbers: boolean) => void;
  /** 모달이 열릴 때 초기 선택될 보고서 종류(문서 우클릭 진입 시 "doc"). 기본 "work". */
  defaultType?: ReportType;
}

const THEMES: { id: string; label: string }[] = [
  { id: "classic", label: "클래식" },
  { id: "minimal", label: "모던 미니멀" },
  { id: "executive", label: "임원 보고형" },
  { id: "compact", label: "컴팩트" },
  { id: "pastel", label: "부드러운 파스텔" },
];

// === ANCHOR: EXPORTREPORTMODAL_EXPORTREPORTMODAL_START ===
export function ExportReportModal({ open, planPath, cwd, onClose, onReviewRequest, defaultType }: ExportReportModalProps) {
  const [reportType, setReportType] = useState<ReportType>(defaultType ?? "work");
  const [format, setFormat] = useState<Format>("html");
  const [polish, setPolish] = useState(false);
  const [theme, setTheme] = useState<string>(() => {
    try {
      return localStorage.getItem("vibelign_report_theme") || "classic";
    } catch {
      return "classic";
    }
  });
  const [author, setAuthor] = useState<string>(() => {
    try {
      return localStorage.getItem("vibelign_report_author") || "";
    } catch {
      return "";
    }
  });
  const [pageNumbers, setPageNumbers] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ResultState | null>(null);
  const [openErr, setOpenErr] = useState<string | null>(null);
  // 사용자에게 전달된 최종 저장 위치(.vibelign/reports 내부 사본과 별개로 복사한 곳).
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);

  if (!open) return null;

  // 생성된 보고서를 지정 폴더로 복사한다. dir 가 없으면 기본 폴더(설정값→OS 문서 폴더)를 쓴다.
  // === ANCHOR: EXPORTREPORTMODAL_EXPORTTO_START ===
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
  // === ANCHOR: EXPORTREPORTMODAL_EXPORTTO_END ===

  // "다른 위치에 저장": 폴더 선택 → 복사 → 그 폴더를 다음 기본값으로 기억.
  // === ANCHOR: EXPORTREPORTMODAL_HANDLECHOOSELOCATION_START ===
  const handleChooseLocation = async () => {
    if (!result || !result.ok) return;
    const dir = await pickFolder().catch(() => null);
    if (!dir) return;
    await exportTo(result.path, dir);
    void setReportExportDir(dir).catch(() => {});
  };
  // === ANCHOR: EXPORTREPORTMODAL_HANDLECHOOSELOCATION_END ===

  // === ANCHOR: EXPORTREPORTMODAL_HANDLEGENERATE_START ===
  const handleGenerate = async () => {
    // 사전 점검(다듬기 없이 → LLM 미호출, 즉시): 선택한 종류로 추출된 섹션 수를 미리 본다.
    setGenerating(true);
    const probe = await emitReportModel(cwd, planPath, reportType, false, author);

    // 빈 보고서 가드: 일반 문서에 기획 양식 종류(업무/제안/결과)를 고르면 추출 0 → 빈 보고서.
    // 'doc'(문서 그대로)는 구조를 보존하므로 제외한다.
    if (probe.ok && probe.payload.base.sections.length === 0 && reportType !== "doc") {
      setGenerating(false);
      const label = TYPES.find((t) => t.id === reportType)?.label ?? reportType;
      const switchToDoc = await tauriConfirm(
        `'${label}' 종류로는 이 문서에서 보고서 내용을 찾지 못했어요.\n` +
          `업무 보고·제안서·결과 보고는 VibeLign 기획 양식 전용이에요.\n\n` +
          `'문서 그대로'로 바꿀까요? (바꾼 뒤 다시 '보고서 생성'을 누르세요.)`,
        { title: "보고서 종류 확인", kind: "warning", okLabel: "문서 그대로로 변경", cancelLabel: "취소" },
      );
      if (switchToDoc) setReportType("doc");
      return; // 생성 중단 — 사용자가 종류 확인 후 다시 생성
    }

    // 다듬기 ON + 리뷰 핸들러 제공 시: 인라인 생성 대신 검토 화면으로 위임한다.
    if (polish && onReviewRequest) {
      setGenerating(false);
      // 큰 문서 경고: 다듬기는 블록당 순차 LLM 호출이라 오래 걸린다.
      if (probe.ok) {
        const blocks = countPolishableBlocks(probe.payload);
        if (blocks > POLISH_WARN_BLOCKS) {
          const mins = Math.max(1, Math.round((blocks * SECONDS_PER_BLOCK_EST) / 60));
          // window.confirm 은 Tauri WKWebView 에서 반환값이 신뢰 불가 → 플러그인 다이얼로그 사용.
          const proceed = await tauriConfirm(
            `이 문서는 다듬기 대상 블록이 ${blocks}개예요.\n` +
              `AI 어조 다듬기는 블록마다 순차로 처리해 약 ${mins}분 이상 걸릴 수 있어요.\n\n` +
              `취소하면 'AI 어조 다듬기'를 끄고 바로 생성할 수 있어요.`,
            { title: "AI 어조 다듬기", kind: "warning", okLabel: "계속", cancelLabel: "취소" },
          );
          if (!proceed) return; // 모달 유지 — 사용자가 다듬기 끄고 다시 누르면 즉시 생성
        }
      }
      onReviewRequest(reportType, format, theme, author, pageNumbers);
      onClose();
      return;
    }
    // 다듬기 OFF: 인라인 생성(setGenerating 은 위에서 이미 true).
    setResult(null);
    setOpenErr(null);
    setExportedPath(null);
    setExportErr(null);
    let next: ResultState;
    if (format === "html") {
      const r = await generatePlanningReport(cwd, planPath, reportType, polish, theme, author, pageNumbers);
      next = r.ok
        ? { kind: "html", ok: true, path: r.path, reportType: r.reportType, html: r.html }
        : r;
    } else if (format === "pdf") {
      const r = await generateReportPdf(cwd, planPath, reportType, polish, theme, author, pageNumbers);
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    } else {
      const r = await generateReportOffice(cwd, planPath, reportType, format, polish, theme, author, pageNumbers);
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    }
    setResult(next);
    setGenerating(false);
    // 생성 성공 시 기본 폴더로 자동 복사(내부 .vibelign/reports 사본은 그대로 유지).
    if (next.ok) void exportTo(next.path);
  };
  // === ANCHOR: EXPORTREPORTMODAL_HANDLEGENERATE_END ===

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
              디자인 테마{" "}
              <select
                aria-label="디자인 테마"
                value={theme}
                onChange={(e) => {
                  setTheme(e.target.value);
                  try {
                    localStorage.setItem("vibelign_report_theme", e.target.value);
                  } catch {
                    /* 테스트 환경 등 localStorage 미지원 시 무시 */
                  }
                }}
              >
                {THEMES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>
              작성자{" "}
              <input
                type="text"
                aria-label="작성자"
                value={author}
                placeholder="(선택) 이름"
                onChange={(e) => {
                  setAuthor(e.target.value);
                  try {
                    localStorage.setItem("vibelign_report_author", e.target.value);
                  } catch {
                    /* localStorage 미지원 시 무시 */
                  }
                }}
              />
            </label>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label>
              <input
                type="checkbox"
                checked={pageNumbers}
                onChange={(e) => setPageNumbers(e.target.checked)}
              />{" "}
              페이지 번호 (Word·PDF)
            </label>
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
// === ANCHOR: EXPORTREPORTMODAL_EXPORTREPORTMODAL_END ===
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
// === ANCHOR: EXPORTREPORTMODAL_END ===
