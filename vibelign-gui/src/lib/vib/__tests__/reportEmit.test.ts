import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../core", () => ({ runVib: vi.fn() }));

import { runVib } from "../core";
import { emitReportModel, requestReportAssistance } from "../reportEmit";

const mockRunVib = vi.mocked(runVib);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("report emit wrappers", () => {
  test("emitReportModel adds --emit-model and parses payload sidecars", async () => {
    mockRunVib.mockResolvedValue({
      ok: true,
      stdout: JSON.stringify({
        ok: true,
        report_type: "work",
        slug: "s",
        key: "k1",
        base: {},
        polished: {},
        guards: [],
        vague_warnings: [],
        quality: {
          schema_version: "report-quality-v1",
          status: "warn",
          score: 50,
          readiness: "needs_review",
          summary: "4개 품질 경고를 검토하세요.",
          findings: [
            {
              code: "missing_evidence",
              severity: "warn",
              message: "근거가 부족합니다.",
              source: "report_model",
              blocking: false,
            },
          ],
        },
        assistance: {
          schema_version: "report-assist-v1",
          status: "not_requested",
          suggestions: [],
          questions: [],
          applied_suggestion_ids: [],
        },
      }),
      stderr: "",
      exit_code: 0,
    });

    const result = await emitReportModel("/proj", "plans/p.md", "work", true);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.key).toBe("k1");
      expect(result.payload.quality.status).toBe("warn");
      expect(result.payload.quality.findings[0].code).toBe("missing_evidence");
      expect(result.payload.assistance.status).toBe("not_requested");
    }
    expect(mockRunVib.mock.calls[0][0]).toEqual(expect.arrayContaining(["--emit-model", "--polish"]));
  });

  test("requestReportAssistance adds --assist-missing and parses assistance sidecar", async () => {
    mockRunVib.mockResolvedValue({
      ok: true,
      stdout: JSON.stringify({
        ok: true,
        report_type: "proposal",
        quality: {
          schema_version: "report-quality-v1",
          status: "warn",
          score: 70,
          readiness: "needs_review",
          summary: "확인이 필요합니다.",
          findings: [],
        },
        assistance: {
          schema_version: "report-assist-v1",
          status: "needs_user_input",
          suggestions: [
            {
              id: "missing-evidence-question",
              finding_code: "missing_evidence",
              kind: "user_question",
              title: "근거 보완",
              proposed_text: "근거를 알려주세요.",
              rationale: "원문에 충분한 근거가 없습니다.",
              source_refs: [],
              requires_user_confirmation: true,
            },
          ],
          questions: [],
          applied_suggestion_ids: [],
        },
      }),
      stderr: "",
      exit_code: 0,
    });

    const result = await requestReportAssistance({
      cwd: "/proj",
      planPath: "plans/p.md",
      reportType: "proposal",
      author: "팀장",
      assistProvider: "codex",
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.assistance.status).toBe("needs_user_input");
      expect(result.payload.assistance.suggestions[0].kind).toBe("user_question");
    }
    expect(mockRunVib.mock.calls[0][0]).toEqual(
      expect.arrayContaining([
        "report",
        "plans/p.md",
        "--type",
        "proposal",
        "--assist-missing",
        "--cli",
        "codex",
        "--author",
        "팀장",
        "--json",
      ]),
    );
  });
});
