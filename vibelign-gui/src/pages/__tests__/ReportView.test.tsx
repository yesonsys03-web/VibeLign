import { test, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

vi.mock("../../lib/vib", () => ({
  listPlanningChatSessions: vi.fn().mockResolvedValue([
    { sessionId: "s1", title: "예약 앱", outputPath: "plans/예약-앱.md" },
  ]),
}));
vi.mock("../../components/plan-doc/ExportReportModal", () => ({
  ExportReportModal: ({ open, planPath }: { open: boolean; planPath: string }) =>
    open ? <div data-testid="export-modal">{planPath}</div> : null,
}));

import ReportView from "../ReportView";

beforeEach(() => vi.clearAllMocks());
afterEach(() => cleanup());

test("기획안 목록 + 보고서 만들기 버튼 → 모달 오픈", async () => {
  render(<ReportView projectDir="/proj" />);
  const btn = await screen.findByRole("button", { name: /보고서 만들기/ });
  expect(screen.queryByTestId("export-modal")).toBeNull();
  fireEvent.click(btn);
  const modal = await screen.findByTestId("export-modal");
  expect(modal).toHaveTextContent("plans/예약-앱.md");
});

test("기획안 없으면 빈 상태 안내", async () => {
  const mod = await import("../../lib/vib");
  vi.mocked(mod.listPlanningChatSessions).mockResolvedValueOnce([]);
  render(<ReportView projectDir="/proj" />);
  expect(await screen.findByText(/보고서로 만들 기획안이 아직 없어요/)).toBeInTheDocument();
});
