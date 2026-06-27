// === ANCHOR: REPORTQUALITYASSISTITEM_START ===
import type { CSSProperties } from "react";

import type { ReportAssistSourceRef, ReportAssistSuggestion } from "../../lib/vib/reportAssist";

export type ReportQualityAssistItemProps = {
  readonly item: ReportAssistSuggestion;
  readonly sourceLabel: string;
  readonly editValue: string;
  readonly answerValue: string;
  readonly answerStatus: "idle" | "saved" | "changed";
  readonly selectionStatus: "idle" | "selected" | "rejected";
  readonly scoreImpact: number;
  readonly onEditChange: (text: string) => void;
  readonly onAnswerChange: (text: string) => void;
  readonly onAccept: () => void;
  readonly onEdit: () => void;
  readonly onReject: () => void;
  readonly onSaveAnswer: () => void;
};

// === ANCHOR: REPORTQUALITYASSISTITEM_SOURCEREFLABEL_START ===
function sourceRefLabel(ref: ReportAssistSourceRef, sourceLabel: string): string {
  if (ref.start_line === undefined || ref.end_line === undefined) {
    return ref.warning ?? `${sourceLabel} 범위 확인 필요`;
  }
  return `${sourceLabel} ${ref.start_line}-${ref.end_line}줄`;
}
// === ANCHOR: REPORTQUALITYASSISTITEM_SOURCEREFLABEL_END ===

// === ANCHOR: REPORTQUALITYASSISTITEM_REPORTQUALITYASSISTITEM_START ===
export function ReportQualityAssistItem(props: ReportQualityAssistItemProps) {
  const { item, sourceLabel } = props;
  const isQuestion = item.kind === "user_question";
  const selectionStatusText = props.selectionStatus === "selected"
    ? "선택한 제안입니다."
    : props.selectionStatus === "rejected"
      ? "제외한 제안입니다."
      : null;
  const answerStatusText = props.answerStatus === "saved"
    ? "답변이 저장되었습니다."
    : props.answerStatus === "changed"
      ? "저장 후 내용이 변경되었습니다."
      : null;
  return (
    <article style={assistItem}>
      <div style={row}>
        <strong>{item.title}</strong>
        <span style={badgeRow}>
          {props.scoreImpact > 0 && <span style={scoreBadge}>예상 +{props.scoreImpact}점</span>}
          <span style={kindBadge}>{item.kindLabel}</span>
        </span>
      </div>
      <p style={bodyText}>{item.rationale}</p>
      {item.source_refs.length > 0 && (
        <div aria-label={`${item.title} 출처`} style={chipRow}>
          {item.source_refs.map((ref) => (
            <span key={`${ref.chunk_id}:${sourceRefLabel(ref, sourceLabel)}`} style={lineChip}>
              {sourceRefLabel(ref, sourceLabel)}
            </span>
          ))}
        </div>
      )}
      {isQuestion ? (
        <>
          <p style={questionText}>{item.proposed_text}</p>
          <textarea
            aria-label={`${item.title} 답변`}
            value={props.answerValue}
            onChange={(event) => props.onAnswerChange(event.target.value)}
            style={textarea}
          />
          {answerStatusText !== null && (
            <p role="status" aria-live="polite" style={answerStatus}>
              {answerStatusText}
            </p>
          )}
          <div style={buttonRow}>
            <button type="button" onClick={props.onSaveAnswer} style={secondaryButton}>
              {props.answerStatus === "saved" ? `${item.title} 답변 다시 저장` : `${item.title} 답변 저장`}
            </button>
            <button type="button" onClick={props.onReject} style={ghostButton}>
              {item.title} 제외
            </button>
          </div>
        </>
      ) : (
        <>
          <textarea
            aria-label={`${item.title} 편집`}
            value={props.editValue}
            onChange={(event) => props.onEditChange(event.target.value)}
            style={textarea}
          />
          {selectionStatusText !== null && <p style={selectionStatus}>{selectionStatusText}</p>}
          <div style={buttonRow}>
            <button type="button" onClick={props.onAccept} style={secondaryButton}>
              {props.selectionStatus === "selected" ? `${item.title} 수락됨` : `${item.title} 수락`}
            </button>
            <button type="button" onClick={props.onEdit} style={secondaryButton}>
              {props.selectionStatus === "selected" ? `${item.title} 수정 다시 반영` : `${item.title} 수정 반영`}
            </button>
            <button type="button" onClick={props.onReject} style={ghostButton}>
              {item.title} 제외
            </button>
          </div>
        </>
      )}
    </article>
  );
}
// === ANCHOR: REPORTQUALITYASSISTITEM_REPORTQUALITYASSISTITEM_END ===

const assistItem: CSSProperties = { border: "1px solid #1A1A1A", padding: 8, background: "#FFFFFF" };
const row: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" };
const badgeRow: CSSProperties = { display: "flex", flexWrap: "wrap", justifyContent: "flex-end", gap: 6 };
const scoreBadge: CSSProperties = { fontSize: 11, fontWeight: 900, background: "var(--green)", border: "1px solid #1A1A1A", padding: "2px 6px" };
const kindBadge: CSSProperties = { fontSize: 11, fontWeight: 800, background: "#E8F1FF", border: "1px solid #1A1A1A", padding: "2px 6px" };
const bodyText: CSSProperties = { margin: "6px 0 0", fontSize: 12, lineHeight: 1.5 };
const chipRow: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 };
const lineChip: CSSProperties = { border: "1px solid #1A1A1A", padding: "2px 6px", fontSize: 11, fontWeight: 800, maxWidth: "100%", overflowWrap: "anywhere" };
const questionText: CSSProperties = { margin: "8px 0", fontSize: 13, fontWeight: 800 };
const textarea: CSSProperties = { boxSizing: "border-box", width: "100%", minHeight: 64, border: "2px solid #1A1A1A", padding: 8, fontSize: 13, lineHeight: 1.5 };
const selectionStatus: CSSProperties = { margin: "8px 0 0", fontSize: 12, fontWeight: 800, color: "var(--black)" };
const answerStatus: CSSProperties = { margin: "8px 0 0", fontSize: 12, fontWeight: 800, color: "var(--black)" };
const buttonRow: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "7px 10px", fontWeight: 800, cursor: "pointer" };
const ghostButton: CSSProperties = { border: "1px solid #1A1A1A", background: "#FEFBF0", color: "#1A1A1A", padding: "7px 10px", fontWeight: 800, cursor: "pointer" };
// === ANCHOR: REPORTQUALITYASSISTITEM_END ===
