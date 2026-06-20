import { describe, expect, test } from "vitest";

import {
  categoryLabel,
  parseReportQualityPayload,
  qualitySeverityRank,
  sortQualityFindingsBySeverity,
} from "../reportQuality";

describe("report quality parser", () => {
  test("normalizes unknown status, severity, and finding code without throwing", () => {
    const quality = parseReportQualityPayload({
      schema_version: "report-quality-v1",
      status: "review_later",
      score: 150,
      readiness: "almost_ready",
      summary: "custom backend payload",
      findings: [
        {
          code: "new_backend_check",
          severity: "critical",
          message: "backend added a category",
          source: "future_source",
          blocking: true,
          section: 2,
          block: 3,
          suggestion: "show a safe warning",
        },
      ],
    });

    expect(quality.status).toBe("warn");
    expect(quality.rawStatus).toBe("review_later");
    expect(quality.score).toBe(100);
    expect(quality.readiness).toBe("needs_review");
    expect(quality.findings[0]).toMatchObject({
      code: "new_backend_check",
      rawCategory: "new_backend_check",
      categoryLabel: "기타 점검",
      severity: "warn",
      rawSeverity: "critical",
      source: "unknown",
      rawSource: "future_source",
      blocking: true,
    });
  });

  test("uses stable labels and severity ordering", () => {
    const quality = parseReportQualityPayload({
      status: "warn",
      findings: [
        { code: "missing_risk", severity: "warn", message: "risk", source: "report_model", blocking: false },
        { code: "empty_content", severity: "block", message: "empty", source: "template", blocking: true },
        { code: "parser_confidence", severity: "info", message: "parser", source: "reader", blocking: false },
      ],
    });

    const sorted = sortQualityFindingsBySeverity(quality.findings);

    expect(categoryLabel("missing_next_action")).toBe("다음 액션 누락");
    expect(qualitySeverityRank("block")).toBeGreaterThan(qualitySeverityRank("warn"));
    expect(sorted.map((finding) => finding.severity)).toEqual(["block", "warn", "info"]);
  });

  test("returns safe warning data for malformed payloads", () => {
    expect(() => parseReportQualityPayload("not-json-object")).not.toThrow();

    const quality = parseReportQualityPayload({ status: "surprise", findings: "bad" });

    expect(quality.status).toBe("warn");
    expect(quality.findings).toHaveLength(1);
    expect(quality.findings[0].code).toBe("unknown_quality_payload");
    expect(quality.findings[0].severity).toBe("warn");
  });
});
