// === ANCHOR: REPORTSESSIONDRAFT_START ===
import type {
  ReportQualityPanelProceedPayload,
  ReportQualityQuestionAnswer,
} from "./ReportQualityPanel";
import type { EmitPayload, RModelBlock, RModelSection } from "../../lib/vib/reportModel";

export type ReportSessionDraftEntry = {
  readonly id: string;
  readonly text: string;
  readonly source: "suggestion" | "answer";
};

export type ReportSessionDraft = {
  readonly entries: readonly ReportSessionDraftEntry[];
};

// === ANCHOR: REPORTSESSIONDRAFT_CLEANTEXT_START ===
function cleanText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
// === ANCHOR: REPORTSESSIONDRAFT_CLEANTEXT_END ===

// === ANCHOR: REPORTSESSIONDRAFT_ANSWERTEXT_START ===
function answerText(answer: ReportQualityQuestionAnswer): string | null {
  const text = cleanText(answer.answer);
  return text === null ? null : text;
}
// === ANCHOR: REPORTSESSIONDRAFT_ANSWERTEXT_END ===

// === ANCHOR: REPORTSESSIONDRAFT_CREATEREPORTSESSIONDRAFT_START ===
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
// === ANCHOR: REPORTSESSIONDRAFT_CREATEREPORTSESSIONDRAFT_END ===

// === ANCHOR: REPORTSESSIONDRAFT_HASREPORTSESSIONDRAFT_START ===
export function hasReportSessionDraft(draft: ReportSessionDraft): boolean {
  return draft.entries.length > 0;
}
// === ANCHOR: REPORTSESSIONDRAFT_HASREPORTSESSIONDRAFT_END ===

// === ANCHOR: REPORTSESSIONDRAFT_DRAFTMARKDOWNTOBLOCKS_START ===
const _BULLET_RE = /^(\s*)(?:[-*]\s+|\d+[.)]\s+)(.*)$/;
const _HEADING_RE = /^#{1,6}\s+(.*)$/;

/** Turn the AI draft markdown into renderer blocks (bullets/paragraph) so it reads like the
 *  rest of the report instead of one escaped wall of `- **…**` text. Mirrors the Python
 *  `parse_generic_markdown` block primitives; nested bullets are flattened with a `↳` prefix.
 *  Inline markers (`**bold**`, `*em*`, `` `code` ``) are kept verbatim — the HTML renderer
 *  converts them to <strong>/<em>/<code> (see html_renderer._render_inline). */
function draftMarkdownToBlocks(text: string): RModelBlock[] {
  const blocks: RModelBlock[] = [];
  let para: string[] = [];
  let bullets: string[] = [];
  const flushPara = (): void => {
    const joined = para.map((s) => s.trim()).filter((s) => s !== "").join(" ");
    if (joined !== "") blocks.push({ kind: "paragraph", text: joined, items: [] });
    para = [];
  };
  const flushBullets = (): void => {
    if (bullets.length > 0) blocks.push({ kind: "bullets", text: "", items: bullets });
    bullets = [];
  };
  for (const rawLine of text.split("\n")) {
    const line = rawLine.replace(/\s+$/, "");
    if (line.trim() === "") {
      flushBullets();
      flushPara();
      continue;
    }
    const heading = _HEADING_RE.exec(line.trim());
    if (heading) {
      flushBullets();
      flushPara();
      const headingText = heading[1].trim();
      if (headingText !== "") blocks.push({ kind: "paragraph", text: headingText, items: [] });
      continue;
    }
    const bullet = _BULLET_RE.exec(line);
    if (bullet) {
      flushPara();
      const content = bullet[2].trim();
      if (content !== "") bullets.push(bullet[1].length > 0 ? `↳ ${content}` : content);
      continue;
    }
    flushBullets();
    para.push(line);
  }
  flushBullets();
  flushPara();
  return blocks.length > 0 ? blocks : [{ kind: "paragraph", text: text.trim(), items: [] }];
}
// === ANCHOR: REPORTSESSIONDRAFT_DRAFTMARKDOWNTOBLOCKS_END ===

// === ANCHOR: REPORTSESSIONDRAFT_APPLYREPORTSESSIONDRAFTTOEMITPAYLOAD_START ===
export function applyReportSessionDraftToEmitPayload(payload: EmitPayload, draft: ReportSessionDraft): EmitPayload {
  if (!hasReportSessionDraft(draft)) return payload;
  const draftSection: RModelSection = {
    heading: "사용자 확인 보완 초안",
    blocks: draftMarkdownToBlocks(draft.entries.map((entry) => entry.text).join("\n")),
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
// === ANCHOR: REPORTSESSIONDRAFT_APPLYREPORTSESSIONDRAFTTOEMITPAYLOAD_END ===
// === ANCHOR: REPORTSESSIONDRAFT_END ===
