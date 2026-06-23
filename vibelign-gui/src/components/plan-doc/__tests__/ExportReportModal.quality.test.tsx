// === ANCHOR: EXPORTREPORTMODAL_QUALITY_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { ReportAssistPayload } from "../../../lib/vib/reportAssist";
import type { ReportQualityPayload } from "../../../lib/vib/reportQuality";
import type { EmitPayload } from "../../../lib/vib/reportModel";

vi.mock("../../../lib/vib/report", () => ({
  generatePlanningReport: vi.fn(),
  generateReportPdf: vi.fn(),
  generateReportOffice: vi.fn(),
  renderReportFileWithDecisions: vi.fn(),
  renderReportHtmlWithDecisions: vi.fn(),
  emitReportModel: vi.fn(),
  requestReportAssistance: vi.fn(),
  getReportExportDir: vi.fn().mockResolvedValue("/docs"),
  setReportExportDir: vi.fn().mockResolvedValue(undefined),
  copyReportTo: vi.fn((src: string, dir: string) => Promise.resolve(`${dir}/${src.split("/").pop()}`)),
}));
vi.mock("../../../lib/vib/planning-personas", () => ({
  probePlanningProviders: vi.fn().mockResolvedValue(["codex"]),
}));
vi.mock("../../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
vi.mock("../PdfPreview", () => ({ PdfPreview: () => null }));

import {
  emitReportModel,
  generatePlanningReport,
  generateReportOffice,
  renderReportFileWithDecisions,
  renderReportHtmlWithDecisions,
  requestReportAssistance,
} from "../../../lib/vib/report";
import { ExportReportModal } from "../ExportReportModal";

const mockEmit = vi.mocked(emitReportModel);
const mockGen = vi.mocked(generatePlanningReport);
const mockGenOffice = vi.mocked(generateReportOffice);
const mockRenderFileWithDecisions = vi.mocked(renderReportFileWithDecisions);
const mockRenderHtmlWithDecisions = vi.mocked(renderReportHtmlWithDecisions);
const mockRequestAssistance = vi.mocked(requestReportAssistance);

const notRequestedAssistance: ReportAssistPayload = {
  schema_version: "report-assist-v1",
  status: "not_requested",
  rawStatus: "not_requested",
  suggestions: [],
  questions: [],
  applied_suggestion_ids: [],
};

const warningQuality: ReportQualityPayload = {
  schema_version: "report-quality-v1",
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
    suggestion: "성과 수치를 추가하세요.",
  }],
};

const blockingQuality: ReportQualityPayload = {
  ...warningQuality,
  status: "block",
  rawStatus: "block",
  score: 0,
  readiness: "blocked",
  rawReadiness: "blocked",
  summary: "보고서로 만들 내용이 없습니다.",
  findings: [{ ...warningQuality.findings[0], severity: "block", rawSeverity: "block", blocking: true }],
};

function emitPayload(quality: ReportQualityPayload): EmitPayload {
  return {
    ok: true,
    report_type: "work",
    slug: "report",
    key: "polish-key",
    base: {
      title: "예약 앱",
      report_type: "work",
      date: "2026-06-20",
      source_plan_path: "plans/p.md",
      sections: [{ heading: "요약", blocks: [{ kind: "paragraph", text: "본문", items: [] }] }],
    },
    polished: {
      title: "예약 앱",
      report_type: "work",
      date: "2026-06-20",
      source_plan_path: "plans/p.md",
      sections: [],
    },
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
      proposed_text: "파일럿 검증에서 재확인 건수가 31% 줄었습니다.",
      rationale: "중간 검증 섹션의 수치 근거입니다.",
      source_refs: [{ chunk_id: "chunk-7", heading_path: ["검증"], start_line: 842, end_line: 870 }],
      requires_user_confirmation: true,
    },
    {
      id: "risk-1",
      finding_code: "missing_risk",
      kind: "risk_candidate",
      rawKind: "risk_candidate",
      kindLabel: "리스크 후보",
      title: "일정 리스크",
      proposed_text: "운영팀 확인이 늦어지면 배포 일정이 밀릴 수 있습니다.",
      rationale: "리스크 메모 기반 후보입니다.",
      source_refs: [],
      requires_user_confirmation: true,
    },
  ],
  questions: [{
    id: "question-1",
    finding_code: "missing_owner",
    kind: "user_question",
    rawKind: "user_question",
    kindLabel: "사용자 확인 질문",
    title: "담당자 확인",
    proposed_text: "담당자는 누구인가요?",
    rationale: "담당자 보완 질문입니다.",
    source_refs: [],
    requires_user_confirmation: true,
  }],
  applied_suggestion_ids: [],
} satisfies ReportAssistPayload;

beforeEach(() => {
  vi.clearAllMocks();
  mockEmit.mockResolvedValue({ ok: true, payload: emitPayload(warningQuality) });
  mockRequestAssistance.mockResolvedValue({ ok: true, payload: { ok: true, report_type: "work", quality: warningQuality, assistance } });
  mockRenderFileWithDecisions.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r-work-draft.pdf" });
  mockRenderHtmlWithDecisions.mockResolvedValue({
    ok: true,
    path: "/proj/.vibelign/reports/r-work-draft.html",
    reportType: "work",
    html: "<html><body>파일럿 검증에서 재확인 건수가 31% 줄었습니다.</body></html>",
  });
});

afterEach(cleanup);

function renderOpen(onReviewRequest = vi.fn()) {
  return render(<ExportReportModal open planPath="plans/p.md" cwd="/proj" onClose={() => {}} onReviewRequest={onReviewRequest} />);
}

test("warning preflight pauses generation until generate-anyway", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r-work.html", reportType: "work", html: "<html><body>업무 보고</body></html>" });
  renderOpen();

  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByText("검토 필요")).toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "보고서 품질 점검 확대 보기" })).toBeInTheDocument();
  expect(mockGen).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "그래도 생성" }));

  await screen.findByTitle("보고서 미리보기");
  expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "", true, {}, {});
});

test("generate-anyway resumes original export options", async () => {
  mockGenOffice.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r-work.docx" });
  renderOpen();

  fireEvent.click(screen.getByLabelText("Word 파일"));
  fireEvent.change(screen.getByLabelText("디자인 테마"), { target: { value: "board-indigo-balanced" } });
  fireEvent.change(screen.getByLabelText("작성자"), { target: { value: "팀장" } });
  fireEvent.change(screen.getByLabelText("본문 폰트 크기"), { target: { value: "15" } });
  fireEvent.click(screen.getByLabelText(/페이지 번호/));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  expect(await screen.findByRole("dialog", { name: "보고서 품질 점검 확대 보기" })).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "그래도 생성" }));

  await waitFor(() =>
    expect(mockGenOffice).toHaveBeenCalledWith("/proj", "plans/p.md", "work", "docx", false, "board-indigo-balanced", "팀장", false, { body: 15 }, {}),
  );
});

test("block preflight prevents render", async () => {
  mockEmit.mockResolvedValueOnce({ ok: true, payload: emitPayload(blockingQuality) });
  renderOpen();

  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByText("생성 중단")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "생성 불가" })).toBeDisabled();
  expect(mockGen).not.toHaveBeenCalled();
  expect(mockGenOffice).not.toHaveBeenCalled();
});

test("AI assistance request only runs after explicit user action", async () => {
  renderOpen();

  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByText("AI 보완 도움")).toBeInTheDocument();
  expect(mockRequestAssistance).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.getByLabelText("AI 보완 모델")).toHaveValue("codex"));
  fireEvent.click(screen.getByRole("button", { name: "AI 보완 제안 요청" }));

  expect(await screen.findByText("성과 근거 추가")).toBeInTheDocument();
  expect(mockRequestAssistance).toHaveBeenCalledWith(
    { cwd: "/proj", planPath: "plans/p.md", reportType: "work", author: "", assistProvider: "codex" },
    expect.any(Function),
  );
  expect(screen.getByText(/전체 870줄을 한 번에 보내지 않습니다/)).toBeInTheDocument();
});

test("accepted PDF assistance uses render payload while rejected and unanswered items are omitted", async () => {
  renderOpen();

  fireEvent.click(screen.getByLabelText("PDF 파일"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  fireEvent.click(await screen.findByRole("button", { name: "AI 보완 제안 요청" }));
  fireEvent.click(await screen.findByRole("button", { name: "성과 근거 추가 수락" }));
  fireEvent.click(screen.getByRole("button", { name: "일정 리스크 제외" }));
  fireEvent.click(screen.getByRole("button", { name: "생성 계속" }));

  await waitFor(() => expect(mockRenderFileWithDecisions).toHaveBeenCalled());
  const request = mockRenderFileWithDecisions.mock.calls[0][0];
  expect(request).toEqual(expect.objectContaining({
    cwd: "/proj",
    planPath: "plans/p.md",
    reportType: "work",
    format: "pdf",
    theme: "classic",
    author: "",
    pageNumbers: true,
    fontSizes: {},
    fonts: {},
  }));
  expect(JSON.stringify(request.payload)).toContain("파일럿 검증에서 재확인 건수가 31% 줄었습니다.");
  expect(JSON.stringify(request.payload)).not.toContain("운영팀 확인이 늦어지면");
  expect(JSON.stringify(request.payload)).not.toContain("담당자는 누구인가요?");
  await screen.findByText("/docs/r-work-draft.pdf");
});

test("polish still routes to review after quality proceed with accepted assistance", async () => {
  const onReviewRequest = vi.fn();
  renderOpen(onReviewRequest);

  fireEvent.click(screen.getByLabelText("AI 어조 다듬기 (무료)"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  fireEvent.click(await screen.findByRole("button", { name: "AI 보완 제안 요청" }));
  fireEvent.click(await screen.findByRole("button", { name: "성과 근거 추가 수락" }));
  fireEvent.click(screen.getByRole("button", { name: "생성 계속" }));

  await waitFor(() => expect(onReviewRequest).toHaveBeenCalled());
  expect(onReviewRequest.mock.calls[0][0]).toEqual(expect.objectContaining({
    reportType: "work",
    format: "html",
    draft: { entries: [{ id: "evidence-1", text: "파일럿 검증에서 재확인 건수가 31% 줄었습니다.", source: "suggestion" }] },
  }));
});
// === ANCHOR: EXPORTREPORTMODAL_QUALITY_TEST_END ===
