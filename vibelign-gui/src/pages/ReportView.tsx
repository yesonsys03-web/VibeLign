// === ANCHOR: REPORT_VIEW_START ===
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listPlanningChatSessions } from "../lib/vib";
import type { PlanningSessionSummary } from "../lib/vib/types";
import { emitReportModel, renderReportWithDecisions, stampPdfPageNumbers, type ReportType } from "../lib/vib/report";
import { useReportExport } from "../components/report-review/useReportExport";
import type { EmitPayload } from "../lib/vib/reportModel";
import type { ReportFontSizes } from "../lib/vib/reportFontSizes";
import type { ReportFonts } from "../lib/vib/reportFonts";
import type {
  ReportComposerFormat,
  ReportComposerReviewRequestPayload,
} from "../components/plan-doc/useReportComposerGeneration";
import {
  applyReportSessionDraftToEmitPayload,
  type ReportSessionDraft,
} from "../components/plan-doc/reportSessionDraft";
import { ReportViewComposerPanel } from "./ReportViewComposerPanel";
import { ReportViewPlanList } from "./ReportViewPlanList";
import { ReportViewReviewPanel } from "./ReportViewReviewPanel";

interface ReportViewProps {
  projectDir: string;
  /** 보고서로 만들 기획안이 하나도 없을 때 기획 시작으로 이동. */
  onStart?: () => void;
  /** 문서/코드탐색에서 우클릭→보고서로 넘어온 소스 .md 경로(루트 상대). */
  sourcePath?: string | null;
  /** sourcePath 를 모달로 소비한 뒤 부모 상태를 비우게 알린다(재진입 시 재오픈 방지). */
  onSourceHandled?: () => void;
}

/**
 * 기획 단계 '보고서 작성' 서브탭. 저장된 기획안을 골라 업무용 보고서
 * (HTML·PDF·Word·PPT)로 내보낸다. 직장인용 — 기획 내용을 보고서 독자에 맞게 변환.
 */
export default function ReportView({ projectDir, onStart, sourcePath, onSourceHandled }: ReportViewProps) {
  const [plans, setPlans] = useState<PlanningSessionSummary[] | null>(null);
  const [reportFor, setReportFor] = useState<string | null>(null);
  const [fromDoc, setFromDoc] = useState(false);
  const [review, setReview] = useState<
    {
      payload: EmitPayload;
      plan: string;
      type: ReportType;
      format: ReportComposerFormat;
      theme: string;
      author: string;
      pageNumbers: boolean;
      fontSizes: ReportFontSizes;
      fonts: ReportFonts;
      draft?: ReportSessionDraft;
    } | null
  >(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewErr, setReviewErr] = useState<string | null>(null);
  const { exportedPath, exportErr, exportTo, reset } = useReportExport();

  async function handleReviewRequest(request: ReportComposerReviewRequestPayload) {
    if (!reportFor) return;
    const plan = reportFor;
    const { reportType, format, theme, author, pageNumbers, fontSizes, fonts, draft } = request;
    setReviewBusy(true);
    setReviewErr(null);
    reset();
    const r = await emitReportModel(projectDir, plan, reportType, true, author);
    setReviewBusy(false);
    if (r.ok) {
      setReview({
        payload: draft === undefined ? r.payload : applyReportSessionDraftToEmitPayload(r.payload, draft),
        plan,
        type: reportType,
        format,
        theme,
        author,
        pageNumbers,
        fontSizes,
        fonts,
        ...(draft === undefined ? {} : { draft }),
      });
    }
    else setReviewErr(r.error);
  }

  async function handleReviewConfirm(rejectBlocks: [number, number][]) {
    if (!review) return;
    const { plan, type, format, payload, theme, author, pageNumbers, fontSizes, fonts } = review;
    setReview(null);
    setReviewBusy(true);
    setReviewErr(null);
    const r = await renderReportWithDecisions({
      cwd: projectDir,
      planPath: plan,
      reportType: type,
      format,
      rejectBlocks,
      payload,
      theme,
      author,
      pageNumbers,
      fontSizes,
      fonts,
    });
    if (!r.ok) {
      setReviewBusy(false);
      setReviewErr(r.error);
      return;
    }
    let finalPath = r.path;
    if (format === "pdf") {
      try {
        finalPath = await invoke<string>("export_report_pdf", {
          root: projectDir, htmlPath: r.path, outPdf: r.path.replace(/\.html$/i, ".pdf"),
        });
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        setReviewBusy(false);
        setReviewErr(`PDF 변환 실패: ${detail}`);
        return;
      }
      if (pageNumbers) await stampPdfPageNumbers(projectDir, finalPath);
    }
    await exportTo(finalPath);
    setReviewBusy(false);
  }

  useEffect(() => {
    if (!sourcePath) return;
    setReportFor(sourcePath);
    setFromDoc(true);
    onSourceHandled?.();
  }, [sourcePath, onSourceHandled]);

  useEffect(() => {
    let cancelled = false;
    listPlanningChatSessions(projectDir)
      .then((rows) => {
        if (!cancelled) setPlans(rows.filter((r) => Boolean(r.outputPath)));
      })
      .catch(() => {
        if (!cancelled) setPlans([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectDir]);

  if (plans !== null && plans.length === 0 && !reportFor && !review && !reviewBusy && !exportedPath) {
    return (
      <ReportViewPlanList
        plans={plans}
        reviewBusy={reviewBusy}
        reviewErr={reviewErr}
        exportErr={exportErr}
        exportedPath={exportedPath}
        onStart={onStart}
        onSelectPlan={openPlanReport}
      />
    );
  }

  if (review) {
    return (
      <ReportViewReviewPanel
        payload={review.payload}
        onConfirm={(rejectBlocks) => void handleReviewConfirm(rejectBlocks)}
        onCancel={() => setReview(null)}
      />
    );
  }

  if (reportFor) {
    return (
      <ReportViewComposerPanel
        reportFor={reportFor}
        projectDir={projectDir}
        fromDoc={fromDoc}
        onBack={closeReportComposer}
        onReviewRequest={(request) => void handleReviewRequest(request)}
      />
    );
  }

  return (
    <ReportViewPlanList
      plans={plans}
      reviewBusy={reviewBusy}
      reviewErr={reviewErr}
      exportErr={exportErr}
      exportedPath={exportedPath}
      onStart={onStart}
      onSelectPlan={openPlanReport}
    />
  );

  function openPlanReport(outputPath: string): void {
    setFromDoc(false);
    setReportFor(outputPath);
  }

  function closeReportComposer(): void {
    setReportFor(null);
    setFromDoc(false);
  }
}
// === ANCHOR: REPORT_VIEW_END ===
