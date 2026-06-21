// === ANCHOR: REPORTQUALITY_START ===
export const REPORT_QUALITY_STATUSES = ["ok", "warn", "block"] as const;
export type ReportQualityStatus = (typeof REPORT_QUALITY_STATUSES)[number];

export const REPORT_QUALITY_READINESS = ["ready", "needs_review", "blocked"] as const;
export type ReportQualityReadiness = (typeof REPORT_QUALITY_READINESS)[number];

export const REPORT_QUALITY_SEVERITIES = ["info", "warn", "block"] as const;
export type ReportQualitySeverity = (typeof REPORT_QUALITY_SEVERITIES)[number];

export const REPORT_QUALITY_SOURCES = ["planning_data", "report_model", "reader", "template", "format"] as const;
export type ReportQualitySource = (typeof REPORT_QUALITY_SOURCES)[number] | "unknown";

export const REPORT_QUALITY_CATEGORIES = [
  "missing_audience",
  "missing_objective",
  "missing_evidence",
  "missing_decision_or_recommendation",
  "missing_risk",
  "missing_next_action",
  "unresolved_questions",
  "format_risk",
  "parser_confidence",
  "empty_content",
] as const;
export type ReportQualityCategory = (typeof REPORT_QUALITY_CATEGORIES)[number];

export type ReportQualityFinding = {
  readonly code: string;
  readonly rawCategory: string;
  readonly categoryLabel: string;
  readonly severity: ReportQualitySeverity;
  readonly rawSeverity: string | null;
  readonly message: string;
  readonly source: ReportQualitySource;
  readonly rawSource: string | null;
  readonly blocking: boolean;
  readonly section?: number;
  readonly block?: number;
  readonly suggestion?: string;
};

export type ReportQualityPayload = {
  readonly schema_version: "report-quality-v1";
  readonly status: ReportQualityStatus;
  readonly rawStatus: string | null;
  readonly score: number;
  readonly readiness: ReportQualityReadiness;
  readonly rawReadiness: string | null;
  readonly summary: string;
  readonly findings: readonly ReportQualityFinding[];
};

const CATEGORY_LABELS: Readonly<Record<ReportQualityCategory, string>> = {
  missing_audience: "대상 독자 누락",
  missing_objective: "목적 누락",
  missing_evidence: "근거 누락",
  missing_decision_or_recommendation: "결정/제안 누락",
  missing_risk: "리스크 누락",
  missing_next_action: "다음 액션 누락",
  unresolved_questions: "미해결 질문",
  format_risk: "형식 리스크",
  parser_confidence: "파서 신뢰도",
  empty_content: "빈 보고서",
};

// === ANCHOR: REPORTQUALITY_ASSERTNEVER_START ===
function assertNever(value: never): never {
  throw new Error(`Unhandled report quality variant: ${String(value)}`);
}
// === ANCHOR: REPORTQUALITY_ASSERTNEVER_END ===

// === ANCHOR: REPORTQUALITY_ISRECORD_START ===
function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
// === ANCHOR: REPORTQUALITY_ISRECORD_END ===

// === ANCHOR: REPORTQUALITY_STRINGVALUE_START ===
function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}
// === ANCHOR: REPORTQUALITY_STRINGVALUE_END ===

// === ANCHOR: REPORTQUALITY_NUMBERVALUE_START ===
function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
// === ANCHOR: REPORTQUALITY_NUMBERVALUE_END ===

// === ANCHOR: REPORTQUALITY_OPTIONALINDEX_START ===
function optionalIndex(value: unknown): number | undefined {
  const parsed = numberValue(value);
  return parsed === null || !Number.isInteger(parsed) || parsed < 0 ? undefined : parsed;
}
// === ANCHOR: REPORTQUALITY_OPTIONALINDEX_END ===

// === ANCHOR: REPORTQUALITY_NORMALIZESCORE_START ===
function normalizeScore(value: unknown): number {
  const parsed = numberValue(value);
  if (parsed === null) return 0;
  return Math.min(100, Math.max(0, Math.round(parsed)));
}
// === ANCHOR: REPORTQUALITY_NORMALIZESCORE_END ===

// === ANCHOR: REPORTQUALITY_NORMALIZESTATUS_START ===
function normalizeStatus(value: unknown): ReportQualityStatus {
  switch (value) {
    case "ok":
    case "warn":
    case "block":
      return value;
    default:
      return "warn";
  }
}
// === ANCHOR: REPORTQUALITY_NORMALIZESTATUS_END ===

// === ANCHOR: REPORTQUALITY_NORMALIZEREADINESS_START ===
function normalizeReadiness(value: unknown): ReportQualityReadiness {
  switch (value) {
    case "ready":
    case "needs_review":
    case "blocked":
      return value;
    default:
      return "needs_review";
  }
}
// === ANCHOR: REPORTQUALITY_NORMALIZEREADINESS_END ===

// === ANCHOR: REPORTQUALITY_NORMALIZESEVERITY_START ===
function normalizeSeverity(value: unknown): ReportQualitySeverity {
  switch (value) {
    case "info":
    case "warn":
    case "block":
      return value;
    default:
      return "warn";
  }
}
// === ANCHOR: REPORTQUALITY_NORMALIZESEVERITY_END ===

// === ANCHOR: REPORTQUALITY_NORMALIZESOURCE_START ===
function normalizeSource(value: unknown): ReportQualitySource {
  switch (value) {
    case "planning_data":
    case "report_model":
    case "reader":
    case "template":
    case "format":
      return value;
    default:
      return "unknown";
  }
}
// === ANCHOR: REPORTQUALITY_NORMALIZESOURCE_END ===

// === ANCHOR: REPORTQUALITY_CATEGORYLABEL_START ===
export function categoryLabel(code: string): string {
  switch (code) {
    case "missing_audience":
      return CATEGORY_LABELS.missing_audience;
    case "missing_objective":
      return CATEGORY_LABELS.missing_objective;
    case "missing_evidence":
      return CATEGORY_LABELS.missing_evidence;
    case "missing_decision_or_recommendation":
      return CATEGORY_LABELS.missing_decision_or_recommendation;
    case "missing_risk":
      return CATEGORY_LABELS.missing_risk;
    case "missing_next_action":
      return CATEGORY_LABELS.missing_next_action;
    case "unresolved_questions":
      return CATEGORY_LABELS.unresolved_questions;
    case "format_risk":
      return CATEGORY_LABELS.format_risk;
    case "parser_confidence":
      return CATEGORY_LABELS.parser_confidence;
    case "empty_content":
      return CATEGORY_LABELS.empty_content;
    default:
      return "기타 점검";
  }
}
// === ANCHOR: REPORTQUALITY_CATEGORYLABEL_END ===

// === ANCHOR: REPORTQUALITY_QUALITYSEVERITYRANK_START ===
export function qualitySeverityRank(severity: ReportQualitySeverity): number {
  switch (severity) {
    case "block":
      return 3;
    case "warn":
      return 2;
    case "info":
      return 1;
    default:
      return assertNever(severity);
  }
}
// === ANCHOR: REPORTQUALITY_QUALITYSEVERITYRANK_END ===

// === ANCHOR: REPORTQUALITY_SORTQUALITYFINDINGSBYSEVERITY_START ===
export function sortQualityFindingsBySeverity(findings: readonly ReportQualityFinding[]): readonly ReportQualityFinding[] {
  return [...findings].sort((left, right) => qualitySeverityRank(right.severity) - qualitySeverityRank(left.severity));
}
// === ANCHOR: REPORTQUALITY_SORTQUALITYFINDINGSBYSEVERITY_END ===

// === ANCHOR: REPORTQUALITY_PARSEFINDING_START ===
function parseFinding(value: unknown): ReportQualityFinding {
  if (!isRecord(value)) {
    return {
      code: "unknown_quality_payload",
      rawCategory: "unknown_quality_payload",
      categoryLabel: "기타 점검",
      severity: "warn",
      rawSeverity: null,
      message: "품질 점검 항목을 읽을 수 없습니다.",
      source: "unknown",
      rawSource: null,
      blocking: false,
    };
  }

  const code = stringValue(value.code) ?? "unknown_quality_payload";
  const rawSeverity = stringValue(value.severity);
  const rawSource = stringValue(value.source);
  const section = optionalIndex(value.section);
  const block = optionalIndex(value.block);
  const suggestion = stringValue(value.suggestion);
  return {
    code,
    rawCategory: code,
    categoryLabel: categoryLabel(code),
    severity: normalizeSeverity(value.severity),
    rawSeverity,
    message: stringValue(value.message) ?? "품질 점검 항목을 검토하세요.",
    source: normalizeSource(value.source),
    rawSource,
    blocking: value.blocking === true,
    ...(section === undefined ? {} : { section }),
    ...(block === undefined ? {} : { block }),
    ...(suggestion === null ? {} : { suggestion }),
  };
}
// === ANCHOR: REPORTQUALITY_PARSEFINDING_END ===

// === ANCHOR: REPORTQUALITY_PARSEFINDINGS_START ===
function parseFindings(value: unknown): readonly ReportQualityFinding[] {
  if (!Array.isArray(value)) return [parseFinding(null)];
  return value.map(parseFinding);
}
// === ANCHOR: REPORTQUALITY_PARSEFINDINGS_END ===

// === ANCHOR: REPORTQUALITY_PARSEREPORTQUALITYPAYLOAD_START ===
export function parseReportQualityPayload(value: unknown): ReportQualityPayload {
  if (!isRecord(value)) {
    return {
      schema_version: "report-quality-v1",
      status: "warn",
      rawStatus: null,
      score: 0,
      readiness: "needs_review",
      rawReadiness: null,
      summary: "품질 점검 결과를 읽을 수 없습니다.",
      findings: [parseFinding(null)],
    };
  }

  return {
    schema_version: "report-quality-v1",
    status: normalizeStatus(value.status),
    rawStatus: stringValue(value.status),
    score: normalizeScore(value.score),
    readiness: normalizeReadiness(value.readiness),
    rawReadiness: stringValue(value.readiness),
    summary: stringValue(value.summary) ?? "품질 점검 결과를 검토하세요.",
    findings: parseFindings(value.findings),
  };
}
// === ANCHOR: REPORTQUALITY_PARSEREPORTQUALITYPAYLOAD_END ===
// === ANCHOR: REPORTQUALITY_END ===
