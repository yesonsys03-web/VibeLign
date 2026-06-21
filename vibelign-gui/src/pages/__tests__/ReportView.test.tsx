// === ANCHOR: REPORTVIEW_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { EmitPayload } from "../../lib/vib/reportModel";
import type { ReportAssistPayload } from "../../lib/vib/reportAssist";
import type { ReportQualityPayload } from "../../lib/vib/reportQuality";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
vi.mock("../../components/plan-doc/PdfPreview", () => ({ PdfPreview: () => null }));
vi.mock("../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
vi.mock("../../lib/vib", () => ({
  listPlanningChatSessions: vi.fn(),
}));
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
import {
  emitReportModel,
  generatePlanningReport,
} from "../../lib/vib/report";
import ReportView from "../ReportView";

const mockListPlanningChatSessions = vi.mocked(listPlanningChatSessions);
const mockEmit = vi.mocked(emitReportModel);
const mockGenerateHtml = vi.mocked(generatePlanningReport);

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
  schema_version: "report-quality-v1",
  status: "warn",
  rawStatus: "warn",
  score: 70,
  readiness: "needs_review",
  rawReadiness: "needs_review",
  summary: "근거 보완이 필요합니다.",
  findings: [
    {
      code: "missing_evidence",
      rawCategory: "missing_evidence",
      categoryLabel: "근거 누락",
      severity: "warn",
      rawSeverity: "warn",
      message: "정량 근거가 부족합니다.",
      source: "report_model",
      rawSource: "report_model",
      blocking: false,
    },
  ],
};

function emitPayload(quality: ReportQualityPayload, sourcePath: string): EmitPayload {
  const section = {
    heading: "요약",
    blocks: [{ kind: "paragraph", text: "예약 앱 보고서 본문", items: [] }],
  };
  return {
    ok: true,
    report_type: "work",
    slug: "reservation-app",
    key: "polish-key",
    base: {
      title: "예약 앱",
      report_type: "work",
      date: "2026-06-20",
      source_plan_path: sourcePath,
      sections: [section],
    },
    polished: {
      title: "예약 앱",
      report_type: "work",
      date: "2026-06-20",
      source_plan_path: sourcePath,
      sections: [section],
    },
    guards: [],
    vague_warnings: [],
    quality,
    assistance: notRequestedAssistance,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListPlanningChatSessions.mockResolvedValue([
    { sessionId: "complete", title: "완성 보고서", outputPath: "tests/fixtures/reporting_cli/quality_complete.md" },
    { sessionId: "sparse", title: "보완 필요 보고서", outputPath: "tests/fixtures/reporting_cli/quality_sparse.md" },
    { sessionId: "long", title: "긴 보고서", outputPath: "tests/fixtures/reporting_cli/quality_long_2000.md" },
  ]);
  mockEmit.mockImplementation((_cwd, planPath) => Promise.resolve({ ok: true, payload: emitPayload(readyQuality, planPath) }));
  mockGenerateHtml.mockResolvedValue({
    ok: true,
    path: "/proj/.vibelign/reports/report.html",
    reportType: "work",
    html: "<html><body>보고서 미리보기 본문</body></html>",
  });
});

afterEach(cleanup);

test("기획안 목록 + 보고서 만들기 버튼이 real inline ReportComposer를 연다", async () => {
  render(<ReportView projectDir="/proj" />);

  const buttons = await screen.findAllByRole("button", { name: /보고서 만들기/ });
  const firstButton = buttons[0];
  if (firstButton === undefined) throw new Error("보고서 만들기 버튼을 찾지 못했습니다.");
  fireEvent.click(firstButton);

  expect(await screen.findByRole("button", { name: "보고서 생성" })).toBeInTheDocument();
});

test("기획안 없으면 빈 상태 안내", async () => {
  mockListPlanningChatSessions.mockResolvedValueOnce([]);
  render(<ReportView projectDir="/proj" />);

  expect(await screen.findByText(/보고서로 만들 기획안이 아직 없어요/)).toBeInTheDocument();
});

test("quality_complete sourcePath opens ReportComposer and generates preview", async () => {
  const onSourceHandled = vi.fn();
  render(
    <ReportView
      projectDir="/proj"
      sourcePath="tests/fixtures/reporting_cli/quality_complete.md"
      onSourceHandled={onSourceHandled}
    />,
  );

  expect(await screen.findByRole("button", { name: "보고서 생성" })).toBeInTheDocument();
  await waitFor(() => expect(onSourceHandled).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByTitle("보고서 미리보기")).toBeInTheDocument();
  expect(mockGenerateHtml).toHaveBeenCalledWith(
    "/proj",
    "tests/fixtures/reporting_cli/quality_complete.md",
    "doc",
    false,
    "classic",
    "",
    true,
    {},
    {},
  );
});

test("카드뉴스 companion은 보고서 작성 오른쪽 작업 영역 탭에서 열린다", async () => {
  render(<ReportView projectDir="/proj" sourcePath="tests/fixtures/reporting_cli/quality_complete.md" />);

  expect(await screen.findByRole("button", { name: "보고서 생성" })).toBeInTheDocument();
  expect(screen.queryByText("카드뉴스 출력")).toBeNull();

  fireEvent.click(screen.getByRole("tab", { name: "카드뉴스" }));

  expect(await screen.findByText("카드뉴스 출력")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "카드뉴스 초안 만들기" })).toBeInTheDocument();
});

test("quality panel warning blocks preview until generate-anyway", async () => {
  mockEmit.mockResolvedValueOnce({
    ok: true,
    payload: emitPayload(warningQuality, "tests/fixtures/reporting_cli/quality_sparse.md"),
  });
  render(<ReportView projectDir="/proj" sourcePath="tests/fixtures/reporting_cli/quality_sparse.md" />);

  fireEvent.click(await screen.findByRole("button", { name: "보고서 생성" }));

  expect(await screen.findByText("검토 필요")).toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "보고서 품질 점검 확대 보기" })).toBeInTheDocument();
  expect(screen.queryByTitle("보고서 미리보기")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "그래도 생성" }));
  expect(await screen.findByTitle("보고서 미리보기")).toBeInTheDocument();
});

// === ANCHOR: REPORTVIEW_TEST_END ===
