import type {
  ReportAssistSelectedSuggestion,
  ReportAssistSuggestion,
} from "../../lib/vib/reportAssist";
import type {
  ReportQualityFinding,
  ReportQualityPayload,
  ReportQualityStatus,
} from "../../lib/vib/reportQuality";

export type ReportQualityScorePreview = {
  readonly score: number;
  readonly status: ReportQualityStatus;
  readonly addressedCount: number;
  readonly remainingCount: number;
};

export type ReportQualityScorePreviewInput = {
  readonly quality: ReportQualityPayload;
  readonly items: readonly ReportAssistSuggestion[];
  readonly selectedSuggestions: readonly ReportAssistSelectedSuggestion[];
  readonly savedAnswers: Readonly<Record<string, string>>;
  readonly rejectedIds: readonly string[];
};

function findingWeight(code: string): number {
  switch (code) {
    case "missing_audience":
    case "missing_objective":
    case "missing_decision_or_recommendation":
    case "missing_risk":
    case "missing_next_action":
      return 12;
    case "missing_evidence":
      return 14;
    case "unresolved_questions":
      return 6;
    case "format_risk":
    case "parser_confidence":
      return 4;
    default:
      return 0;
  }
}

function isAnswered(value: string | undefined): boolean {
  return value !== undefined && value.trim() !== "";
}

function coveredFindingCodes(input: ReportQualityScorePreviewInput): ReadonlySet<string> {
  const itemById = new Map(input.items.map((item) => [item.id, item] as const));
  const rejectedIds = new Set(input.rejectedIds);
  const covered = new Set<string>();

  for (const selected of input.selectedSuggestions) {
    if (rejectedIds.has(selected.id) || !isAnswered(selected.text)) continue;
    const item = itemById.get(selected.id);
    if (item !== undefined) covered.add(item.finding_code);
  }

  for (const item of input.items) {
    if (item.kind !== "user_question" || rejectedIds.has(item.id)) continue;
    if (isAnswered(input.savedAnswers[item.id])) covered.add(item.finding_code);
  }

  return covered;
}

function statusFromRemaining(findings: readonly ReportQualityFinding[]): ReportQualityStatus {
  if (findings.some((finding) => finding.blocking)) return "block";
  return findings.length === 0 ? "ok" : "warn";
}

export function scoreImpactForFindingCode(
  quality: ReportQualityPayload,
  findingCode: string,
): number {
  const nonBlockingFindings = quality.findings.filter((finding) => !finding.blocking);
  const matchingScore = nonBlockingFindings
    .filter((finding) => finding.code === findingCode)
    .reduce((score, finding) => score + findingWeight(finding.code), 0);
  if (
    matchingScore > 0 &&
    nonBlockingFindings.length > 0 &&
    nonBlockingFindings.every((finding) => finding.code === findingCode)
  ) {
    return Math.max(matchingScore, 100 - quality.score);
  }
  return matchingScore;
}

export function previewReportQualityScore(input: ReportQualityScorePreviewInput): ReportQualityScorePreview {
  const covered = coveredFindingCodes(input);
  const remainingFindings = input.quality.findings.filter(
    (finding) => finding.blocking || !covered.has(finding.code),
  );
  const addressedScore = input.quality.findings
    .filter((finding) => covered.has(finding.code) && !finding.blocking)
    .reduce((score, finding) => score + findingWeight(finding.code), 0);

  return {
    score: remainingFindings.length === 0 ? 100 : Math.min(100, input.quality.score + addressedScore),
    status: statusFromRemaining(remainingFindings),
    addressedCount: input.quality.findings.length - remainingFindings.length,
    remainingCount: remainingFindings.length,
  };
}
