// === ANCHOR: PLANDOCVIEW_REPORT_TEST_START ===
import { describe, test, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

// Mock all barrel exports PlanDocView imports from "../../lib/vib"
vi.mock("../../lib/vib", () => ({
  listPlanningChatSessions: vi.fn().mockResolvedValue([
    { sessionId: "s1", title: "예약 앱", outputPath: "plans/예약-앱.md", docStale: false },
  ]),
  listTrashedPlanningSessions: vi.fn().mockResolvedValue([]),
  deletePlanningChatSession: vi.fn(),
  restorePlanningChatSession: vi.fn(),
  emptyPlanningTrash: vi.fn(),
}));

vi.mock("../../lib/docs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/docs")>();
  return {
    ...actual,
    loadDoc: vi.fn().mockResolvedValue({ path: "plans/예약-앱.md", content: "# 예약 앱" }),
  };
});

vi.mock("../../components/plan-doc/ExportReportModal", () => ({
  ExportReportModal: ({ open, planPath }: { open: boolean; planPath: string }) =>
    open ? <div data-testid="export-modal">{planPath}</div> : null,
}));

import PlanDocView from "../PlanDocView";

afterEach(cleanup);

describe("PlanDocView — 보고서 내보내기 버튼", () => {
  test("내보내기 버튼 클릭 → 모달 열림(해당 기획안 경로 전달)", async () => {
    render(<PlanDocView projectDir="/proj" />);

    const btn = await screen.findByRole("button", { name: /보고서로 내보내기/ });
    expect(screen.queryByTestId("export-modal")).toBeNull();

    fireEvent.click(btn);

    const modal = await screen.findByTestId("export-modal");
    expect(modal.textContent).toBe("plans/예약-앱.md");
  });
});
// === ANCHOR: PLANDOCVIEW_REPORT_TEST_END ===
