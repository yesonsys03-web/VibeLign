// === ANCHOR: REPORT_VIEW_START ===
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listPlanningChatSessions } from "../lib/vib";
import type { PlanningSessionSummary } from "../lib/vib/types";
import { ExportReportModal } from "../components/plan-doc/ExportReportModal";
import { emitReportModel, renderReportWithDecisions, type ReportType } from "../lib/vib/report";
import { ReportDiffReview } from "../components/report-review/ReportDiffReview";
import { useReportExport } from "../components/report-review/useReportExport";
import type { EmitPayload } from "../lib/vib/reportModel";

type Fmt = "html" | "pdf" | "docx" | "pptx";

interface ReportViewProps {
  projectDir: string;
  /** 보고서로 만들 기획안이 하나도 없을 때 기획 시작으로 이동. */
  onStart?: () => void;
}

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}

/**
 * 기획 단계 '보고서 작성' 서브탭. 저장된 기획안을 골라 업무용 보고서
 * (HTML·PDF·Word·PPT)로 내보낸다. 직장인용 — 기획 내용을 보고서 독자에 맞게 변환.
 */
export default function ReportView({ projectDir, onStart }: ReportViewProps) {
  const [plans, setPlans] = useState<PlanningSessionSummary[] | null>(null);
  const [reportFor, setReportFor] = useState<string | null>(null);
  const [review, setReview] = useState<
    { payload: EmitPayload; plan: string; type: ReportType; format: Fmt; theme: string; author: string; pageNumbers: boolean } | null
  >(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewErr, setReviewErr] = useState<string | null>(null);
  const { exportedPath, exportErr, exportTo, reset } = useReportExport();

  async function handleReviewRequest(type: ReportType, format: Fmt, theme: string, author: string, pageNumbers: boolean) {
    if (!reportFor) return;
    const plan = reportFor;
    setReviewBusy(true);
    setReviewErr(null);
    reset();
    const r = await emitReportModel(projectDir, plan, type, true, author);
    setReviewBusy(false);
    if (r.ok) setReview({ payload: r.payload, plan, type, format, theme, author, pageNumbers });
    else setReviewErr(r.error);
  }

  async function handleReviewConfirm(rejectBlocks: [number, number][]) {
    if (!review) return;
    const { plan, type, format, payload, theme, author, pageNumbers } = review;
    setReview(null);
    setReviewBusy(true);
    setReviewErr(null);
    const r = await renderReportWithDecisions(projectDir, plan, type, format, rejectBlocks, payload.key, theme, author, pageNumbers);
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
      } catch (e) {
        setReviewBusy(false);
        setReviewErr(`PDF 변환 실패: ${String(e)}`);
        return;
      }
    }
    await exportTo(finalPath);
    setReviewBusy(false);
  }

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

  if (plans !== null && plans.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 12,
          color: "#888",
        }}
      >
        <div style={{ fontSize: 32 }}>📄</div>
        <div style={{ fontSize: 14 }}>보고서로 만들 기획안이 아직 없어요.</div>
        <div style={{ fontSize: 12, color: "#666" }}>
          기획방에서 기획안을 먼저 만들면 여기서 보고서로 내보낼 수 있어요.
        </div>
        {onStart && (
          <button className="nav-tab" style={{ marginTop: 4 }} onClick={onStart}>
            기획 시작하기 →
          </button>
        )}
      </div>
    );
  }

  if (review) {
    return (
      <div style={{ height: "100%", overflow: "auto", padding: "16px 20px" }}>
        <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>📝 다듬기 검토</h2>
        <p style={{ fontSize: 13, color: "#666", margin: "0 0 8px" }}>
          AI가 다듬은 문장을 블록마다 확인하고 수락/거부하세요. 숫자가 바뀐 블록은 자동으로 원문이 유지됩니다.
        </p>
        <ReportDiffReview
          payload={review.payload}
          onConfirm={(rb) => void handleReviewConfirm(rb)}
          onCancel={() => setReview(null)}
        />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", overflow: "auto", padding: "16px 20px" }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>📄 보고서 작성</h2>
      <p style={{ fontSize: 13, color: "#666", margin: "0 0 16px" }}>
        저장된 기획안을 업무 보고서(PDF·Word·PPT)로 내보내세요. 보고서 종류와 포맷을 골라 바로 생성합니다.
      </p>
      {reviewBusy && <p style={{ fontSize: 13, color: "#888" }}>다듬기 모델 준비 중…</p>}
      {reviewErr && <p role="alert" style={{ fontSize: 13, color: "#9B1B1B" }}>{reviewErr}</p>}
      {exportErr && <p role="alert" style={{ fontSize: 13, color: "#9B1B1B" }}>{exportErr}</p>}
      {exportedPath && (
        <p style={{ fontSize: 13, color: "#2f6f46" }}>📁 저장 위치: <b style={{ wordBreak: "break-all" }}>{exportedPath}</b></p>
      )}
      {plans === null && <div style={{ fontSize: 13, color: "#888" }}>불러오는 중…</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {plans?.map((plan) => (
          <div
            key={plan.sessionId}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: "1px solid #e5e0d0",
              borderRadius: 8,
              padding: "12px 14px",
              gap: 12,
            }}
          >
            <div style={{ overflow: "hidden" }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{plan.title || "(제목 없음)"}</div>
              <div
                style={{
                  fontSize: 12,
                  color: "#888",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {plan.outputPath ? fileName(plan.outputPath) : ""}
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                if (plan.outputPath) setReportFor(plan.outputPath);
              }}
              style={{
                flexShrink: 0,
                background: "#9B1B1B",
                color: "#fff",
                border: "none",
                padding: "8px 14px",
                borderRadius: 6,
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              📄 보고서 만들기
            </button>
          </div>
        ))}
      </div>

      <ExportReportModal
        open={reportFor !== null}
        planPath={reportFor ?? ""}
        cwd={projectDir}
        onClose={() => setReportFor(null)}
        onReviewRequest={(type, format, theme, author, pageNumbers) => void handleReviewRequest(type, format, theme, author, pageNumbers)}
      />
    </div>
  );
}
// === ANCHOR: REPORT_VIEW_END ===
