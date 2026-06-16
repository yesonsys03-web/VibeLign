import { describe, test, expect, vi, beforeEach } from "vitest";

vi.mock("../core", () => ({ runVib: vi.fn() }));
vi.mock("../../docs", () => ({ loadDoc: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

import { runVib } from "../core";
import { loadDoc } from "../../docs";
import { invoke } from "@tauri-apps/api/core";
import { generatePlanningReport, generateReportPdf, toProjectRelative } from "../report";

const mockRunVib = vi.mocked(runVib);
const mockLoadDoc = vi.mocked(loadDoc);
const mockInvoke = vi.mocked(invoke);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("toProjectRelative", () => {
  test("cwd 접두사를 벗겨 상대경로로", () => {
    expect(toProjectRelative("/proj", "/proj/.vibelign/reports/r-work.html")).toBe(
      ".vibelign/reports/r-work.html",
    );
  });
  test("루트 밖 경로는 그대로", () => {
    expect(toProjectRelative("/proj", "/other/r.html")).toBe("/other/r.html");
  });
});

describe("generatePlanningReport", () => {
  test("성공 시 path/reportType/html 반환", async () => {
    mockRunVib.mockResolvedValue({
      ok: true,
      stdout: JSON.stringify({
        ok: true,
        path: "/proj/.vibelign/reports/r-work.html",
        report_type: "work",
      }),
      stderr: "",
      exit_code: 0,
    });
    mockLoadDoc.mockResolvedValue({
      path: ".vibelign/reports/r-work.html",
      content: "<html>RP</html>",
    } as never);

    const res = await generatePlanningReport("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.path).toContain("r-work.html");
      expect(res.reportType).toBe("work");
      expect(res.html).toContain("RP");
    }
    expect(mockRunVib).toHaveBeenCalledWith(
      ["report", "plans/p.md", "--type", "work", "--format", "html", "--json"],
      "/proj",
    );
    expect(mockLoadDoc).toHaveBeenCalledWith("/proj", ".vibelign/reports/r-work.html");
  });

  test("ok:false JSON → 에러, 파일 안 읽음", async () => {
    mockRunVib.mockResolvedValue({
      ok: false,
      stdout: JSON.stringify({ ok: false, error: "unknown report type: nope" }),
      stderr: "",
      exit_code: 1,
    });

    const res = await generatePlanningReport("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toContain("unknown report type");
    expect(mockLoadDoc).not.toHaveBeenCalled();
  });

  test("비-JSON crash → stderr 폴백", async () => {
    mockRunVib.mockResolvedValue({
      ok: false,
      stdout: "",
      stderr: "Traceback (most recent call last): ...",
      exit_code: 1,
    });

    const res = await generatePlanningReport("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toContain("Traceback");
  });
});

test("loadDoc 실패 시 {ok:false} 반환 (모달 멈춤 방지)", async () => {
  mockRunVib.mockResolvedValue({
    ok: true,
    stdout: JSON.stringify({
      ok: true,
      path: "/proj/.vibelign/reports/r-work.html",
      report_type: "work",
    }),
    stderr: "",
    exit_code: 0,
  });
  mockLoadDoc.mockRejectedValue(new Error("EACCES"));

  const res = await generatePlanningReport("/proj", "plans/p.md", "work");

  expect(res.ok).toBe(false);
  if (!res.ok) expect(res.error).toContain("읽지 못");
});

describe("generateReportPdf", () => {
  function setupHtmlSuccess() {
    mockRunVib.mockResolvedValue({
      ok: true,
      stdout: JSON.stringify({
        ok: true,
        path: "/proj/.vibelign/reports/r-work.html",
        report_type: "work",
      }),
      stderr: "",
      exit_code: 0,
    });
    mockLoadDoc.mockResolvedValue({
      path: ".vibelign/reports/r-work.html",
      content: "<html>RP</html>",
    } as never);
  }

  test("성공 시 {ok:true, path} 반환하고 invoke 를 올바른 인자로 호출", async () => {
    setupHtmlSuccess();
    mockInvoke.mockResolvedValue("/proj/.vibelign/reports/r-work.pdf");

    const res = await generateReportPdf("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(true);
    if (res.ok) expect(res.path).toBe("/proj/.vibelign/reports/r-work.pdf");
    expect(mockInvoke).toHaveBeenCalledWith("export_report_pdf", {
      htmlPath: "/proj/.vibelign/reports/r-work.html",
      outPdf: "/proj/.vibelign/reports/r-work.pdf",
    });
  });

  test("HTML 생성 실패 시 {ok:false} 전파하고 invoke 미호출", async () => {
    mockRunVib.mockResolvedValue({
      ok: false,
      stdout: JSON.stringify({ ok: false, error: "보고서 생성 오류" }),
      stderr: "",
      exit_code: 1,
    });

    const res = await generateReportPdf("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toContain("보고서 생성 오류");
    expect(mockInvoke).not.toHaveBeenCalled();
  });

  test("invoke 실패 시 {ok:false, error contains 'PDF'}", async () => {
    setupHtmlSuccess();
    mockInvoke.mockRejectedValue(new Error("Chromium not found"));

    const res = await generateReportPdf("/proj", "plans/p.md", "work");

    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.error).toContain("PDF");
      expect(res.error).toContain("Chromium not found");
    }
  });
});
