import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

vi.mock("../../../lib/vib/report", () => ({ generatePlanningReport: vi.fn() }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openUrl: vi.fn().mockResolvedValue(undefined) }));

import { generatePlanningReport } from "../../../lib/vib/report";
import { openUrl } from "@tauri-apps/plugin-opener";
import { ExportReportModal } from "../ExportReportModal";

const mockGen = vi.mocked(generatePlanningReport);
const mockOpen = vi.mocked(openUrl);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

function renderOpen() {
  return render(
    <ExportReportModal open planPath="plans/p.md" cwd="/proj" onClose={() => {}} />,
  );
}

test("open=false 면 렌더 안 함", () => {
  const { container } = render(
    <ExportReportModal open={false} planPath="plans/p.md" cwd="/proj" onClose={() => {}} />,
  );
  expect(container.firstChild).toBeNull();
});

test("생성 성공 → iframe 미리보기 + 파일 열기", async () => {
  mockGen.mockResolvedValue({
    ok: true,
    path: "/proj/.vibelign/reports/r-work.html",
    reportType: "work",
    html: "<html><body>업무 보고</body></html>",
  });
  renderOpen();

  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  const frame = await screen.findByTitle("보고서 미리보기");
  expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("업무 보고"));
  expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work");

  fireEvent.click(screen.getByRole("button", { name: "파일 열기" }));
  expect(mockOpen).toHaveBeenCalledWith("file:///proj/.vibelign/reports/r-work.html");
});

test("종류 선택이 호출 인자에 반영", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/p/r.html", reportType: "proposal", html: "<i></i>" });
  renderOpen();
  fireEvent.click(screen.getByLabelText("제안서"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "proposal"));
});

test("실패 → 에러 메시지, iframe 없음", async () => {
  mockGen.mockResolvedValue({ ok: false, error: "unknown report type: nope" });
  renderOpen();
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("unknown report type");
  expect(screen.queryByTitle("보고서 미리보기")).toBeNull();
});
