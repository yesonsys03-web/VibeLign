export const REPORT_ASSIST_STATUSES = ["not_requested", "ready", "needs_user_input", "failed"] as const;
export type ReportAssistStatus = (typeof REPORT_ASSIST_STATUSES)[number];

export const REPORT_ASSIST_SUGGESTION_KINDS = [
  "draft_text",
  "source_candidate",
  "user_question",
  "risk_candidate",
  "next_action_candidate",
] as const;
export type ReportAssistSuggestionKind = (typeof REPORT_ASSIST_SUGGESTION_KINDS)[number];

export type ReportAssistSourceRef = {
  readonly chunk_id: string;
  readonly heading_path: readonly string[];
  readonly start_line?: number;
  readonly end_line?: number;
  readonly warning?: string;
};

export type ReportAssistSuggestion = {
  readonly id: string;
  readonly finding_code: string;
  readonly kind: ReportAssistSuggestionKind;
  readonly rawKind: string | null;
  readonly kindLabel: string;
  readonly title: string;
  readonly proposed_text: string;
  readonly rationale: string;
  readonly source_refs: readonly ReportAssistSourceRef[];
  readonly requires_user_confirmation: boolean;
};

export type ReportAssistPayload = {
  readonly schema_version: "report-assist-v1";
  readonly status: ReportAssistStatus;
  readonly rawStatus: string | null;
  readonly suggestions: readonly ReportAssistSuggestion[];
  readonly questions: readonly ReportAssistSuggestion[];
  readonly applied_suggestion_ids: readonly string[];
};

export type ReportAssistSelectionStatus = "accepted" | "edited";

export type ReportAssistSelectedSuggestion = {
  readonly id: string;
  readonly text: string;
  readonly status: ReportAssistSelectionStatus;
};

export type ReportAssistSuggestionState = {
  readonly selected: readonly ReportAssistSelectedSuggestion[];
  readonly rejectedIds: readonly string[];
};

export type ReportAssistSuggestionStateUpdate =
  | { readonly type: "accept"; readonly suggestionId: string; readonly text: string }
  | { readonly type: "edit"; readonly suggestionId: string; readonly text: string }
  | { readonly type: "reject"; readonly suggestionId: string };

function assertNever(value: never): never {
  throw new Error(`Unhandled report assistance variant: ${String(value)}`);
}

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function stringArray(value: unknown): readonly string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function positiveLine(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : null;
}

function normalizeStatus(value: unknown): ReportAssistStatus {
  switch (value) {
    case "not_requested":
    case "ready":
    case "needs_user_input":
    case "failed":
      return value;
    default:
      return "needs_user_input";
  }
}

function normalizeKind(value: unknown): ReportAssistSuggestionKind {
  switch (value) {
    case "draft_text":
    case "source_candidate":
    case "user_question":
    case "risk_candidate":
    case "next_action_candidate":
      return value;
    default:
      return "user_question";
  }
}

export function reportAssistSuggestionKindLabel(kind: ReportAssistSuggestionKind): string {
  switch (kind) {
    case "draft_text":
      return "초안 문구";
    case "source_candidate":
      return "원문 근거 후보";
    case "user_question":
      return "사용자 확인 필요";
    case "risk_candidate":
      return "리스크 후보";
    case "next_action_candidate":
      return "다음 액션 후보";
    default:
      return assertNever(kind);
  }
}

function warningSourceRef(chunkId: string, headingPath: readonly string[], warning: string): ReportAssistSourceRef {
  return { chunk_id: chunkId, heading_path: headingPath, warning };
}

function parseSourceRef(value: unknown): ReportAssistSourceRef {
  if (!isRecord(value)) return warningSourceRef("unknown-source", [], "출처 범위를 확인할 수 없습니다.");

  const chunkId = stringValue(value.chunk_id) ?? "unknown-source";
  const headingPath = stringArray(value.heading_path);
  const startLine = positiveLine(value.start_line);
  const endLine = positiveLine(value.end_line);
  if (startLine === null || endLine === null || endLine < startLine) {
    return warningSourceRef(chunkId, headingPath, "출처 줄 범위가 올바르지 않습니다.");
  }

  return {
    chunk_id: chunkId,
    heading_path: headingPath,
    start_line: startLine,
    end_line: endLine,
  };
}

function parseSourceRefs(value: unknown): readonly ReportAssistSourceRef[] {
  if (!Array.isArray(value)) return [];
  return value.map(parseSourceRef);
}

function parseSuggestion(value: unknown): ReportAssistSuggestion {
  if (!isRecord(value)) {
    return {
      id: "unknown-assist-suggestion",
      finding_code: "unknown",
      kind: "user_question",
      rawKind: null,
      kindLabel: reportAssistSuggestionKindLabel("user_question"),
      title: "보완 제안 확인",
      proposed_text: "보완 제안을 읽을 수 없습니다.",
      rationale: "응답 형식이 예상과 다릅니다.",
      source_refs: [],
      requires_user_confirmation: true,
    };
  }

  const kind = normalizeKind(value.kind);
  return {
    id: stringValue(value.id) ?? "unknown-assist-suggestion",
    finding_code: stringValue(value.finding_code) ?? "unknown",
    kind,
    rawKind: stringValue(value.kind),
    kindLabel: reportAssistSuggestionKindLabel(kind),
    title: stringValue(value.title) ?? "보완 제안 확인",
    proposed_text: stringValue(value.proposed_text) ?? "",
    rationale: stringValue(value.rationale) ?? "사용자 확인이 필요합니다.",
    source_refs: parseSourceRefs(value.source_refs),
    requires_user_confirmation: true,
  };
}

function parseSuggestions(value: unknown): readonly ReportAssistSuggestion[] {
  if (!Array.isArray(value)) return [];
  return value.map(parseSuggestion);
}

export function parseReportAssistPayload(value: unknown): ReportAssistPayload {
  if (!isRecord(value)) {
    return {
      schema_version: "report-assist-v1",
      status: "needs_user_input",
      rawStatus: null,
      suggestions: [],
      questions: [],
      applied_suggestion_ids: [],
    };
  }

  return {
    schema_version: "report-assist-v1",
    status: normalizeStatus(value.status),
    rawStatus: stringValue(value.status),
    suggestions: parseSuggestions(value.suggestions),
    questions: parseSuggestions(value.questions),
    applied_suggestion_ids: stringArray(value.applied_suggestion_ids),
  };
}

export function createReportAssistSuggestionState(): ReportAssistSuggestionState {
  return { selected: [], rejectedIds: [] };
}

function selectedWithoutId(
  selected: readonly ReportAssistSelectedSuggestion[],
  suggestionId: string,
): readonly ReportAssistSelectedSuggestion[] {
  return selected.filter((item) => item.id !== suggestionId);
}

function idsWithoutId(ids: readonly string[], suggestionId: string): readonly string[] {
  return ids.filter((id) => id !== suggestionId);
}

function hasSuggestion(suggestions: readonly ReportAssistSuggestion[], suggestionId: string): boolean {
  return suggestions.some((suggestion) => suggestion.id === suggestionId);
}

export function reportAssistSuggestionStateUpdate(
  state: ReportAssistSuggestionState,
  update: ReportAssistSuggestionStateUpdate,
): ReportAssistSuggestionState {
  switch (update.type) {
    case "accept":
      return {
        selected: [
          ...selectedWithoutId(state.selected, update.suggestionId),
          { id: update.suggestionId, text: update.text, status: "accepted" },
        ],
        rejectedIds: idsWithoutId(state.rejectedIds, update.suggestionId),
      };
    case "edit":
      return {
        selected: [
          ...selectedWithoutId(state.selected, update.suggestionId),
          { id: update.suggestionId, text: update.text, status: "edited" },
        ],
        rejectedIds: idsWithoutId(state.rejectedIds, update.suggestionId),
      };
    case "reject":
      return {
        selected: selectedWithoutId(state.selected, update.suggestionId),
        rejectedIds: state.rejectedIds.includes(update.suggestionId)
          ? state.rejectedIds
          : [...state.rejectedIds, update.suggestionId],
      };
    default:
      return assertNever(update);
  }
}

export function acceptedReportAssistSuggestionIds(state: ReportAssistSuggestionState): readonly string[] {
  return state.selected.filter((item) => item.status === "accepted").map((item) => item.id);
}

export function editedReportAssistSuggestionIds(state: ReportAssistSuggestionState): readonly string[] {
  return state.selected.filter((item) => item.status === "edited").map((item) => item.id);
}

export function selectedReportAssistSuggestions(
  payload: ReportAssistPayload,
  state: ReportAssistSuggestionState,
): readonly ReportAssistSelectedSuggestion[] {
  return state.selected.filter(
    (item) => !state.rejectedIds.includes(item.id) && hasSuggestion(payload.suggestions, item.id),
  );
}
