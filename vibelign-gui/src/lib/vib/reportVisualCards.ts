// === ANCHOR: REPORTVISUALCARDS_START ===
import { runVib, runVibWithProgress } from "./core";
import type { ReportType } from "./report";
import { removeReportRenderPayload, writeReportJsonPayload } from "./reportRenderPayload";

export type ReportVisualCardSourceRef = {
  readonly source_plan_path: string;
  readonly section: number;
  readonly block: number;
  readonly heading: string;
};

export type ReportVisualCardImage = {
  readonly provider: string;
  readonly asset_path: string;
  readonly prompt: string;
  readonly generated: boolean;
  readonly source: "llm" | "fallback" | "template";
};

export type ReportVisualCard = {
  readonly id: string;
  readonly title: string;
  readonly body: string;
  readonly caption: string;
  readonly visual_prompt: string;
  readonly negative_prompt: string;
  readonly source_refs: readonly ReportVisualCardSourceRef[];
  readonly image: ReportVisualCardImage;
  readonly approved: boolean;
};

export type ReportVisualCardsPayload = {
  readonly schema_version: "report-visual-cards-v1";
  readonly status: "ready" | "empty";
  readonly provider: string;
  readonly cards: readonly ReportVisualCard[];
  readonly assets: readonly ReportVisualCardImage[];
  readonly poster_html?: string;
};

export type ReportVisualCardsProviderId = "local" | "claude" | "codex" | "agy" | "opencode";

export type ReportVisualCardsResult =
  | {
      readonly ok: true;
      readonly payload: ReportVisualCardsPayload;
      readonly poster?: { readonly html: string; readonly source: "llm" | "fallback" };
    }
  | { readonly ok: false; readonly error: string };

export type ReportCardNewsExportResult =
  | {
      readonly ok: true;
      readonly htmlPath: string;
      readonly jsonPath: string;
      readonly storyboardPath: string;
      readonly promptDir: string;
      readonly promptPaths: readonly string[];
      readonly cardCount: number;
    }
  | { readonly ok: false; readonly error: string };

// === ANCHOR: REPORTVISUALCARDS_ISRECORD_START ===
function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
// === ANCHOR: REPORTVISUALCARDS_ISRECORD_END ===

// === ANCHOR: REPORTVISUALCARDS_STRINGVALUE_START ===
function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}
// === ANCHOR: REPORTVISUALCARDS_STRINGVALUE_END ===

// === ANCHOR: REPORTVISUALCARDS_NUMBERVALUE_START ===
function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
// === ANCHOR: REPORTVISUALCARDS_NUMBERVALUE_END ===

// === ANCHOR: REPORTVISUALCARDS_BOOLEANVALUE_START ===
function booleanValue(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}
// === ANCHOR: REPORTVISUALCARDS_BOOLEANVALUE_END ===

// === ANCHOR: REPORTVISUALCARDS_RECORDARRAY_START ===
function recordArray(value: unknown): readonly Readonly<Record<string, unknown>>[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord);
}
// === ANCHOR: REPORTVISUALCARDS_RECORDARRAY_END ===

// === ANCHOR: REPORTVISUALCARDS_STRINGARRAY_START ===
function stringArray(value: unknown): readonly string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}
// === ANCHOR: REPORTVISUALCARDS_STRINGARRAY_END ===

// === ANCHOR: REPORTVISUALCARDS_PARSEIMAGE_START ===
function parseImage(value: unknown): ReportVisualCardImage {
  const record = isRecord(value) ? value : {};
  const rawSource = stringValue(record.source);
  const source = rawSource === "llm" || rawSource === "fallback" ? rawSource : "template";
  return {
    provider: stringValue(record.provider),
    asset_path: stringValue(record.asset_path),
    prompt: stringValue(record.prompt),
    generated: booleanValue(record.generated),
    source,
  };
}
// === ANCHOR: REPORTVISUALCARDS_PARSEIMAGE_END ===

// === ANCHOR: REPORTVISUALCARDS_PARSESOURCEREF_START ===
function parseSourceRef(value: unknown): ReportVisualCardSourceRef {
  const record = isRecord(value) ? value : {};
  return {
    source_plan_path: stringValue(record.source_plan_path),
    section: numberValue(record.section),
    block: numberValue(record.block),
    heading: stringValue(record.heading),
  };
}
// === ANCHOR: REPORTVISUALCARDS_PARSESOURCEREF_END ===

// === ANCHOR: REPORTVISUALCARDS_PARSECARD_START ===
function parseCard(value: unknown): ReportVisualCard {
  const record = isRecord(value) ? value : {};
  return {
    id: stringValue(record.id),
    title: stringValue(record.title),
    body: stringValue(record.body),
    caption: stringValue(record.caption),
    visual_prompt: stringValue(record.visual_prompt),
    negative_prompt: stringValue(record.negative_prompt),
    source_refs: recordArray(record.source_refs).map(parseSourceRef),
    image: parseImage(record.image),
    approved: booleanValue(record.approved),
  };
}
// === ANCHOR: REPORTVISUALCARDS_PARSECARD_END ===

// === ANCHOR: REPORTVISUALCARDS_PARSEREPORTVISUALCARDSPAYLOAD_START ===
export function parseReportVisualCardsPayload(value: unknown): ReportVisualCardsPayload {
  const record = isRecord(value) ? value : {};
  const cards = recordArray(record.cards).map(parseCard);
  return {
    schema_version: "report-visual-cards-v1",
    status: record.status === "empty" ? "empty" : "ready",
    provider: stringValue(record.provider) || "generic-image-provider",
    cards,
    assets: recordArray(record.assets).map(parseImage),
  };
}
// === ANCHOR: REPORTVISUALCARDS_PARSEREPORTVISUALCARDSPAYLOAD_END ===

// === ANCHOR: REPORTVISUALCARDS_APPROVEDREPORTVISUALCARDS_START ===
export function approvedReportVisualCards(cards: readonly ReportVisualCard[]): readonly ReportVisualCard[] {
  return cards.filter((card) => card.approved);
}
// === ANCHOR: REPORTVISUALCARDS_APPROVEDREPORTVISUALCARDS_END ===

// === ANCHOR: REPORTVISUALCARDS_REQUESTREPORTVISUALCARDS_START ===
/** Sketch-first progressive preview signals streamed while a card-news job runs. */
export type CardNewsProgress = {
  readonly stage?: string;
  readonly draft?: ReportVisualCardsPayload;
};

export async function requestReportVisualCards(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  provider: ReportVisualCardsProviderId,
  mode: "per-card" | "poster" = "per-card",
  onProgress?: (progress: CardNewsProgress) => void,
): Promise<ReportVisualCardsResult> {
  const args = ["report", planPath, "--type", reportType, "--visual-cards", "--visual-card-cli", provider, "--card-news-mode", mode, "--json"] as const;
  const res = onProgress
    ? await runVibWithProgress(
        [...args],
        cwd,
        undefined,
        (e) => {
          const cn = e.card_news;
          if (isRecord(cn)) {
            const kind = stringValue(cn.kind);
            if (kind === "draft" && isRecord(cn.visual_cards)) {
              onProgress({ draft: parseReportVisualCardsPayload(cn.visual_cards) });
              return;
            }
          }
          if (e.stage) onProgress({ stage: e.stage });
        },
      )
    : await runVib(
        [...args],
        cwd,
      );
  try {
    const raw: unknown = JSON.parse(res.stdout.trim());
    if (!isRecord(raw) || raw.ok !== true) {
      return { ok: false, error: isRecord(raw) ? stringValue(raw.error) || "카드뉴스 생성 실패" : "카드뉴스 생성 실패" };
    }
    return { ok: true, payload: parseReportVisualCardsPayload(raw.visual_cards), poster: parsePoster(raw.card_news_poster) };
  } catch {
    return { ok: false, error: res.stderr.trim() || "카드뉴스 생성 실패" };
  }
}

function parsePoster(value: unknown): { html: string; source: "llm" | "fallback" } | undefined {
  if (!isRecord(value)) return undefined;
  const html = stringValue(value.html);
  if (html.length === 0) return undefined;
  return { html, source: value.source === "fallback" ? "fallback" : "llm" };
}
// === ANCHOR: REPORTVISUALCARDS_REQUESTREPORTVISUALCARDS_END ===

// === ANCHOR: REPORTVISUALCARDS_SAVEREPORTVISUALCARDS_START ===
export async function saveReportVisualCards(
  cwd: string,
  payload: ReportVisualCardsPayload,
): Promise<ReportCardNewsExportResult> {
  const payloadPath = await writeReportJsonPayload(cwd, payload);
  try {
    const res = await runVib(["report-card-news", payloadPath, "--json"], cwd);
    const stdout = res.stdout.trim();
    const stderr = res.stderr.trim();
    if (stdout.length === 0) {
      return { ok: false, error: cardNewsSaveError(stderr) };
    }
    const raw: unknown = JSON.parse(stdout);
    if (!isRecord(raw) || raw.ok !== true) {
      return {
        ok: false,
        error: isRecord(raw) ? stringValue(raw.error) || cardNewsSaveError(stderr) : cardNewsSaveError(stderr),
      };
    }
    const htmlPath = stringValue(raw.html_path);
    const jsonPath = stringValue(raw.json_path);
    if (htmlPath.length === 0 || jsonPath.length === 0) {
      return { ok: false, error: "카드뉴스 저장 결과 경로가 비어 있어요." };
    }
    return {
      ok: true,
      htmlPath,
      jsonPath,
      storyboardPath: stringValue(raw.storyboard_path),
      promptDir: stringValue(raw.prompt_dir),
      promptPaths: stringArray(raw.prompt_paths),
      cardCount: numberValue(raw.card_count),
    };
  } catch (error) {
    if (error instanceof SyntaxError) return { ok: false, error: "카드뉴스 저장 응답을 읽지 못했어요." };
    if (error instanceof Error) return { ok: false, error: error.message || "카드뉴스 저장 실패" };
    throw error;
  } finally {
    await removeReportRenderPayload(cwd, payloadPath);
  }
}
// === ANCHOR: REPORTVISUALCARDS_SAVEREPORTVISUALCARDS_END ===

// === ANCHOR: REPORTVISUALCARDS_CARDNEWSSAVEERROR_START ===
function cardNewsSaveError(stderr: string): string {
  if (stderr.includes("invalid choice: 'report-card-news'")) {
    return "카드뉴스 확정 명령을 현재 설치된 vib에서 찾지 못했어요. VibeLign CLI를 업데이트한 뒤 다시 시도하세요.";
  }
  return stderr || "카드뉴스 저장 실패";
}
// === ANCHOR: REPORTVISUALCARDS_CARDNEWSSAVEERROR_END ===
// === ANCHOR: REPORTVISUALCARDS_END ===
