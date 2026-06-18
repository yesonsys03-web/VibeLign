// === ANCHOR: EXPORTREPORTMODAL_TEST_START ===
import { test, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

vi.mock("../../../lib/vib/report", () => ({
  generatePlanningReport: vi.fn(),
  generateReportPdf: vi.fn(),
  generateReportOffice: vi.fn(),
  // 생성 전 빈-보고서 점검용 프로브. ok:false 면 가드를 건너뛰어 기존 동작 유지.
  emitReportModel: vi.fn().mockResolvedValue({ ok: false, error: "" }),
  getReportExportDir: vi.fn().mockResolvedValue("/docs"),
  setReportExportDir: vi.fn().mockResolvedValue(undefined),
  copyReportTo: vi.fn((src: string, dir: string) => Promise.resolve(`${dir}/${src.split("/").pop()}`)),
}));
vi.mock("../../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
// PdfPreview 는 pdf.js 를 동적 import 하므로 jsdom 단위테스트에선 스텁으로 대체한다.
vi.mock("../PdfPreview", () => ({ PdfPreview: () => null }));

import {
  generatePlanningReport,
  generateReportPdf,
  generateReportOffice,
} from "../../../lib/vib/report";
import { openPath } from "@tauri-apps/plugin-opener";
import { ExportReportModal } from "../ExportReportModal";

const mockGen = vi.mocked(generatePlanningReport);
const mockGenPdf = vi.mocked(generateReportPdf);
const mockGenOffice = vi.mocked(generateReportOffice);
const mockOpen = vi.mocked(openPath);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

// === ANCHOR: EXPORTREPORTMODAL_TEST_RENDEROPEN_START ===
function renderOpen() {
  return render(
    <ExportReportModal open planPath="plans/p.md" cwd="/proj" onClose={() => {}} />,
  );
}
// === ANCHOR: EXPORTREPORTMODAL_TEST_RENDEROPEN_END ===

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
  expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "", true, {});

  // 생성 후 기본 폴더(/docs)로 자동 복사된 위치가 표시되고, 파일 열기는 그 위치를 연다.
  await screen.findByText("/docs/r-work.html");
  fireEvent.click(screen.getByRole("button", { name: "파일 열기" }));
  expect(mockOpen).toHaveBeenCalledWith("/docs/r-work.html");
});

test("종류 선택이 호출 인자에 반영", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/p/r.html", reportType: "proposal", html: "<i></i>" });
  renderOpen();
  fireEvent.click(screen.getByLabelText("제안서"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "proposal", false, "classic", "", true, {}));
});

test("실패 → 에러 메시지, iframe 없음", async () => {
  mockGen.mockResolvedValue({ ok: false, error: "unknown report type: nope" });
  renderOpen();
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("unknown report type");
  expect(screen.queryByTitle("보고서 미리보기")).toBeNull();
});

test("PDF 포맷 선택 → generateReportPdf 호출, 저장됨 표시, iframe 없음", async () => {
  mockGenPdf.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r-work.pdf" });
  renderOpen();

  fireEvent.click(screen.getByLabelText("PDF 파일"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  await waitFor(() => expect(mockGenPdf).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "", true, {}));
  expect(mockGen).not.toHaveBeenCalled();

  expect(await screen.findByText(/내부 사본.*r-work\.pdf/)).toBeInTheDocument();
  expect(screen.queryByTitle("보고서 미리보기")).toBeNull();

  await screen.findByText("/docs/r-work.pdf");
  fireEvent.click(screen.getByRole("button", { name: "파일 열기" }));
  expect(mockOpen).toHaveBeenCalledWith("/docs/r-work.pdf");
});

test("HTML 포맷(기본) → generatePlanningReport 호출, iframe 표시", async () => {
  mockGen.mockResolvedValue({
    ok: true,
    path: "/proj/.vibelign/reports/r-work.html",
    reportType: "work",
    html: "<html><body>HTML 보고</body></html>",
  });
  renderOpen();

  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));

  await screen.findByTitle("보고서 미리보기");
  expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "", true, {});
  expect(mockGenPdf).not.toHaveBeenCalled();
  expect(screen.queryByTitle("보고서 미리보기")).toBeInTheDocument();
});

test("Word 포맷 선택 → generateReportOffice(docx) 호출, 저장됨 표시", async () => {
  mockGenOffice.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r-work.docx" });
  renderOpen();
  fireEvent.click(screen.getByLabelText("Word 파일"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() =>
    expect(mockGenOffice).toHaveBeenCalledWith("/proj", "plans/p.md", "work", "docx", false, "classic", "", true, {}),
  );
  expect(await screen.findByText(/내부 사본.*r-work\.docx/)).toBeInTheDocument();
  expect(screen.queryByTitle("보고서 미리보기")).toBeNull();
});

test("AI 다듬기 토글 → polish=true 로 전달", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/p/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.click(screen.getByLabelText("AI 어조 다듬기 (무료)"));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", true, "classic", "", true, {}));
});

test("테마 선택 → generatePlanningReport 에 theme 전달", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.change(screen.getByLabelText("디자인 테마"), { target: { value: "board-indigo-balanced" } });
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "board-indigo-balanced", "", true, {}));
});

test("폰트 크기 조절 → generatePlanningReport 에 fontSizes 전달", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.change(screen.getByLabelText("타이틀 폰트 크기"), { target: { value: "32" } });
  fireEvent.change(screen.getByLabelText("헤드라인 폰트 크기"), { target: { value: "19" } });
  fireEvent.change(screen.getByLabelText("본문 폰트 크기"), { target: { value: "15" } });
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() =>
    expect(mockGen).toHaveBeenCalledWith(
      "/proj",
      "plans/p.md",
      "work",
      false,
      "classic",
      "",
      true,
      { title: 32, heading: 19, body: 15 },
    ),
  );
});

test("폰트 크기 키보드 입력은 입력 중에 최소값으로 보정하지 않음", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  const titleSizeInput = screen.getByLabelText("타이틀 폰트 크기");
  fireEvent.change(titleSizeInput, { target: { value: "3" } });
  expect(titleSizeInput).toHaveValue(3);
  fireEvent.change(titleSizeInput, { target: { value: "32" } });
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() =>
    expect(mockGen).toHaveBeenCalledWith(
      "/proj",
      "plans/p.md",
      "work",
      false,
      "classic",
      "",
      true,
      { title: 32 },
    ),
  );
});

test("디자인 테마는 100개 이상 제공", () => {
  renderOpen();
  expect(screen.getAllByRole("option").length).toBeGreaterThanOrEqual(100);
  expect(screen.getByRole("option", { name: "임원형 · 인디고 · 표준" })).toBeInTheDocument();
});

test("작성자 입력/페이지번호 → generatePlanningReport 인자", async () => {
  mockGen.mockResolvedValue({ ok: true, path: "/proj/.vibelign/reports/r.html", reportType: "work", html: "<i></i>" });
  renderOpen();
  fireEvent.change(screen.getByLabelText("작성자"), { target: { value: "홍길동" } });
  fireEvent.click(screen.getByLabelText(/페이지 번호/));
  fireEvent.click(screen.getByRole("button", { name: "보고서 생성" }));
  await waitFor(() => expect(mockGen).toHaveBeenCalledWith("/proj", "plans/p.md", "work", false, "classic", "홍길동", false, {}));
});
// === ANCHOR: EXPORTREPORTMODAL_TEST_END ===
