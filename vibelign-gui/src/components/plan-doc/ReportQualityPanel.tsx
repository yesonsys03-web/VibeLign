// === ANCHOR: REPORTQUALITYPANEL_START ===
import { useMemo, useState, type CSSProperties, type KeyboardEvent } from "react";

import {
  createReportAssistSuggestionState,
  reportAssistSuggestionStateUpdate,
  type ReportAssistPayload,
  type ReportAssistSelectedSuggestion,
  type ReportAssistSuggestion,
  type ReportAssistSuggestionState,
} from "../../lib/vib/reportAssist";
import type {
  ReportQualityFinding,
  ReportQualityPayload,
  ReportQualitySeverity,
  ReportQualityStatus,
} from "../../lib/vib/reportQuality";
import { GyariProgressBar } from "./GyariProgressBar";
import { ReportQualityAssistItem } from "./ReportQualityAssistItem";
import { ReportQualityScorePreviewView } from "./ReportQualityScorePreview";
import {
  normalizeReportAssistProviderId,
  reportAssistProviderOptions,
  type ReportAssistProviderId,
  type ReportAssistProviderOption,
} from "./reportAssistProviders";
import { previewReportQualityScore, scoreImpactForFindingCode } from "./reportQualityScoreProjection";

export type ReportQualityQuestionAnswer = { readonly suggestionId: string; readonly answer: string };

export type ReportQualityPanelProceedPayload = {
  readonly mode: "normal" | "generate_anyway";
  readonly selectedSuggestions: readonly ReportAssistSelectedSuggestion[];
  readonly rejectedSuggestionIds: readonly string[];
  readonly questionAnswers: readonly ReportQualityQuestionAnswer[];
};

export type ReportQualityLongSource = { readonly totalLines: number; readonly analyzedSections: number };

export type ReportQualityPanelProps = {
  readonly quality: ReportQualityPayload;
  readonly assistance?: ReportAssistPayload;
  readonly sourceLabel?: string;
  readonly longSource?: ReportQualityLongSource;
  readonly nextActionText?: string;
  readonly onRequestAssistance?: (onProgress?: (done: number, total: number) => void) => Promise<ReportAssistPayload>;
  readonly assistProvider?: ReportAssistProviderId;
  readonly assistProviderOptions?: readonly ReportAssistProviderOption[];
  readonly onAssistProviderChange?: (providerId: ReportAssistProviderId) => void;
  readonly onProceed: (payload: ReportQualityPanelProceedPayload) => void;
  readonly onCancel: () => void;
};

type SeverityGroup = { readonly severity: ReportQualitySeverity; readonly label: string };

const severityGroups: readonly SeverityGroup[] = [{ severity: "block", label: "중단" }, { severity: "warn", label: "주의" }, { severity: "info", label: "정보" }];

const emptyAssistance: ReportAssistPayload = {
  schema_version: "report-assist-v1", status: "not_requested", rawStatus: "not_requested",
  suggestions: [], questions: [], applied_suggestion_ids: [],
};
const defaultAssistProviderOptions = reportAssistProviderOptions([]);

const statusLabels = { ok: "생성 가능", warn: "검토 필요", block: "생성 중단" } satisfies Record<ReportQualityStatus, string>;
const readinessLabels = { ready: "준비됨", needs_review: "검토 필요", blocked: "중단됨" } satisfies Record<ReportQualityPayload["readiness"], string>;
const nextActions = {
  ok: "바로 생성할 수 있습니다.",
  warn: "경고를 확인한 뒤 생성하거나 AI 보완을 요청하세요.",
  block: "문서 그대로 양식으로 바꾸거나 원문 섹션을 보완하세요.",
} satisfies Record<ReportQualityStatus, string>;

// === ANCHOR: REPORTQUALITYPANEL_STATUSLABEL_START ===
function statusLabel(status: ReportQualityStatus): string {
  return statusLabels[status];
}
// === ANCHOR: REPORTQUALITYPANEL_STATUSLABEL_END ===

// === ANCHOR: REPORTQUALITYPANEL_READINESSLABEL_START ===
function readinessLabel(readiness: ReportQualityPayload["readiness"]): string {
  return readinessLabels[readiness];
}
// === ANCHOR: REPORTQUALITYPANEL_READINESSLABEL_END ===

// === ANCHOR: REPORTQUALITYPANEL_DEFAULTNEXTACTION_START ===
function defaultNextAction(quality: ReportQualityPayload): string {
  return nextActions[quality.status];
}
// === ANCHOR: REPORTQUALITYPANEL_DEFAULTNEXTACTION_END ===

// === ANCHOR: REPORTQUALITYPANEL_FINDINGGROUPS_START ===
function findingGroups(findings: readonly ReportQualityFinding[]): readonly SeverityGroup[] {
  return severityGroups.filter((group) => findings.some((finding) => finding.severity === group.severity));
}
// === ANCHOR: REPORTQUALITYPANEL_FINDINGGROUPS_END ===

// === ANCHOR: REPORTQUALITYPANEL_ALLASSISTANCEITEMS_START ===
function allAssistanceItems(assistance: ReportAssistPayload): readonly ReportAssistSuggestion[] {
  const items = [...assistance.suggestions, ...assistance.questions];
  return items.filter((item, index) => items.findIndex((candidate) => candidate.id === item.id) === index);
}
// === ANCHOR: REPORTQUALITYPANEL_ALLASSISTANCEITEMS_END ===

// === ANCHOR: REPORTQUALITYPANEL_SELECTEDSUGGESTIONS_START ===
function selectedSuggestions(state: ReportAssistSuggestionState): readonly ReportAssistSelectedSuggestion[] {
  return state.selected.filter((item) => !state.rejectedIds.includes(item.id));
}
// === ANCHOR: REPORTQUALITYPANEL_SELECTEDSUGGESTIONS_END ===

// === ANCHOR: REPORTQUALITYPANEL_HASSAVEDQUESTIONANSWER_START ===
function hasSavedQuestionAnswer(savedAnswers: Readonly<Record<string, string>>, rejectedIds: readonly string[]): boolean {
  return Object.entries(savedAnswers).some(([suggestionId, answer]) => !rejectedIds.includes(suggestionId) && answer.trim() !== "");
}
// === ANCHOR: REPORTQUALITYPANEL_HASSAVEDQUESTIONANSWER_END ===

// === ANCHOR: REPORTQUALITYPANEL_PROCEEDBUTTONLABEL_START ===
function proceedButtonLabel(status: ReportQualityStatus, hasAppliedAssistance: boolean): string {
  switch (status) {
    case "block":
      return "생성 불가";
    case "warn":
      return hasAppliedAssistance ? "보완 반영해 생성" : "그래도 생성";
    case "ok":
      return "생성 계속";
  }
}
// === ANCHOR: REPORTQUALITYPANEL_PROCEEDBUTTONLABEL_END ===

// === ANCHOR: REPORTQUALITYPANEL_QUESTIONANSWERS_START ===
function questionAnswers(
  items: readonly ReportAssistSuggestion[],
  savedAnswers: Readonly<Record<string, string>>,
  rejectedIds: readonly string[],
): readonly ReportQualityQuestionAnswer[] {
  return items.flatMap((item) => {
    if (item.kind !== "user_question" || rejectedIds.includes(item.id)) return [];
    const answer = savedAnswers[item.id]?.trim();
    return answer === undefined || answer === "" ? [] : [{ suggestionId: item.id, answer }];
  });
}
// === ANCHOR: REPORTQUALITYPANEL_QUESTIONANSWERS_END ===

// === ANCHOR: REPORTQUALITYPANEL_ACTIVATEBUTTONFROMKEYBOARD_START ===
function activateButtonFromKeyboard(event: KeyboardEvent<HTMLButtonElement>, action: () => void): void {
  if ((event.key !== "Enter" && event.key !== " ") || event.repeat) return;
  event.preventDefault();
  action();
}
// === ANCHOR: REPORTQUALITYPANEL_ACTIVATEBUTTONFROMKEYBOARD_END ===

// === ANCHOR: REPORTQUALITYPANEL_ANSWERSTATUS_START ===
function answerStatus(
  suggestionId: string,
  answerDrafts: Readonly<Record<string, string>>,
  savedAnswers: Readonly<Record<string, string>>,
): "idle" | "saved" | "changed" {
  const savedAnswer = savedAnswers[suggestionId];
  if (savedAnswer === undefined) return "idle";
  return savedAnswer === (answerDrafts[suggestionId] ?? "") ? "saved" : "changed";
}
// === ANCHOR: REPORTQUALITYPANEL_ANSWERSTATUS_END ===

// === ANCHOR: REPORTQUALITYPANEL_SELECTIONSTATUS_START ===
function selectionStatus(
  suggestionId: string,
  state: ReportAssistSuggestionState,
): "idle" | "selected" | "rejected" {
  if (state.selected.some((item) => item.id === suggestionId)) return "selected";
  return state.rejectedIds.includes(suggestionId) ? "rejected" : "idle";
}
// === ANCHOR: REPORTQUALITYPANEL_SELECTIONSTATUS_END ===

// === ANCHOR: REPORTQUALITYPANEL_REPORTQUALITYPANEL_START ===
export function ReportQualityPanel({
  quality,
  assistance = emptyAssistance,
  sourceLabel = "기획안",
  longSource,
  nextActionText,
  onRequestAssistance,
  assistProvider = "local",
  assistProviderOptions = defaultAssistProviderOptions,
  onAssistProviderChange,
  onProceed,
  onCancel,
}: ReportQualityPanelProps) {
  const [currentAssistance, setCurrentAssistance] = useState(assistance);
  const [assistState, setAssistState] = useState(createReportAssistSuggestionState);
  const [suggestionEdits, setSuggestionEdits] = useState<Readonly<Record<string, string>>>({});
  const [answerDrafts, setAnswerDrafts] = useState<Readonly<Record<string, string>>>({});
  const [savedAnswers, setSavedAnswers] = useState<Readonly<Record<string, string>>>({});
  const [loadingAssistance, setLoadingAssistance] = useState(false);
  const [assistProgress, setAssistProgress] = useState<{ done: number; total: number } | null>(null);
  const [assistError, setAssistError] = useState<string | null>(null);

  const items = useMemo(() => allAssistanceItems(currentAssistance), [currentAssistance]);
  const groups = findingGroups(quality.findings);
  const metricText = quality.score > 0 ? `점수 ${quality.score}` : readinessLabel(quality.readiness);
  const selectedAssistance = useMemo(() => selectedSuggestions(assistState), [assistState]);
  const hasAppliedAssistance = selectedAssistance.length > 0 || hasSavedQuestionAnswer(savedAnswers, assistState.rejectedIds);
  const scorePreview = useMemo(
    () =>
      previewReportQualityScore({
        quality,
        items,
        selectedSuggestions: selectedAssistance,
        savedAnswers,
        rejectedIds: assistState.rejectedIds,
      }),
    [quality, items, selectedAssistance, savedAnswers, assistState.rejectedIds],
  );
  const effectiveStatus = scorePreview.status;
  const isBlocking = effectiveStatus === "block";
  const visibleAssistProvider = assistProviderOptions.some((option) => option.id === assistProvider)
    ? assistProvider
    : "local";

  // === ANCHOR: REPORTQUALITYPANEL_PROCEED_START ===
  const proceed = () => {
    if (isBlocking) return;
    onProceed({
      mode: effectiveStatus === "warn" ? "generate_anyway" : "normal",
      selectedSuggestions: selectedAssistance,
      rejectedSuggestionIds: assistState.rejectedIds,
      questionAnswers: questionAnswers(items, savedAnswers, assistState.rejectedIds),
    });
  };
  // === ANCHOR: REPORTQUALITYPANEL_PROCEED_END ===

  // === ANCHOR: REPORTQUALITYPANEL_REQUESTASSISTANCE_START ===
  const requestAssistance = async () => {
    if (onRequestAssistance === undefined) return;
    setLoadingAssistance(true);
    setAssistProgress(null);
    setAssistError(null);
    try {
      setCurrentAssistance(await onRequestAssistance((done, total) => setAssistProgress({ done, total })));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown";
      setAssistError(`보완 제안을 불러오지 못했습니다. ${detail}`);
    } finally {
      setLoadingAssistance(false);
      setAssistProgress(null);
    }
  };
  // === ANCHOR: REPORTQUALITYPANEL_REQUESTASSISTANCE_END ===

  // === ANCHOR: REPORTQUALITYPANEL_UPDATESUGGESTION_START ===
  const updateSuggestion = (update: Parameters<typeof reportAssistSuggestionStateUpdate>[1]) => {
    setAssistState((state) => reportAssistSuggestionStateUpdate(state, update));
  };
  // === ANCHOR: REPORTQUALITYPANEL_UPDATESUGGESTION_END ===

  return (
    <section aria-label="보고서 품질 점검" style={panel}>
      <header style={header}>
        <div>
          <div style={eyebrow}>보고서 품질 점검</div>
          <h2 style={title}>{statusLabel(quality.status)}</h2>
        </div>
        <span style={scoreBadge}>{metricText}</span>
      </header>

      <p style={summary}>{quality.summary}</p>
      <p style={nextAction}>{nextActionText ?? defaultNextAction(quality)}</p>

      {longSource !== undefined && longSource.totalLines > 600 && (
        <p style={longSourceNote}>
          {`긴 문서는 관련 섹션 ${longSource.analyzedSections}개만 분석합니다.`}
          <br />
          {`전체 ${longSource.totalLines}줄을 한 번에 보내지 않습니다.`}
        </p>
      )}

      <div style={reviewGrid}>
        <div style={findingList}>
          {quality.findings.length === 0 ? (
            <p style={emptyState}>품질 점검 통과</p>
          ) : (
            groups.map((group) => (
              <section key={group.severity} aria-label={`${group.label} 항목`} style={findingGroupStyle}>
                <h3 style={groupTitle}>{group.label}</h3>
                {quality.findings
                  .filter((finding) => finding.severity === group.severity)
                  .map((finding) => (
                    <article key={`${finding.code}:${finding.message}`} style={findingItem}>
                      <div style={findingHead}>
                        <strong>{finding.categoryLabel}</strong>
                        <span style={severityBadge}>{finding.severity}</span>
                      </div>
                      <p style={findingMessage}>{finding.message}</p>
                      {finding.suggestion !== undefined && <p style={findingSuggestion}>{finding.suggestion}</p>}
                    </article>
                  ))}
              </section>
            ))
          )}
        </div>

        <section aria-label="AI 보완 도움" style={assistBox}>
          <div style={assistHeader}>
            <div>
              <h3 style={assistTitle}>AI 보완 도움</h3>
              <p style={assistCopy}>제안은 수락, 수정, 제외 또는 답변 저장 후에만 적용됩니다.</p>
            </div>
            {onRequestAssistance !== undefined && (
              <div style={assistActions}>
                <label style={providerLabel}>
                  <span>보완 모델</span>
                  <select
                    aria-label="AI 보완 모델"
                    value={visibleAssistProvider}
                    onChange={(event) => onAssistProviderChange?.(normalizeReportAssistProviderId(event.currentTarget.value))}
                    style={providerSelect}
                  >
                    {assistProviderOptions.map((option) => (
                      <option key={option.id} value={option.id}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => void requestAssistance()}
                  onKeyDown={(event) => activateButtonFromKeyboard(event, () => void requestAssistance())}
                  disabled={loadingAssistance}
                  style={secondaryButton}
                >
                  AI 보완 제안 요청
                </button>
              </div>
            )}
          </div>
          {loadingAssistance && (
            <GyariProgressBar
              ariaLabel="AI 보완 생성 진행"
              pct={assistProgress && assistProgress.total > 0 ? 4 + (assistProgress.done / assistProgress.total) * 92 : 8}
              label={
                assistProgress && assistProgress.total > 0
                  ? `보완 제안 분석 중 (${assistProgress.done}/${assistProgress.total})`
                  : "관련 섹션을 분석하는 중"
              }
            />
          )}
          {assistError !== null && (
            <p role="alert" style={errorText}>
              {assistError}
            </p>
          )}
          {items.length > 0 && <ReportQualityScorePreviewView currentScore={quality.score} preview={scorePreview} />}
          {items.map((item) => (
            <ReportQualityAssistItem
              key={item.id}
              item={item}
              sourceLabel={sourceLabel}
              editValue={suggestionEdits[item.id] ?? item.proposed_text}
              answerValue={answerDrafts[item.id] ?? ""}
              answerStatus={answerStatus(item.id, answerDrafts, savedAnswers)}
              selectionStatus={selectionStatus(item.id, assistState)}
              scoreImpact={scoreImpactForFindingCode(quality, item.finding_code)}
              onEditChange={(text) => setSuggestionEdits((drafts) => ({ ...drafts, [item.id]: text }))}
              onAnswerChange={(text) => setAnswerDrafts((drafts) => ({ ...drafts, [item.id]: text }))}
              onAccept={() => updateSuggestion({ type: "accept", suggestionId: item.id, text: item.proposed_text })}
              onEdit={() => updateSuggestion({ type: "edit", suggestionId: item.id, text: suggestionEdits[item.id] ?? item.proposed_text })}
              onReject={() => updateSuggestion({ type: "reject", suggestionId: item.id })}
              onSaveAnswer={() => setSavedAnswers((answers) => ({ ...answers, [item.id]: answerDrafts[item.id] ?? "" }))}
            />
          ))}
        </section>
      </div>

      <div style={footer}>
        <button type="button" onClick={proceed} onKeyDown={(event) => activateButtonFromKeyboard(event, proceed)} disabled={isBlocking} style={primaryButton}>
          {proceedButtonLabel(effectiveStatus, hasAppliedAssistance)}
        </button>
        <button type="button" onClick={onCancel} onKeyDown={(event) => activateButtonFromKeyboard(event, onCancel)} style={secondaryButton}>
          취소
        </button>
      </div>
    </section>
  );
}
// === ANCHOR: REPORTQUALITYPANEL_REPORTQUALITYPANEL_END ===

const panel: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 12, boxShadow: "4px 4px 0 #1A1A1A" };
const header: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" };
const eyebrow: CSSProperties = { fontSize: 11, fontWeight: 800, color: "#999999" };
const title: CSSProperties = { margin: 0, fontSize: 20, lineHeight: 1.2 };
const scoreBadge: CSSProperties = { border: "2px solid #1A1A1A", padding: "4px 8px", fontSize: 12, fontWeight: 800, background: "#FEFBF0" };
const summary: CSSProperties = { margin: "10px 0 0", fontSize: 13, lineHeight: 1.5 };
const nextAction: CSSProperties = { margin: "8px 0 0", fontSize: 13, fontWeight: 800 };
const longSourceNote: CSSProperties = { margin: "8px 0 0", fontSize: 12, lineHeight: 1.5, color: "#1A1A1A" };
const reviewGrid: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 380px), 1fr))", gap: 12, alignItems: "start", marginTop: 12 };
const findingList: CSSProperties = { display: "grid", gap: 8 };
const emptyState: CSSProperties = { margin: 0, fontSize: 13, fontWeight: 800 };
const findingGroupStyle: CSSProperties = { display: "grid", gap: 6 };
const groupTitle: CSSProperties = { margin: 0, fontSize: 12, fontWeight: 900 };
const findingItem: CSSProperties = { border: "1px solid #1A1A1A", padding: 8, background: "#FEFBF0" };
const findingHead: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" };
const severityBadge: CSSProperties = { fontSize: 11, fontWeight: 800, border: "1px solid #1A1A1A", padding: "2px 6px", background: "#FFFFFF" };
const findingMessage: CSSProperties = { margin: "6px 0 0", fontSize: 12, lineHeight: 1.5 };
const findingSuggestion: CSSProperties = { margin: "4px 0 0", fontSize: 12, fontWeight: 800 };
const assistBox: CSSProperties = { display: "grid", gap: 8, borderTop: "2px solid #1A1A1A", paddingTop: 12 };
const assistHeader: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "start", flexWrap: "wrap" };
const assistTitle: CSSProperties = { margin: 0, fontSize: 14, fontWeight: 900 };
const assistCopy: CSSProperties = { margin: "4px 0 0", fontSize: 12, lineHeight: 1.5, color: "#666666" };
const assistActions: CSSProperties = { display: "grid", gap: 6, justifyItems: "end", minWidth: 160 };
const providerLabel: CSSProperties = { display: "grid", gap: 4, fontSize: 11, fontWeight: 900, color: "#1A1A1A" };
const providerSelect: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 8px", fontWeight: 800, minWidth: 132 };
const footer: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 };
const primaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#F5621E", color: "#1A1A1A", padding: "8px 12px", fontWeight: 900, cursor: "pointer" };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "7px 10px", fontWeight: 800, cursor: "pointer" };
const errorText: CSSProperties = { margin: 0, color: "#9B1B1B", fontSize: 12, fontWeight: 800 };
// === ANCHOR: REPORTQUALITYPANEL_END ===
