import type {
  ReportQualityPanelProceedPayload,
  ReportQualityQuestionAnswer,
} from "./ReportQualityPanel";
import type { EmitPayload, RModelSection } from "../../lib/vib/reportModel";

export type ReportSessionDraftEntry = {
  readonly id: string;
  readonly text: string;
  readonly source: "suggestion" | "answer";
};

export type ReportSessionDraft = {
  readonly entries: readonly ReportSessionDraftEntry[];
};

function cleanText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function answerText(answer: ReportQualityQuestionAnswer): string | null {
  const text = cleanText(answer.answer);
  return text === null ? null : text;
}

export function createReportSessionDraft(payload: ReportQualityPanelProceedPayload): ReportSessionDraft {
  const suggestionEntries = payload.selectedSuggestions.flatMap((suggestion): readonly ReportSessionDraftEntry[] => {
    const text = cleanText(suggestion.text);
    return text === null ? [] : [{ id: suggestion.id, text, source: "suggestion" }];
  });
  const answerEntries = payload.questionAnswers.flatMap((answer): readonly ReportSessionDraftEntry[] => {
    const text = answerText(answer);
    return text === null ? [] : [{ id: answer.suggestionId, text, source: "answer" }];
  });
  return { entries: [...suggestionEntries, ...answerEntries] };
}

export function hasReportSessionDraft(draft: ReportSessionDraft): boolean {
  return draft.entries.length > 0;
}

export function applyReportSessionDraftToEmitPayload(payload: EmitPayload, draft: ReportSessionDraft): EmitPayload {
  if (!hasReportSessionDraft(draft)) return payload;
  const draftSection: RModelSection = {
    heading: "사용자 확인 보완 초안",
    blocks: [
      {
        kind: "paragraph",
        text: draft.entries.map((entry) => entry.text).join("\n"),
        items: [],
      },
    ],
  };
  return {
    ...payload,
    base: {
      ...payload.base,
      sections: [...payload.base.sections, draftSection],
    },
    polished: {
      ...payload.polished,
      sections: [...payload.polished.sections, draftSection],
    },
  };
}
