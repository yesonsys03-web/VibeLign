import { useEffect, useState, type CSSProperties } from "react";

import {
  approvedReportVisualCards,
  type ReportVisualCard,
  type ReportVisualCardsPayload,
} from "../../lib/vib/reportVisualCards";

export type ReportVisualCardsPanelProps = {
  readonly payload: ReportVisualCardsPayload;
  readonly onExportChange?: (cards: readonly ReportVisualCard[]) => void;
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

export function ReportVisualCardsPanel({ payload, onExportChange, onRegenerate }: ReportVisualCardsPanelProps) {
  const [cards, setCards] = useState<readonly ReportVisualCard[]>(payload.cards);
  const [candidateVersions, setCandidateVersions] = useState<Readonly<Record<string, number>>>({});

  useEffect(() => {
    setCards(payload.cards);
    setCandidateVersions({});
  }, [payload]);

  useEffect(() => {
    onExportChange?.(approvedReportVisualCards(cards));
  }, [cards, onExportChange]);

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
        <div>
          <div style={eyebrow}>카드뉴스 companion</div>
          <h2 style={title}>시각 카드 초안</h2>
        </div>
        <span style={providerBadge}>{provider}</span>
      </header>

      <div style={grid}>
        {cards.map((card) => {
          const edit = editFor(card);
          const candidateVersion = candidateVersions[card.id] ?? 1;
          return (
            <article key={card.id} aria-label={`${card.title} 카드`} style={cardBox}>
              <div style={imageLayer}>
                <div
                  aria-label={`${card.id} 이미지 레이어`}
                  data-asset-path={card.image.asset_path}
                  data-candidate-version={candidateVersion}
                  style={assetLayer}
                />
                <div style={overlay}>
                  <input
                    aria-label={`${card.title} 제목 오버레이`}
                    value={edit.title}
                    onChange={(event) => editCard(card.id, { title: event.target.value })}
                    style={titleInput}
                  />
                  <textarea
                    aria-label={`${card.title} 본문 오버레이`}
                    value={edit.body}
                    onChange={(event) => editCard(card.id, { body: event.target.value })}
                    style={bodyInput}
                  />
                  <input
                    aria-label={`${card.title} 캡션 오버레이`}
                    value={edit.caption}
                    onChange={(event) => editCard(card.id, { caption: event.target.value })}
                    style={captionInput}
                  />
                </div>
              </div>
              <p aria-label={`${card.title} 후보 상태`} style={candidateText}>후보 v{candidateVersion}</p>
              <p style={promptText}>{card.visual_prompt}</p>
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

const panel: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 12, boxShadow: "4px 4px 0 #1A1A1A" };
const header: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", marginBottom: 12 };
const eyebrow: CSSProperties = { fontSize: 11, fontWeight: 800, color: "#999999" };
const title: CSSProperties = { margin: 0, fontSize: 20, lineHeight: 1.2 };
const providerBadge: CSSProperties = { border: "2px solid #1A1A1A", padding: "4px 8px", fontSize: 12, fontWeight: 800, background: "#FEFBF0" };
const grid: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 };
const cardBox: CSSProperties = { display: "grid", gap: 8, border: "2px solid #1A1A1A", padding: 8, background: "#FEFBF0" };
const imageLayer: CSSProperties = { minHeight: 260, border: "2px solid #1A1A1A", background: "#FFFFFF", position: "relative", overflow: "hidden" };
const assetLayer: CSSProperties = { position: "absolute", inset: 10, border: "2px solid #1A1A1A", background: "#FEFBF0", boxShadow: "4px 4px 0 #1A1A1A" };
const overlay: CSSProperties = { position: "absolute", inset: 12, display: "grid", alignContent: "end", gap: 8 };
const titleInput: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 8, fontSize: 18, fontWeight: 900 };
const bodyInput: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", padding: 8, minHeight: 74, fontSize: 13, lineHeight: 1.5, resize: "none" };
const captionInput: CSSProperties = { border: "1px solid #1A1A1A", background: "#FFFFFF", padding: 6, fontSize: 12, fontWeight: 800 };
const candidateText: CSSProperties = { margin: 0, fontSize: 11, fontWeight: 800, color: "#1A1A1A" };
const promptText: CSSProperties = { margin: 0, fontSize: 11, lineHeight: 1.4, color: "#666666", overflowWrap: "anywhere" };
const controls: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 6 };
const secondaryButton: CSSProperties = { border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", padding: "6px 9px", fontWeight: 800, cursor: "pointer" };
const approvedButton: CSSProperties = { ...secondaryButton, background: "#4DFF91" };
const dangerButton: CSSProperties = { ...secondaryButton, background: "#FF4D4D" };
