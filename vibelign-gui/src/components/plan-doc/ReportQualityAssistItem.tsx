import type { CSSProperties } from "react";

import type { ReportAssistSourceRef, ReportAssistSuggestion } from "../../lib/vib/reportAssist";

export type ReportQualityAssistItemProps = {
  readonly item: ReportAssistSuggestion;
  readonly sourceLabel: string;
  readonly editValue: string;
  readonly answerValue: string;
  readonly onEditChange: (text: string) => void;
  readonly onAnswerChange: (text: string) => void;
  readonly onAccept: () => void;
  readonly onEdit: () => void;
  readonly onReject: () => void;
  readonly onSaveAnswer: () => void;
};

function sourceRefLabel(ref: ReportAssistSourceRef, sourceLabel: string): string {
  if (ref.start_line === undefined || ref.end_line === undefined) {
    return ref.warning ?? `${sourceLabel} 범위 확인 필요`;
  }
  return `${sourceLabel} ${ref.start_line}-${ref.end_line}줄`;
}

export function ReportQualityAssistItem(props: ReportQualityAssistItemProps) {
  const { item, sourceLabel } = props;
  const isQuestion = item.kind === "user_question";
  return (
    <article style={assistItem}>
      <div style={row}>
        <strong>{item.title}</strong>
        <span style={kindBadge}>{item.kindLabel}</span>
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
          <div style={buttonRow}>
            <button type="button" onClick={props.onSaveAnswer} style={secondaryButton}>
              {item.title} 답변 저장
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
          <div style={buttonRow}>
            <button type="button" onClick={props.onAccept} style={secondaryButton}>
              {item.title} 수락
            </button>
            <button type="button" onClick={props.onEdit} style={secondaryButton}>
              {item.title} 수정 반영
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

const assistItem: CSSProperties = { border: "1px solid #1A1A1A", padding: 8, background: "#FFFFFF" };
const row: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" };
const kindBadge: CSSProperties = { fontSize: 11, fontWeight: 800, background: "#E8F1FF", border: "1px solid #1A1A1A", padding: "2px 6px" };
const bodyText: CSSProperties = { margin: "6px 0 0", fontSize: 12, lineHeight: 1.5 };
const chipRow: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 };
const lineChip: CSSProperties = { border: "1px solid #1A1A1A", padding: "2px 6px", fontSize: 11, fontWeight: 800, maxWidth: "100%", overflowWrap: "anywhere" };
const questionText: CSSProperties = { margin: "8px 0", fontSize: 13, fontWeight: 800 };
const textarea: CSSProperties = { boxSizing: "border-box", width: "100%", minHeight: 64, border: "2px solid #1A1A1A", padding: 8, fontSize: 13, lineHeight: 1.5 };
const buttonRow: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "7px 10px", fontWeight: 800, cursor: "pointer" };
const ghostButton: CSSProperties = { border: "1px solid #1A1A1A", background: "#FEFBF0", color: "#1A1A1A", padding: "7px 10px", fontWeight: 800, cursor: "pointer" };
