// === ANCHOR: REPORTVISUALCARDPREVIEW_START ===
import type { CSSProperties } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";

import type { ReportVisualCard } from "../../lib/vib/reportVisualCards";
import { ReportVisualSketch } from "./ReportVisualSketch";

export type ReportVisualCardEdit = {
  readonly title: string;
  readonly body: string;
  readonly caption: string;
};

export type ReportVisualCardPreviewProps = {
  readonly cwd?: string;
  readonly card: ReportVisualCard;
  readonly edit: ReportVisualCardEdit;
  readonly cardNumber: number;
  readonly candidateVersion: number;
  readonly onEdit: (edit: Pick<Partial<ReportVisualCardEdit>, "title" | "caption">) => void;
};

// === ANCHOR: REPORTVISUALCARDPREVIEW_REPORTVISUALCARDPREVIEW_START ===
export function ReportVisualCardPreview({ cwd, card, edit, cardNumber, candidateVersion, onEdit }: ReportVisualCardPreviewProps) {
  const points = bodyLines(edit.body);
  const assetSrc = visualAssetSrc(cwd, card.image.asset_path);
  const sourceBadge =
    card.image.source === "llm" ? { text: "모델 생성", bg: "#4DFF91" }
    : card.image.source === "fallback" ? { text: "폴백 · 모델 실패", bg: "#FFD84D" }
    : { text: "템플릿", bg: "#EEEEEE" };
  return (
    <div aria-label={`${card.id} 요약 카드`} data-candidate-version={candidateVersion} style={summaryCard}>
      <div style={hiddenMeta} aria-label={`${card.id} 카드 메타`} data-asset-path={card.image.asset_path} data-candidate-version={candidateVersion} />
      <div style={panelNo}>{cardNumber}</div>
      <span aria-label={`${card.id} 이미지 출처`} style={{ ...sourceBadgeBase, background: sourceBadge.bg }}>{sourceBadge.text}</span>
      <input
        aria-label={`${card.title} 카드 제목`}
        value={edit.title}
        onChange={(event) => onEdit({ title: event.target.value })}
        style={titleInput}
      />
      <figure style={sketch}>
        {assetSrc === null ? (
          <ReportVisualSketch card={card} />
        ) : (
          <img src={assetSrc} alt={`${card.title} 생성 이미지`} style={assetImage} />
        )}
      </figure>
      <ul style={pointsList}>
        {points.map((item) => (
          <li key={item} style={pointItem}>
            <span style={pointBullet} aria-hidden="true" />
            {item}
          </li>
        ))}
      </ul>
      <input
        aria-label={`${card.title} 출처 문구`}
        value={edit.caption}
        onChange={(event) => onEdit({ caption: event.target.value })}
        style={captionInput}
      />
    </div>
  );
}
// === ANCHOR: REPORTVISUALCARDPREVIEW_REPORTVISUALCARDPREVIEW_END ===

// === ANCHOR: REPORTVISUALCARDPREVIEW_BODYLINES_START ===
function bodyLines(body: string): readonly string[] {
  const rawLines = body.replace("。", ".").split(/\r?\n/).map((line) => line.trim());
  const cleaned = cleanBodyLines(rawLines);
  if (cleaned.length >= 2) return cleaned.slice(0, 4);
  if (body.trim().length > 0) return cleanBodyLines([body.trim()]).slice(0, 4);
  const sentences = body.replace("!", ".").replace("?", ".").split(".").map((item) => item.trim()).filter(Boolean);
  const sentenceLines = cleanBodyLines(sentences);
  return sentenceLines.length > 0 ? sentenceLines.slice(0, 4) : ["요약 내용 없음"];
}
// === ANCHOR: REPORTVISUALCARDPREVIEW_BODYLINES_END ===

// === ANCHOR: REPORTVISUALCARDPREVIEW_CLEANBODYLINES_START ===
function cleanBodyLines(lines: readonly string[]): readonly string[] {
  const cleaned: string[] = [];
  for (const line of lines) {
    for (const item of line.split(" / ")) {
      const text = stripInlineMarkup(item).replace(/^[\s\-•]+|[\s\-•]+$/g, "");
      if (text.length > 0) cleaned.push(text);
    }
  }
  return cleaned;
}
// === ANCHOR: REPORTVISUALCARDPREVIEW_CLEANBODYLINES_END ===

// === ANCHOR: REPORTVISUALCARDPREVIEW_STRIPINLINEMARKUP_START ===
function stripInlineMarkup(value: string): string {
  return value.replaceAll("**", "").replaceAll("__", "");
}
// === ANCHOR: REPORTVISUALCARDPREVIEW_STRIPINLINEMARKUP_END ===

// === ANCHOR: REPORTVISUALCARDPREVIEW_VISUALASSETSRC_START ===
function visualAssetSrc(cwd: string | undefined, assetPath: string): string | null {
  const normalizedAsset = assetPath.trim().replaceAll("\\", "/");
  if (normalizedAsset.length === 0 || hasPathTraversal(normalizedAsset)) return null;
  const fullPath = visualAssetFullPath(cwd, normalizedAsset);
  return fullPath === null ? null : convertFileSrc(fullPath);
}
// === ANCHOR: REPORTVISUALCARDPREVIEW_VISUALASSETSRC_END ===

function visualAssetFullPath(cwd: string | undefined, normalizedAsset: string): string | null {
  if (isAbsoluteProjectCardNewsAssetPath(normalizedAsset)) {
    return normalizedAsset;
  }
  if (cwd === undefined || !normalizedAsset.startsWith(".vibelign/reports/card-news/assets/")) return null;
  const normalizedCwd = cwd.replaceAll("\\", "/").replace(/\/+$/, "");
  return `${normalizedCwd}/${normalizedAsset}`;
}

function isAbsoluteProjectCardNewsAssetPath(path: string): boolean {
  const isAbsolute = path.startsWith("/") || /^[A-Za-z]:\//.test(path);
  return isAbsolute && path.includes("/.vibelign/reports/card-news/assets/");
}

function hasPathTraversal(path: string): boolean {
  return path === ".." || path.startsWith("../") || path.includes("/../") || path.endsWith("/..");
}

const summaryCard: CSSProperties = {
  position: "relative",
  width: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  border: "4px solid #1A1A1A",
  background: "#FFFFFF",
  padding: "20px 18px 16px",
  minHeight: 440,
  display: "grid",
  gridTemplateRows: "auto auto 1fr auto",
  gap: 12,
  boxShadow: "6px 7px 0 #1A1A1A",
};
const hiddenMeta: CSSProperties = { display: "none" };
const panelNo: CSSProperties = { position: "absolute", left: -4, top: -4, minWidth: 52, height: 50, padding: "0 10px", display: "grid", placeItems: "center", background: "#1A1A1A", color: "#FFFFFF", fontSize: 28, fontWeight: 900 };
const titleInput: CSSProperties = { width: "calc(100% - 56px)", minWidth: 0, boxSizing: "border-box", marginLeft: 56, border: "none", background: "#FFFFFF", padding: "0 0 4px", fontSize: 30, lineHeight: 1.1, fontWeight: 900, wordBreak: "keep-all" };
const sketch: CSSProperties = { minWidth: 0, margin: 0, border: "3px solid #1A1A1A", borderRadius: 12, background: "#FFFDF6", minHeight: 132, display: "grid", placeItems: "center", overflow: "hidden" };
const assetImage: CSSProperties = { width: "100%", height: 132, objectFit: "cover", display: "block" };
const pointsList: CSSProperties = { margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 8 };
const pointItem: CSSProperties = { position: "relative", paddingLeft: 22, fontSize: 16, lineHeight: 1.38, fontWeight: 900, wordBreak: "keep-all" };
const pointBullet: CSSProperties = { position: "absolute", left: 0, top: "0.55em", width: 9, height: 9, border: "2px solid #1A1A1A", borderRadius: 999, background: "#FFD84D" };
const captionInput: CSSProperties = { minWidth: 0, boxSizing: "border-box", border: "none", borderTop: "3px solid #1A1A1A", background: "#FFFFFF", padding: "9px 0 0", fontSize: 12, fontWeight: 800, color: "#666666" };
const sourceBadgeBase: CSSProperties = { display: "inline-block", marginLeft: 56, border: "2px solid #1A1A1A", padding: "2px 7px", fontSize: 11, fontWeight: 800 };
// === ANCHOR: REPORTVISUALCARDPREVIEW_END ===
