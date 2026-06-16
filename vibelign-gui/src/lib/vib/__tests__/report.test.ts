import { describe, test, expect, vi, beforeEach } from "vitest";

vi.mock("../core", () => ({ runVib: vi.fn() }));
vi.mock("../../docs", () => ({ loadDoc: vi.fn() }));

import { runVib } from "../core";
import { loadDoc } from "../../docs";
import { generatePlanningReport, toProjectRelative } from "../report";

const mockRunVib = vi.mocked(runVib);
const mockLoadDoc = vi.mocked(loadDoc);

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
