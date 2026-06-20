// === ANCHOR: REPORTVIEW_POLISH_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { ReportAssistPayload } from "../../lib/vib/reportAssist";
import type { ReportQualityPayload } from "../../lib/vib/reportQuality";
import type { EmitPayload } from "../../lib/vib/reportModel";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
vi.mock("../../components/plan-doc/PdfPreview", () => ({ PdfPreview: () => null }));
vi.mock("../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
vi.mock("../../lib/vib", () => ({ listPlanningChatSessions: vi.fn() }));
vi.mock("../../lib/vib/report", () => ({
  emitReportModel: vi.fn(),
  requestReportAssistance: vi.fn(),
  generatePlanningReport: vi.fn(),
  generateReportPdf: vi.fn(),
  generateReportOffice: vi.fn(),
  renderReportHtmlWithDecisions: vi.fn(),
  renderReportWithDecisions: vi.fn(),
  stampPdfPageNumbers: vi.fn(),
  getReportExportDir: vi.fn().mockResolvedValue("/docs"),
  setReportExportDir: vi.fn().mockResolvedValue(undefined),
  copyReportTo: vi.fn((src: string, dir: string) => Promise.resolve(`${dir}/${src.split("/").pop()}`)),
}));

import { listPlanningChatSessions } from "../../lib/vib";
import { emitReportModel, renderReportWithDecisions, requestReportAssistance } from "../../lib/vib/report";
import ReportView from "../ReportView";

const mockListPlanningChatSessions = vi.mocked(listPlanningChatSessions);
const mockEmit = vi.mocked(emitReportModel);
const mockRenderWithDecisions = vi.mocked(renderReportWithDecisions);
const mockRequestAssistance = vi.mocked(requestReportAssistance);

const notRequestedAssistance: ReportAssistPayload = {
  schema_version: "report-assist-v1",
  status: "not_requested",
  rawStatus: "not_requested",
  suggestions: [],
  questions: [],
  applied_suggestion_ids: [],
};

const readyQuality: ReportQualityPayload = {
  schema_version: "report-quality-v1",
  status: "ok",
  rawStatus: "ok",
  score: 98,
  readiness: "ready",
  rawReadiness: "ready",
  summary: "업무 보고서 기준을 충족합니다.",
  findings: [],
};

const warningQuality: ReportQualityPayload = {
  ...readyQuality,
  status: "warn",
  rawStatus: "warn",
  score: 70,
  readiness: "needs_review",
  rawReadiness: "needs_review",
  summary: "근거 보완이 필요합니다.",
  findings: [{
    code: "missing_evidence",
    rawCategory: "missing_evidence",
    categoryLabel: "근거 누락",
    severity: "warn",
    rawSeverity: "warn",
    message: "정량 근거가 부족합니다.",
    source: "report_model",
    rawSource: "report_model",
    blocking: false,
  }],
};

function emitPayload(quality: ReportQualityPayload, sourcePath: string): EmitPayload {
  const section = { heading: "요약", blocks: [{ kind: "paragraph", text: "예약 앱 보고서 본문", items: [] }] };
  return {
    ok: true,
    report_type: "work",
    slug: "reservation-app",
    key: "polish-key",
    base: { title: "예약 앱", report_type: "work", date: "2026-06-20", source_plan_path: sourcePath, sections: [section] },
    polished: { title: "예약 앱", report_type: "work", date: "2026-06-20", source_plan_path: sourcePath, sections: [section] },
    guards: [],
    vague_warnings: [],
    quality,
    assistance: notRequestedAssistance,
  };
}

const assistance = {
  schema_version: "report-assist-v1",
  status: "needs_user_input",
  rawStatus: "needs_user_input",
  suggestions: [
    {
      id: "evidence-1",
      finding_code: "missing_evidence",
      kind: "source_candidate",
      rawKind: "source_candidate",
      kindLabel: "원문 근거 후보",
      title: "성과 근거 추가",
      proposed_text: "중간 검증에서 이탈률이 18% 감소했습니다.",
      rationale: "긴 문서 중간 섹션의 근거입니다.",
      source_refs: [{ chunk_id: "chunk-12", heading_path: ["중간 검증"], start_line: 1220, end_line: 1250 }],
      requires_user_confirmation: true,
    },
    {
      id: "risk-1",
      finding_code: "missing_risk",
      kind: "risk_candidate",
      rawKind: "risk_candidate",
      kindLabel: "리스크 후보",
      title: "일정 리스크",
      proposed_text: "검수 지연 시 출시 일정이 밀릴 수 있습니다.",
      rationale: "리스크 메모입니다.",
      source_refs: [],
      requires_user_confirmation: true,
    },
  ],
  questions: [],
  applied_suggestion_ids: [],
} satisfies ReportAssistPayload;

beforeEach(() => {
  vi.clearAllMocks();
  mockListPlanningChatSessions.mockResolvedValue([
    { sessionId: "complete", title: "완성 보고서", outputPath: "tests/fixtures/reporting_cli/quality_complete.md" },
    { sessionId: "sparse", title: "보완 필요 보고서", outputPath: "tests/fixtures/reporting_cli/quality_sparse.md" },
  ]);
  mockEmit.mockImplementation((_cwd, planPath) => Promise.resolve({ ok: true, payload: emitPayload(readyQuality, planPath) }));
  mockRenderWithDecisions.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/report.html" });
  mockRequestAssistance.mockResolvedValue({ ok: true, payload: { ok: true, report_type: "work", quality: warningQuality, assistance } });
});

afterEach(cleanup);

test("polish review handoff still opens ReportDiffReview after quality pass", async () => {
  render(<ReportView projectDir="/proj" sourcePath="tests/fixtures/reporting_cli/quality_complete.md" />);

  fireEvent.click(await screen.findByLabelText("AI 어조 다듬기 (무료)"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByText(/다듬기 검토/)).toBeInTheDocument();
  expect(mockEmit).toHaveBeenCalledWith("/proj", "tests/fixtures/reporting_cli/quality_complete.md", "doc", true, "");
});

test("polish warning assistance draft survives into review render path", async () => {
  mockEmit
    .mockResolvedValueOnce({ ok: true, payload: emitPayload(warningQuality, "tests/fixtures/reporting_cli/quality_sparse.md") })
    .mockResolvedValueOnce({ ok: true, payload: emitPayload(readyQuality, "tests/fixtures/reporting_cli/quality_sparse.md") })
    .mockResolvedValueOnce({ ok: true, payload: emitPayload(readyQuality, "tests/fixtures/reporting_cli/quality_sparse.md") });
  render(<ReportView projectDir="/proj" sourcePath="tests/fixtures/reporting_cli/quality_sparse.md" />);

  fireEvent.click(await screen.findByLabelText("AI 어조 다듬기 (무료)"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  fireEvent.click(await screen.findByRole("button", { name: "AI 보완 제안 요청" }));
  fireEvent.click(await screen.findByRole("button", { name: "성과 근거 추가 수락" }));
  fireEvent.change(screen.getByLabelText("일정 리스크 편집"), {
    target: { value: "검수 지연 시 출시 일정을 재조정합니다." },
  });
  fireEvent.click(screen.getByRole("button", { name: "일정 리스크 수정 반영" }));
  fireEvent.click(screen.getByRole("button", { name: "그래도 생성" }));

  expect(await screen.findByText(/다듬기 검토/)).toBeInTheDocument();
  expect(screen.getByText("사용자 확인 보완 초안")).toBeInTheDocument();
  expect(screen.getAllByText((text) => text.includes("중간 검증에서 이탈률이 18% 감소했습니다.")).length).toBeGreaterThan(0);
  expect(screen.getAllByText((text) => text.includes("검수 지연 시 출시 일정을 재조정합니다.")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "저장 / 내보내기" }));
  await waitFor(() => expect(mockRenderWithDecisions).toHaveBeenCalled());
  expect(mockRenderWithDecisions).toHaveBeenCalledWith(expect.objectContaining({
    cwd: "/proj",
    planPath: "tests/fixtures/reporting_cli/quality_sparse.md",
    reportType: "doc",
    format: "html",
    payload: expect.objectContaining({
      base: expect.objectContaining({ sections: expect.arrayContaining([expect.objectContaining({ heading: "사용자 확인 보완 초안" })]) }),
      polished: expect.objectContaining({ sections: expect.arrayContaining([expect.objectContaining({ heading: "사용자 확인 보완 초안" })]) }),
    }),
  }));
});
// === ANCHOR: REPORTVIEW_POLISH_TEST_END ===
