import { useEffect, useMemo, useState, type CSSProperties } from "react";

import {
  approvedReportVisualCards,
  type ReportVisualCard,
  type ReportVisualCardsPayload,
} from "../../lib/vib/reportVisualCards";

export type ReportVisualCardsPanelProps = {
  readonly payload: ReportVisualCardsPayload;
  readonly onExportChange?: (cards: readonly ReportVisualCard[]) => void;
  readonly onFinalize?: (cards: readonly ReportVisualCard[]) => void;
  readonly onRegenerate?: ReportVisualCardRegenerate;
};

type CardEdit = {
  readonly title: string;
  readonly body: string;
  readonly caption: string;
};

export type ReportVisualCardCandidate = {
  readonly version: number;
  readonly visual_prompt: string;
  readonly image: ReportVisualCard["image"];
};

export type ReportVisualCardRegenerate = (
  cardId: string,
  card: ReportVisualCard,
  nextVersion: number,
) => ReportVisualCardCandidate | undefined;

function editFor(card: ReportVisualCard): CardEdit {
  return { title: card.title, body: card.body, caption: card.caption };
}

function defaultCandidate(card: ReportVisualCard, provider: string, version: number): ReportVisualCardCandidate {
  const visualPrompt = `${card.visual_prompt}, alternate composition candidate ${version}`;
  return {
    version,
    visual_prompt: visualPrompt,
    image: {
      provider,
      asset_path: "",
      prompt: visualPrompt,
      generated: false,
    },
  };
}

function updateCard(
  cards: readonly ReportVisualCard[],
  cardId: string,
  update: (card: ReportVisualCard) => ReportVisualCard,
): readonly ReportVisualCard[] {
  return cards.map((card) => (card.id === cardId ? update(card) : card));
}

export function ReportVisualCardsPanel({ payload, onExportChange, onFinalize, onRegenerate }: ReportVisualCardsPanelProps) {
  const [cards, setCards] = useState<readonly ReportVisualCard[]>(payload.cards);
  const [candidateVersions, setCandidateVersions] = useState<Readonly<Record<string, number>>>({});
  const approvedCards = useMemo(() => approvedReportVisualCards(cards), [cards]);

  useEffect(() => {
    setCards(payload.cards);
    setCandidateVersions({});
  }, [payload]);

  useEffect(() => {
    onExportChange?.(approvedCards);
  }, [approvedCards, onExportChange]);

  const provider = payload.provider || "generic-image-provider";

  const editCard = (cardId: string, edit: Partial<CardEdit>) => {
    setCards((current) => updateCard(current, cardId, (card) => ({ ...card, ...edit })));
  };

  const regenerateCard = (cardId: string) => {
    const card = cards.find((item) => item.id === cardId);
    if (card === undefined) return;
    const nextVersion = (candidateVersions[cardId] ?? 1) + 1;
    const candidate = onRegenerate?.(cardId, card, nextVersion) ?? defaultCandidate(card, provider, nextVersion);
    setCandidateVersions((versions) => ({ ...versions, [cardId]: candidate.version }));
    setCards((current) =>
      updateCard(current, cardId, (card) => ({
        ...card,
        visual_prompt: candidate.visual_prompt,
        image: candidate.image,
      })),
    );
  };

  return (
    <section aria-label="카드뉴스 companion" style={panel}>
      <header style={header}>
        <div style={headerTitleBlock}>
          <div style={eyebrow}>카드뉴스 companion</div>
          <h2 style={title}>요약 카드 초안</h2>
        </div>
        <div style={headerActions}>
          <span style={providerBadge}>{provider}</span>
          <button
            type="button"
            disabled={approvedCards.length === 0}
            onClick={() => onFinalize?.(approvedCards)}
            style={approvedCards.length === 0 ? disabledFinalizeButton : finalizeButton}
          >
            카드뉴스 확정
          </button>
        </div>
      </header>

      <div style={grid}>
        {cards.map((card) => {
          const edit = editFor(card);
          const candidateVersion = candidateVersions[card.id] ?? 1;
          return (
            <article key={card.id} aria-label={`${card.title} 카드`} style={cardBox}>
              <div
                aria-label={`${card.id} 요약 카드`}
                data-candidate-version={candidateVersion}
                style={summaryCard}
              >
                <div style={cardTopline}>
                  <span style={numberBadge}>{candidateVersion}</span>
                  <span style={seriesLabel}>REPORT CARD NEWS</span>
                </div>
                <div style={doodleRow} aria-hidden="true">
                  <span>★</span>
                  <span style={doodleLine} />
                  <span>✦</span>
                </div>
                <div
                  aria-label={`${card.id} 카드 메타`}
                  data-asset-path={card.image.asset_path}
                  data-candidate-version={candidateVersion}
                  style={hiddenMeta}
                />
                <input
                  aria-label={`${card.title} 카드 제목`}
                  value={edit.title}
                  onChange={(event) => editCard(card.id, { title: event.target.value })}
                  style={titleInput}
                />
                <textarea
                  aria-label={`${card.title} 요약 본문`}
                  value={edit.body}
                  onChange={(event) => editCard(card.id, { body: event.target.value })}
                  style={bodyInput}
                />
                <input
                  aria-label={`${card.title} 출처 문구`}
                  value={edit.caption}
                  onChange={(event) => editCard(card.id, { caption: event.target.value })}
                  style={captionInput}
                />
              </div>
              <p aria-label={`${card.title} 후보 상태`} style={candidateText}>후보 v{candidateVersion}</p>
              <p style={promptText}>카드뉴스 요약 포맷 · {card.visual_prompt}</p>
              <div style={controls}>
                <button type="button" aria-label={`${card.title} 카드 재생성`} onClick={() => regenerateCard(card.id)} style={secondaryButton}>
                  재생성
                </button>
                <button
                  type="button"
                  aria-label={`${card.title} 카드 ${card.approved ? "승인 취소" : "승인"}`}
                  onClick={() => setCards((current) => updateCard(current, card.id, (item) => ({ ...item, approved: !item.approved })))}
                  style={card.approved ? approvedButton : secondaryButton}
                >
                  {card.approved ? "승인됨" : "승인"}
                </button>
                <button type="button" aria-label={`${card.title} 카드 삭제`} onClick={() => setCards((current) => current.filter((item) => item.id !== card.id))} style={dangerButton}>
                  삭제
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

const panel: CSSProperties = {
  minWidth: 0,
  maxWidth: "100%",
  boxSizing: "border-box",
  border: "2px solid #1A1A1A",
  background: "#FFFFFF",
  padding: 12,
  boxShadow: "4px 4px 0 #1A1A1A",
};
const header: CSSProperties = { display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12, alignItems: "start", marginBottom: 12 };
const headerTitleBlock: CSSProperties = { flex: "1 1 220px", minWidth: 0 };
const headerActions: CSSProperties = { display: "flex", flexWrap: "wrap", justifyContent: "flex-end", gap: 8 };
const eyebrow: CSSProperties = { fontSize: 11, fontWeight: 800, color: "#999999" };
const title: CSSProperties = { margin: 0, fontSize: 20, lineHeight: 1.2, wordBreak: "keep-all" };
const providerBadge: CSSProperties = { border: "2px solid #1A1A1A", padding: "4px 8px", fontSize: 12, fontWeight: 800, background: "#FEFBF0" };
const grid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
  justifyContent: "stretch",
  alignItems: "start",
  gap: 16,
};
const cardBox: CSSProperties = {
  width: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  display: "grid",
  gap: 8,
  border: "2px solid #1A1A1A",
  padding: 8,
  background: "#FEFBF0",
};
const summaryCard: CSSProperties = {
  width: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  aspectRatio: "4 / 5",
  border: "2px solid #1A1A1A",
  background: "#FFFFFF",
  padding: 14,
  display: "grid",
  gridTemplateRows: "auto auto auto 1fr auto",
  gap: 10,
  boxShadow: "5px 5px 0 #1A1A1A",
  overflow: "hidden",
};
const cardTopline: CSSProperties = { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 };
const numberBadge: CSSProperties = { width: 34, height: 34, display: "inline-flex", alignItems: "center", justifyContent: "center", border: "2px solid #1A1A1A", borderRadius: "999px", background: "#FF4D4D", color: "#FFFFFF", fontWeight: 900, fontSize: 18 };
const seriesLabel: CSSProperties = { border: "2px solid #1A1A1A", padding: "3px 8px", background: "#FEFBF0", fontSize: 10, fontWeight: 900 };
const doodleRow: CSSProperties = { display: "flex", alignItems: "center", gap: 8, color: "#F5621E", fontSize: 16, fontWeight: 900 };
const doodleLine: CSSProperties = { flex: 1, borderTop: "3px solid #1A1A1A" };
const hiddenMeta: CSSProperties = { display: "none" };
const titleInput: CSSProperties = { minWidth: 0, boxSizing: "border-box", border: "none", borderBottom: "4px solid #1A1A1A", background: "#FFFFFF", padding: "4px 0 8px", fontSize: 24, lineHeight: 1.15, fontWeight: 900 };
const bodyInput: CSSProperties = { minWidth: 0, boxSizing: "border-box", border: "2px solid #1A1A1A", borderRadius: 8, background: "#FEFBF0", padding: 12, minHeight: 150, fontSize: 14, lineHeight: 1.6, resize: "none" };
const captionInput: CSSProperties = { minWidth: 0, boxSizing: "border-box", border: "2px solid #1A1A1A", borderRadius: 999, background: "#FFFFFF", padding: "8px 10px", fontSize: 12, fontWeight: 800 };
const candidateText: CSSProperties = { margin: 0, fontSize: 11, fontWeight: 800, color: "#1A1A1A" };
const promptText: CSSProperties = { margin: 0, fontSize: 11, lineHeight: 1.4, color: "#666666", overflowWrap: "anywhere" };
const controls: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer" };
const approvedButton: CSSProperties = { ...secondaryButton, background: "#4DFF91" };
const dangerButton: CSSProperties = { ...secondaryButton, background: "#FF4D4D" };
const finalizeButton: CSSProperties = { ...secondaryButton, background: "#F5621E", boxShadow: "2px 2px 0 #1A1A1A" };
const disabledFinalizeButton: CSSProperties = { ...finalizeButton, opacity: 0.45, cursor: "not-allowed" };
