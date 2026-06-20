// === ANCHOR: REPORT_COMPOSER_GENERATION_START ===
import { useState } from "react";
import { confirm as tauriConfirm } from "@tauri-apps/plugin-dialog";

import {
  emitReportModel,
  generatePlanningReport,
  generateReportOffice,
  generateReportPdf,
  renderReportFileWithDecisions,
  renderReportHtmlWithDecisions,
  requestReportAssistance,
  type PdfResult,
  type ReportResult,
  type ReportType,
} from "../../lib/vib/report";
import type { ReportAssistPayload } from "../../lib/vib/reportAssist";
import type { ReportFontSizes } from "../../lib/vib/reportFontSizes";
import type { ReportFonts } from "../../lib/vib/reportFonts";
import { isPolishable, type EmitPayload } from "../../lib/vib/reportModel";
import type { ReportQualityPayload } from "../../lib/vib/reportQuality";
import type { ReportQualityLongSource, ReportQualityPanelProceedPayload } from "./ReportQualityPanel";
import { applyReportSessionDraftToEmitPayload, createReportSessionDraft, hasReportSessionDraft, type ReportSessionDraft } from "./reportSessionDraft";

const POLISH_WARN_BLOCKS = 20;
const SECONDS_PER_BLOCK_EST = 15;

export type ReportComposerFormat = "html" | "pdf" | "docx" | "pptx";

export type ReportComposerResultState =
  | { kind: "html"; ok: true; path: string; reportType: string; html: string }
  | { kind: "file"; ok: true; path: string }
  | { ok: false; error: string };

export type ReportComposerReviewRequestPayload = {
  readonly reportType: ReportType;
  readonly format: ReportComposerFormat;
  readonly theme: string;
  readonly author: string;
  readonly pageNumbers: boolean;
  readonly fontSizes: ReportFontSizes;
  readonly fonts: ReportFonts;
  readonly draft?: ReportSessionDraft;
};

export type ReportComposerReviewRequest = (payload: ReportComposerReviewRequestPayload) => void;

export type ReportComposerGenerationOptions = {
  readonly planPath: string;
  readonly cwd: string;
  readonly reportType: ReportType;
  readonly format: ReportComposerFormat;
  readonly polish: boolean;
  readonly theme: string;
  readonly author: string;
  readonly reportTypeLabel: string;
  readonly pageNumbers: boolean;
  readonly fontSizes: ReportFontSizes;
  readonly fonts: ReportFonts;
  readonly onReviewRequest?: ReportComposerReviewRequest;
  readonly onClose: () => void;
  readonly onReportTypeChange: (reportType: ReportType) => void;
  readonly onResetGeneratedArtifacts: () => void;
  readonly onExportReady: (path: string) => void;
};

export type ReportQualityReviewState = {
  readonly quality: ReportQualityPayload;
  readonly assistance: ReportAssistPayload;
  readonly longSource?: ReportQualityLongSource;
};

class ReportAssistanceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReportAssistanceError";
  }
}

function countPolishableBlocks(payload: EmitPayload): number {
  return payload.base.sections.reduce((n, s) => n + s.blocks.filter(isPolishable).length, 0);
}

function inferLongSource(assistance: ReportAssistPayload): ReportQualityLongSource | undefined {
  let totalLines = 0;
  const chunkIds = new Set<string>();
  for (const item of [...assistance.suggestions, ...assistance.questions]) {
    for (const ref of item.source_refs) {
      chunkIds.add(ref.chunk_id);
      totalLines = Math.max(totalLines, ref.end_line ?? 0);
    }
  }
  return totalLines > 600 ? { totalLines, analyzedSections: chunkIds.size } : undefined;
}

function activeReportSessionDraft(draft: ReportSessionDraft | null): ReportSessionDraft | null {
  return draft !== null && hasReportSessionDraft(draft) ? draft : null;
}

async function renderDraftHtml(
  options: ReportComposerGenerationOptions,
  draft: ReportSessionDraft,
): Promise<ReportResult> {
  const { cwd, planPath, reportType, polish, author, theme, pageNumbers, fontSizes, fonts } = options;
  const emitted = await emitReportModel(cwd, planPath, reportType, polish, author);
  if (!emitted.ok) return emitted;
  return renderReportHtmlWithDecisions({
    cwd,
    planPath,
    reportType,
    format: "html",
    rejectBlocks: [],
    payload: applyReportSessionDraftToEmitPayload(emitted.payload, draft),
    theme,
    author,
    pageNumbers,
    fontSizes,
    fonts,
  });
}

async function renderDraftFile(options: ReportComposerGenerationOptions, draft: ReportSessionDraft, format: "pdf" | "docx" | "pptx"): Promise<PdfResult> {
  const { cwd, planPath, reportType, polish, author, theme, pageNumbers, fontSizes, fonts } = options;
  const emitted = await emitReportModel(cwd, planPath, reportType, polish, author);
  if (!emitted.ok) return emitted;
  return renderReportFileWithDecisions({
    cwd,
    planPath,
    reportType,
    format,
    rejectBlocks: [],
    payload: applyReportSessionDraftToEmitPayload(emitted.payload, draft),
    theme,
    author,
    pageNumbers,
    fontSizes,
    fonts,
  });
}

export function useReportComposerGeneration(options: ReportComposerGenerationOptions) {
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ReportComposerResultState | null>(null);
  const [qualityReview, setQualityReview] = useState<ReportQualityReviewState | null>(null);

  const requestAssistance = async (): Promise<ReportAssistPayload> => {
    const response = await requestReportAssistance({
      cwd: options.cwd,
      planPath: options.planPath,
      reportType: options.reportType,
      author: options.author,
    });
    if (!response.ok) throw new ReportAssistanceError(response.error);
    const longSource = inferLongSource(response.payload.assistance);
    setQualityReview((state) =>
      state === null
        ? state
        : {
            ...state,
            assistance: response.payload.assistance,
            ...(longSource === undefined ? {} : { longSource }),
          },
    );
    return response.payload.assistance;
  };

  const runFinalGeneration = async (draft: ReportSessionDraft | null) => {
    const activeDraft = activeReportSessionDraft(draft);
    if (options.polish && options.onReviewRequest !== undefined) {
      setGenerating(false);
      const probe = await emitReportModel(options.cwd, options.planPath, options.reportType, false, options.author);
      if (probe.ok) {
        const blocks = countPolishableBlocks(probe.payload);
        if (blocks > POLISH_WARN_BLOCKS) {
          const mins = Math.max(1, Math.round((blocks * SECONDS_PER_BLOCK_EST) / 60));
          const proceed = await tauriConfirm(
            `이 문서는 다듬기 대상 블록이 ${blocks}개예요.\n` +
              `AI 어조 다듬기는 블록마다 순차로 처리해 약 ${mins}분 이상 걸릴 수 있어요.\n\n` +
              `취소하면 'AI 어조 다듬기'를 끄고 바로 생성할 수 있어요.`,
            { title: "AI 어조 다듬기", kind: "warning", okLabel: "계속", cancelLabel: "취소" },
          );
          if (!proceed) return;
        }
      }
      options.onReviewRequest({
        reportType: options.reportType,
        format: options.format,
        theme: options.theme,
        author: options.author,
        pageNumbers: options.pageNumbers,
        fontSizes: options.fontSizes,
        fonts: options.fonts,
        ...(activeDraft === null ? {} : { draft: activeDraft }),
      });
      options.onClose();
      return;
    }

    setResult(null);
    options.onResetGeneratedArtifacts();
    let next: ReportComposerResultState;
    if (options.format === "html") {
      const r = activeDraft === null
        ? await generatePlanningReport(options.cwd, options.planPath, options.reportType, options.polish, options.theme, options.author, options.pageNumbers, options.fontSizes, options.fonts)
        : await renderDraftHtml(options, activeDraft);
      next = r.ok ? { kind: "html", ok: true, path: r.path, reportType: r.reportType, html: r.html } : r;
    } else if (options.format === "pdf") {
      const r = activeDraft === null
        ? await generateReportPdf(options.cwd, options.planPath, options.reportType, options.polish, options.theme, options.author, options.pageNumbers, options.fontSizes, options.fonts)
        : await renderDraftFile(options, activeDraft, "pdf");
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    } else {
      const r = activeDraft === null
        ? await generateReportOffice(options.cwd, options.planPath, options.reportType, options.format, options.polish, options.theme, options.author, options.pageNumbers, options.fontSizes, options.fonts)
        : await renderDraftFile(options, activeDraft, options.format);
      next = r.ok ? { kind: "file", ok: true, path: r.path } : r;
    }
    setResult(next);
    setGenerating(false);
    if (next.ok) options.onExportReady(next.path);
  };

  const handleQualityProceed = (payload: ReportQualityPanelProceedPayload) => {
    setQualityReview(null);
    setGenerating(true);
    void runFinalGeneration(createReportSessionDraft(payload));
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setQualityReview(null);
    const probe = await emitReportModel(options.cwd, options.planPath, options.reportType, false, options.author);

    if (probe.ok && probe.payload.base.sections.length === 0 && options.reportType !== "doc") {
      setGenerating(false);
      const switchToDoc = await tauriConfirm(
        `'${options.reportTypeLabel}' 종류로는 이 문서에서 보고서 내용을 찾지 못했어요.\n` +
          `업무 보고·제안서·결과 보고는 VibeLign 기획 양식 전용이에요.\n\n` +
          `'문서 그대로'로 바꿀까요? (바꾼 뒤 다시 '보고서 생성'을 누르세요.)`,
        { title: "보고서 종류 확인", kind: "warning", okLabel: "문서 그대로로 변경", cancelLabel: "취소" },
      );
      if (switchToDoc) options.onReportTypeChange("doc");
      return;
    }

    if (probe.ok && probe.payload.quality.status === "block") {
      setGenerating(false);
      setQualityReview({ quality: probe.payload.quality, assistance: probe.payload.assistance });
      return;
    }

    if (probe.ok && probe.payload.quality.status === "warn") {
      setGenerating(false);
      setQualityReview({ quality: probe.payload.quality, assistance: probe.payload.assistance });
      return;
    }

    await runFinalGeneration(null);
  };

  return {
    generating,
    result,
    qualityReview,
    requestAssistance,
    handleQualityProceed,
    handleGenerate,
    cancelQualityReview: () => setQualityReview(null),
  };
}
// === ANCHOR: REPORT_COMPOSER_GENERATION_END ===
