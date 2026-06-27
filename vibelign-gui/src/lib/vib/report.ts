// === ANCHOR: REPORT_START ===
import { invoke } from "@tauri-apps/api/core";
import { runVib } from "./core";
import { loadDoc } from "../docs";
import { reportFontSizeArgs, type ReportFontSizes } from "./reportFontSizes";
import { reportFontArgs, type ReportFonts } from "./reportFonts";
import type { EmitPayload } from "./reportModel";
import {
  REPORT_RENDER_PAYLOAD_PATH_ENV,
  removeReportRenderPayload,
  writeReportRenderPayload,
} from "./reportRenderPayload";

export type ReportType = "work" | "proposal" | "result" | "doc";

export type ReportResult =
  | { ok: true; path: string; reportType: string; html: string }
  | { ok: false; error: string };

/** 절대 보고서 경로를 프로젝트 루트 기준 상대경로로 변환한다.
 *  read_file(loadDoc) 가 root-상대 경로를 기대하기 때문. 루트 밖이면 원본 유지. */
// === ANCHOR: REPORT_TOPROJECTRELATIVE_START ===
export function toProjectRelative(cwd: string, absPath: string): string {
  // === ANCHOR: REPORT_NORM_START ===
  const norm = (p: string) => p.replace(/\\/g, "/").replace(/\/+$/, "");
  const root = norm(cwd);
  const p = norm(absPath);
  if (p === root) return "";
  if (p.startsWith(root + "/")) return p.slice(root.length + 1);
  return absPath;
// === ANCHOR: REPORT_TOPROJECTRELATIVE_END ===
}

// === ANCHOR: REPORT_GENERATEPLANNINGREPORT_START ===
export async function generatePlanningReport(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  polish = false,
  theme = "classic",
  author = "",
  pageNumbers = true,
  fontSizes: ReportFontSizes = {},
  fonts: ReportFonts = {},
): Promise<ReportResult> {
  const res = await runVib(
    [
      "report", planPath, "--type", reportType, "--format", "html", "--theme", theme,
      "--author", author, "--json",
      ...reportFontSizeArgs(fontSizes),
      ...reportFontArgs(fonts),
      ...(polish ? ["--polish"] : []),
      ...(pageNumbers ? [] : ["--no-page-numbers"]),
    ],
    cwd,
  );

  let parsed: { ok?: boolean; path?: string; report_type?: string; error?: string };
  try {
    parsed = JSON.parse(res.stdout.trim());
  } catch {
    return {
      ok: false,
      error: res.stderr.trim() || res.stdout.trim() || "보고서 생성에 실패했어요.",
    };
  }

  if (!parsed.ok || !parsed.path) {
    return { ok: false, error: String(parsed.error ?? "보고서 생성에 실패했어요.") };
  }

  const rel = toProjectRelative(cwd, parsed.path);
  try {
    const doc = await loadDoc(cwd, rel);
    return {
      ok: true,
      path: parsed.path,
      reportType: String(parsed.report_type ?? reportType),
      html: doc.content,
    };
  } catch (error) {
    // CLI 는 성공했지만 생성된 파일 읽기가 실패(권한/삭제/락) → 모달이 멈추지 않도록
    // 래퍼의 {ok:false} 계약을 유지한다.
    if (error instanceof Error) return { ok: false, error: `보고서 파일을 읽지 못했어요: ${error.message}` };
    throw error;
  }
  // === ANCHOR: REPORT_NORM_END ===
}
// === ANCHOR: REPORT_GENERATEPLANNINGREPORT_END ===

/** 사용자가 지정한 보고서 기본 내보내기 폴더. 미설정 시 OS 문서 폴더로 폴백한다. */
// === ANCHOR: REPORT_GETREPORTEXPORTDIR_START ===
export async function getReportExportDir(): Promise<string> {
  return invoke<string>("get_report_export_dir");
}
// === ANCHOR: REPORT_GETREPORTEXPORTDIR_END ===

/** 보고서 기본 내보내기 폴더를 저장한다(다음 내보내기의 기본값). */
// === ANCHOR: REPORT_SETREPORTEXPORTDIR_START ===
export async function setReportExportDir(dir: string): Promise<void> {
  return invoke<void>("set_report_export_dir", { dir });
}
// === ANCHOR: REPORT_SETREPORTEXPORTDIR_END ===

/** 생성된 보고서 파일(.vibelign/reports/*)을 지정 폴더로 복사하고 실제 대상 경로를 돌려준다. */
// === ANCHOR: REPORT_COPYREPORTTO_START ===
export async function copyReportTo(src: string, destDir: string): Promise<string> {
  return invoke<string>("copy_report_to", { src, destDir });
}
// === ANCHOR: REPORT_COPYREPORTTO_END ===

/** 생성된 PDF 에 페이지 번호("N / M")를 스탬프한다. 실패해도 false 만 돌려주고 throw 안 함(원본 PDF 보존). */
// === ANCHOR: REPORT_STAMPPDFPAGENUMBERS_START ===
export async function stampPdfPageNumbers(cwd: string, pdfPath: string): Promise<boolean> {
  try {
    const res = await runVib(["report-stamp-pdf", pdfPath, "--json"], cwd);
    return JSON.parse(res.stdout.trim()).ok === true;
  } catch {
    return false;
  }
}
// === ANCHOR: REPORT_STAMPPDFPAGENUMBERS_END ===

export type PdfResult = { ok: true; path: string } | { ok: false; error: string };

async function exportReportHtmlToPdf(cwd: string, htmlPath: string, pageNumbers: boolean): Promise<PdfResult> {
  const outPdf = htmlPath.replace(/\.html$/i, ".pdf");
  try {
    const saved = await invoke<string>("export_report_pdf", { root: cwd, htmlPath, outPdf });
    if (pageNumbers) await stampPdfPageNumbers(cwd, saved);
    return { ok: true, path: saved };
  } catch (error) {
    if (error instanceof Error) return { ok: false, error: `PDF 생성 실패: ${error.message}` };
    throw error;
  }
}

// === ANCHOR: REPORT_GENERATEREPORTPDF_START ===
export async function generateReportPdf(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  polish = false,
  theme = "classic",
  author = "",
  pageNumbers = true,
  fontSizes: ReportFontSizes = {},
  fonts: ReportFonts = {},
): Promise<PdfResult> {
  const html = await generatePlanningReport(
    cwd,
    planPath,
    reportType,
    polish,
    theme,
    author,
    pageNumbers,
    fontSizes,
    fonts,
  );
  if (!html.ok) return html;
  return exportReportHtmlToPdf(cwd, html.path, pageNumbers);
}
// === ANCHOR: REPORT_GENERATEREPORTPDF_END ===

/** 생성된 보고서 PDF 의 원시 바이트를 읽어온다(인앱 pdf.js 미리보기용).
 *  Rust 가 tauri::ipc::Response 로 보내므로 JS 는 ArrayBuffer 로 받는다. */
// === ANCHOR: REPORT_READREPORTPDFBYTES_START ===
export async function readReportPdfBytes(root: string, path: string): Promise<ArrayBuffer> {
  return invoke<ArrayBuffer>("read_report_pdf_bytes", { root, path });
}
// === ANCHOR: REPORT_READREPORTPDFBYTES_END ===

export type OfficeFormat = "docx" | "pptx";

/** Word(.docx)/PPT(.pptx) 를 vib report 로 생성한다. CLI 가 바이너리 파일을 쓰고
 *  경로를 반환하므로 미리보기 없이 경로만 돌려준다(모달은 "파일 열기"로 처리). */
// === ANCHOR: REPORT_GENERATEREPORTOFFICE_START ===
export async function generateReportOffice(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  format: OfficeFormat,
  polish = false,
  theme = "classic",
  author = "",
  pageNumbers = true,
  fontSizes: ReportFontSizes = {},
  fonts: ReportFonts = {},
): Promise<PdfResult> {
  const res = await runVib(
    [
      "report", planPath, "--type", reportType, "--format", format, "--theme", theme,
      "--author", author, "--json",
      ...reportFontSizeArgs(fontSizes),
      ...reportFontArgs(fonts),
      ...(polish ? ["--polish"] : []),
      ...(pageNumbers ? [] : ["--no-page-numbers"]),
    ],
    cwd,
  );
  let parsed: { ok?: boolean; path?: string; error?: string };
  try {
    parsed = JSON.parse(res.stdout.trim());
  } catch {
    return {
      ok: false,
      error: res.stderr.trim() || res.stdout.trim() || "보고서 생성에 실패했어요.",
    };
  }
  if (!parsed.ok || !parsed.path) {
    return { ok: false, error: String(parsed.error ?? "보고서 생성에 실패했어요.") };
  }
  return { ok: true, path: parsed.path };
}
// === ANCHOR: REPORT_GENERATEREPORTOFFICE_END ===

// === ANCHOR: REPORT_EMITREPORTMODEL_START ===
export { emitReportModel, requestReportAssistance } from "./reportEmit";
export type { EmitResult, ReportAssistancePayload, ReportAssistanceRequest, ReportAssistanceResult } from "./reportEmit";
// === ANCHOR: REPORT_EMITREPORTMODEL_END ===

/** 거부 블록 인덱스 + emit 의 polishKey 로 캐시 polished 를 병합해 렌더·저장한다.
 *  PDF 는 호출자가 결과 HTML 을 export_report_pdf 로 변환한다(여기서는 html 로 렌더). */
// === ANCHOR: REPORT_RENDERREPORTWITHDECISIONS_START ===
export type ReportRenderDecisionsRequest = {
  readonly cwd: string; readonly planPath: string; readonly reportType: ReportType;
  readonly format: "html" | "pdf" | "docx" | "pptx";
  readonly rejectBlocks: readonly [number, number][]; readonly payload: EmitPayload;
  readonly theme?: string; readonly author?: string; readonly pageNumbers?: boolean;
  readonly fontSizes?: ReportFontSizes; readonly fonts?: ReportFonts;
};

export type ReportRenderFileDecisionsRequest = Omit<ReportRenderDecisionsRequest, "format"> & { readonly format: "pdf" | "docx" | "pptx" };

export async function renderReportWithDecisions(request: ReportRenderDecisionsRequest): Promise<PdfResult> {
  const {
    cwd,
    planPath,
    reportType,
    format,
    rejectBlocks,
    payload,
    theme = "classic",
    author = "",
    pageNumbers = true,
    fontSizes = {},
    fonts = {},
  } = request;
  const fmt = format === "pdf" ? "html" : format;
  const args = [
    "report", planPath, "--type", reportType, "--format", fmt,
    "--reject-blocks", JSON.stringify(rejectBlocks), "--polish-key", payload.key, "--theme", theme,
    "--author", author, "--json",
    ...reportFontSizeArgs(fontSizes),
    ...reportFontArgs(fonts),
    ...(pageNumbers ? [] : ["--no-page-numbers"]),
  ];
  const payloadPath = await writeReportRenderPayload(cwd, payload);
  try {
    const res = await runVib(args, cwd, {
      [REPORT_RENDER_PAYLOAD_PATH_ENV]: payloadPath,
    });
    try {
      const parsed = JSON.parse(res.stdout.trim());
      if (!parsed.ok || !parsed.path) return { ok: false, error: String(parsed.error ?? "렌더 실패") };
      return { ok: true, path: parsed.path };
    } catch {
      return { ok: false, error: res.stderr.trim() || "렌더 실패" };
    }
  } finally {
    await removeReportRenderPayload(cwd, payloadPath);
  }
}

export async function renderReportHtmlWithDecisions(request: ReportRenderDecisionsRequest): Promise<ReportResult> {
  const rendered = await renderReportWithDecisions({ ...request, format: "html" });
  if (!rendered.ok) return rendered;
  const rel = toProjectRelative(request.cwd, rendered.path);
  try {
    const doc = await loadDoc(request.cwd, rel);
    return {
      ok: true,
      path: rendered.path,
      reportType: request.reportType,
      html: doc.content,
    };
  } catch (error) {
    if (error instanceof Error) return { ok: false, error: `보고서 파일을 읽지 못했어요: ${error.message}` };
    throw error;
  }
}

export async function renderReportFileWithDecisions(request: ReportRenderFileDecisionsRequest): Promise<PdfResult> {
  const rendered = await renderReportWithDecisions(request);
  if (!rendered.ok || request.format !== "pdf") return rendered;
  return exportReportHtmlToPdf(request.cwd, rendered.path, request.pageNumbers ?? true);
}
// === ANCHOR: REPORT_RENDERREPORTWITHDECISIONS_END ===
// === ANCHOR: REPORT_END ===
