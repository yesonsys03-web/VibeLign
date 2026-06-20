// === ANCHOR: REPORT_RENDER_PAYLOAD_TEST_START ===
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../core", () => ({ runVib: vi.fn() }));
vi.mock("../../docs", () => ({ loadDoc: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

import { invoke } from "@tauri-apps/api/core";
import { loadDoc } from "../../docs";
import { runVib } from "../core";
import type { EmitPayload } from "../reportModel";
import {
  renderReportFileWithDecisions,
  renderReportHtmlWithDecisions,
  renderReportWithDecisions,
} from "../report";

const mockInvoke = vi.mocked(invoke);
const mockLoadDoc = vi.mocked(loadDoc);
const mockRunVib = vi.mocked(runVib);

const renderPayload: EmitPayload = {
  ok: true,
  report_type: "work",
  slug: "p",
  key: "k1",
  base: {
    title: "보고서",
    report_type: "work",
    date: "2026-06-20",
    source_plan_path: "plans/p.md",
    sections: [{ heading: "요약", blocks: [{ kind: "paragraph", text: "초안", items: [] }] }],
  },
  polished: {
    title: "보고서",
    report_type: "work",
    date: "2026-06-20",
    source_plan_path: "plans/p.md",
    sections: [{ heading: "요약", blocks: [{ kind: "paragraph", text: "다듬은 초안", items: [] }] }],
  },
  guards: [],
  vague_warnings: [],
  quality: {
    schema_version: "report-quality-v1",
    status: "ok",
    rawStatus: "ok",
    score: 100,
    readiness: "ready",
    rawReadiness: "ready",
    summary: "ok",
    findings: [],
  },
  assistance: {
    schema_version: "report-assist-v1",
    status: "not_requested",
    rawStatus: "not_requested",
    suggestions: [],
    questions: [],
    applied_suggestion_ids: [],
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  mockInvoke.mockResolvedValue("/proj/.vibelign/reports/render-payloads/render-payload-1.json");
});

describe("renderReportWithDecisions", () => {
  test("uses payload path env with reject blocks and polish key", async () => {
    mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html" }), stderr: "", exit_code: 0 });

    const r = await renderReportWithDecisions({
      cwd: "/proj",
      planPath: "plans/p.md",
      reportType: "work",
      format: "html",
      rejectBlocks: [[0, 1]],
      payload: renderPayload,
    });

    expect(r.ok).toBe(true);
    expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--reject-blocks", "[[0,1]]", "--polish-key", "k1"]));
    expect(mockInvoke).toHaveBeenCalledWith("write_report_render_payload", {
      root: "/proj",
      payloadJson: JSON.stringify(renderPayload),
    });
    expect(mockRunVib.mock.calls[0][2]).toEqual({
      VIBELIGN_REPORT_RENDER_PAYLOAD_PATH: "/proj/.vibelign/reports/render-payloads/render-payload-1.json",
    });
    expect(mockInvoke).toHaveBeenCalledWith("remove_report_render_payload", {
      root: "/proj",
      path: "/proj/.vibelign/reports/render-payloads/render-payload-1.json",
    });
  });

  test("preserves theme and font size arguments", async () => {
    mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html" }), stderr: "", exit_code: 0 });

    await renderReportWithDecisions({
      cwd: "/proj",
      planPath: "plans/p.md",
      reportType: "work",
      format: "html",
      rejectBlocks: [[0, 1]],
      payload: renderPayload,
      theme: "executive",
      fontSizes: { body: 16 },
    });

    expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--theme", "executive", "--body-font-size", "16"]));
  });
});

test("renderReportHtmlWithDecisions reads the persisted rendered artifact", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/proj/.vibelign/reports/r.html" }), stderr: "", exit_code: 0 });
  mockLoadDoc.mockResolvedValue({
    path: ".vibelign/reports/r.html",
    content: "<html><body>사용자 확인 보완 초안</body></html>",
    source_hash: "hash",
  });

  const r = await renderReportHtmlWithDecisions({
    cwd: "/proj",
    planPath: "plans/p.md",
    reportType: "work",
    format: "html",
    rejectBlocks: [],
    payload: renderPayload,
  });

  expect(r.ok).toBe(true);
  if (r.ok) expect(r.html).toContain("사용자 확인 보완 초안");
  expect(mockLoadDoc).toHaveBeenCalledWith("/proj", ".vibelign/reports/r.html");
});

test("renderReportFileWithDecisions converts PDF render output and stamps page numbers", async () => {
  mockInvoke
    .mockResolvedValueOnce("/proj/.vibelign/reports/render-payloads/render-payload-1.json")
    .mockResolvedValueOnce(undefined)
    .mockResolvedValueOnce("/proj/.vibelign/reports/r.pdf");
  mockRunVib
    .mockResolvedValueOnce({ ok: true, stdout: JSON.stringify({ ok: true, path: "/proj/.vibelign/reports/r.html" }), stderr: "", exit_code: 0 })
    .mockResolvedValueOnce({ ok: true, stdout: JSON.stringify({ ok: true, path: "/proj/.vibelign/reports/r.pdf" }), stderr: "", exit_code: 0 });

  const r = await renderReportFileWithDecisions({
    cwd: "/proj",
    planPath: "plans/p.md",
    reportType: "work",
    format: "pdf",
    rejectBlocks: [],
    payload: renderPayload,
    pageNumbers: true,
  });

  expect(r).toEqual({ ok: true, path: "/proj/.vibelign/reports/r.pdf" });
  expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--format", "html"]));
  expect(mockInvoke).toHaveBeenCalledWith("export_report_pdf", {
    root: "/proj",
    htmlPath: "/proj/.vibelign/reports/r.html",
    outPdf: "/proj/.vibelign/reports/r.pdf",
  });
  expect(mockRunVib.mock.calls[1][0]).toEqual(expect.arrayContaining(["report-stamp-pdf", "/proj/.vibelign/reports/r.pdf"]));
});

test("renderReportFileWithDecisions routes DOCX and PPTX through render payload formats", async () => {
  mockRunVib.mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/proj/.vibelign/reports/r.docx" }), stderr: "", exit_code: 0 });

  const docx = await renderReportFileWithDecisions({
    cwd: "/proj",
    planPath: "plans/p.md",
    reportType: "work",
    format: "docx",
    rejectBlocks: [],
    payload: renderPayload,
  });
  await renderReportFileWithDecisions({
    cwd: "/proj",
    planPath: "plans/p.md",
    reportType: "work",
    format: "pptx",
    rejectBlocks: [],
    payload: renderPayload,
  });

  expect(docx.ok).toBe(true);
  expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--format", "docx"]));
  expect(mockRunVib.mock.calls[1][0]).toEqual(expect.arrayContaining(["--format", "pptx"]));
});
// === ANCHOR: REPORT_RENDER_PAYLOAD_TEST_END ===
