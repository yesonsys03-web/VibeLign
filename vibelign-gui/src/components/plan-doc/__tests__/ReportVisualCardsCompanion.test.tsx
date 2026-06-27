// === ANCHOR: REPORTVISUALCARDSCOMPANION_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn() }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
vi.mock("@tauri-apps/api/core", () => ({ convertFileSrc: (path: string) => `asset://localhost/${encodeURI(path)}` }));
vi.mock("../../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
vi.mock("../../../lib/vib/planning-personas", () => ({ probePlanningProviders: vi.fn().mockResolvedValue(["claude", "codex", "agy", "opencode"]) }));
vi.mock("../../../lib/vib/report", () => ({
  copyReportTo: vi.fn(),
  emitReportModel: vi.fn(),
  generatePlanningReport: vi.fn(),
  generateReportOffice: vi.fn(),
  generateReportPdf: vi.fn(),
  getReportExportDir: vi.fn(),
  renderReportFileWithDecisions: vi.fn(),
  renderReportHtmlWithDecisions: vi.fn(),
  requestReportAssistance: vi.fn(),
  setReportExportDir: vi.fn(),
}));
vi.mock("../PdfPreview", () => ({ PdfPreview: () => null }));
vi.mock("../../../lib/vib/reportVisualCards", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/vib/reportVisualCards")>();
  return { ...actual, requestReportVisualCards: vi.fn(), saveReportVisualCards: vi.fn() };
});

import {
  requestReportVisualCards,
  saveReportVisualCards,
  type ReportVisualCard,
  type ReportVisualCardsPayload,
} from "../../../lib/vib/reportVisualCards";
import { ReportVisualCardsCompanion } from "../ReportVisualCardsCompanion";

const mockRequestReportVisualCards = vi.mocked(requestReportVisualCards);
const mockSaveReportVisualCards = vi.mocked(saveReportVisualCards);

const payload: ReportVisualCardsPayload = {
  schema_version: "report-visual-cards-v1",
  status: "ready",
  provider: "provider-neutral-draft",
  cards: [
    {
      id: "card-1",
      title: "제안 요약",
      body: "제안 요약 본문",
      caption: "출처: 제안 요약",
      visual_prompt: "2D business comic illustration, no readable text in image",
      negative_prompt: "readable text",
      source_refs: [{ source_plan_path: "plan.md", section: 0, block: 0, heading: "제안 요약" }],
      image: {
        provider: "provider-neutral-draft",
        asset_path: "",
        prompt: "2D business comic illustration, no readable text in image",
        generated: false,
        source: "template",
      },
      approved: true,
    },
  ],
  assets: [],
};

const defaultProps = {
  cwd: "/proj",
  planPath: "plans/p.md",
  reportType: "work" as const,
  provider: "claude" as const,
  providerOptions: [{ id: "claude" as const, label: "Claude" }],
  onProviderChange: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  mockRequestReportVisualCards.mockResolvedValue({ ok: true, payload });
  mockSaveReportVisualCards.mockResolvedValue({
    ok: true,
    htmlPath: "/proj/.vibelign/reports/card-news/cards.html",
    jsonPath: "/proj/.vibelign/reports/card-news/cards.json",
    storyboardPath: "/proj/.vibelign/reports/card-news/cards.json",
    promptDir: "/proj/.vibelign/reports/card-news/prompts/cards",
    promptPaths: ["/proj/.vibelign/reports/card-news/prompts/cards/generic-prompt.md"],
    cardCount: 1,
  });
});

afterEach(cleanup);

test("renders mode select next to model select", () => {
  render(<ReportVisualCardsCompanion {...defaultProps} />);
  expect(screen.getByLabelText("카드뉴스 생성 방식")).toBeInTheDocument();
  expect(screen.getByLabelText("카드뉴스 초안 모델")).toBeInTheDocument();
});

test("mode select is disabled while loading", async () => {
  let resolve: (v: unknown) => void;
  mockRequestReportVisualCards.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ReportVisualCardsCompanion {...defaultProps} />);

  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  expect(screen.getByLabelText("카드뉴스 생성 방식")).toBeDisabled();
  resolve!({ ok: false, error: "cancelled" });
});

test("renders sandboxed poster preview when requestReportVisualCards returns a poster", async () => {
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: "<html><body>poster</body></html>", source: "llm" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  const iframe = await screen.findByTitle("카드뉴스 포스터 프리뷰");
  expect(iframe).toBeInTheDocument();
  expect(iframe.getAttribute("sandbox")).toBe("");
  expect(screen.getByText(/모델 생성/)).toBeInTheDocument();
});

test("shows 폴백 badge when poster source is fallback", async () => {
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: "<html><body>fallback poster</body></html>", source: "fallback" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByTitle("카드뉴스 포스터 프리뷰");
  expect(screen.getByText(/폴백/)).toBeInTheDocument();
});

test("switching the model clears the result generated with the previous model", async () => {
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: "<html><body>poster</body></html>", source: "llm" },
  });

  const { rerender } = render(<ReportVisualCardsCompanion {...defaultProps} provider="claude" />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  await screen.findByTitle("카드뉴스 포스터 프리뷰");

  // Changing the model must drop the stale poster made with the previous model, not keep showing it.
  rerender(<ReportVisualCardsCompanion {...defaultProps} provider="opencode" />);
  await waitFor(() => expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument());
});

test("switching the card-news mode clears the result made in the other mode", async () => {
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: "<html><body>poster</body></html>", source: "llm" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  // Generate in poster mode → poster shows.
  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "poster" } });
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  await screen.findByTitle("카드뉴스 포스터 프리뷰");

  // Switching to per-card must drop the poster-mode result, not show it under the new mode.
  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "per-card" } });
  await waitFor(() => expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument());
});

test("after switching models, the old poster is not shown while the new generation is running", async () => {
  // 1) Generate with model A → its poster shows.
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: "<html><body>deepseek poster</body></html>", source: "llm" },
  });
  const { rerender } = render(<ReportVisualCardsCompanion {...defaultProps} provider="opencode" />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  await screen.findByTitle("카드뉴스 포스터 프리뷰");

  // 2) Switch to model B → stale poster clears.
  rerender(<ReportVisualCardsCompanion {...defaultProps} provider="agy" />);
  await waitFor(() => expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument());

  // 3) Start a new (pending) generation — the old poster must stay gone while it runs.
  let resolveSecond!: (v: unknown) => void;
  mockRequestReportVisualCards.mockReturnValue(new Promise((r) => { resolveSecond = r; }));
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument();
  resolveSecond({ ok: true, payload, poster: { html: "<html><body>agy poster</body></html>", source: "llm" } });
});

test("passes mode arg to requestReportVisualCards", async () => {
  render(<ReportVisualCardsCompanion {...defaultProps} />);

  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "poster" } });
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await waitFor(() =>
    expect(mockRequestReportVisualCards).toHaveBeenCalledWith("/proj", "plans/p.md", "work", "claude", "poster", expect.any(Function)),
  );
});

test("includes poster_html in saveReportVisualCards payload when poster exists", async () => {
  const posterHtml = "<html><body>poster</body></html>";
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: posterHtml, source: "llm" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  await screen.findByTitle("카드뉴스 포스터 프리뷰");

  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 확정" }));
  await waitFor(() =>
    expect(mockSaveReportVisualCards).toHaveBeenCalledWith(
      "/proj",
      expect.objectContaining({ poster_html: posterHtml }),
    ),
  );
});

test("does not show poster preview when no poster returned", async () => {
  mockRequestReportVisualCards.mockResolvedValue({ ok: true, payload });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByText("승인된 카드 1개");
  expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument();
});

test("poster mode: hides cards panel and shows poster iframe and 확정 button", async () => {
  const posterHtml = "<html><body>poster only</body></html>";
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: posterHtml, source: "llm" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "poster" } });
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  const iframe = await screen.findByTitle("카드뉴스 포스터 프리뷰");
  expect(iframe).toBeInTheDocument();

  // Cards panel must NOT be rendered in poster mode
  expect(screen.queryByText("요약 카드 초안")).not.toBeInTheDocument();
  expect(screen.queryByText(/승인된 카드 \d+개/)).not.toBeInTheDocument();

  // 확정 button must be present and enabled
  const finalizeBtn = screen.getByRole("button", { name: "카드뉴스 확정" });
  expect(finalizeBtn).toBeInTheDocument();
  expect(finalizeBtn).not.toBeDisabled();
});

test("poster mode: clicking 확정 calls saveReportVisualCards with all cards approved and poster_html", async () => {
  const posterHtml = "<html><body>poster save test</body></html>";
  mockRequestReportVisualCards.mockResolvedValue({
    ok: true,
    payload,
    poster: { html: posterHtml, source: "llm" },
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "poster" } });
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByTitle("카드뉴스 포스터 프리뷰");

  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 확정" }));

  await waitFor(() =>
    expect(mockSaveReportVisualCards).toHaveBeenCalledWith(
      "/proj",
      expect.objectContaining({
        poster_html: posterHtml,
        cards: payload.cards.map((c) => ({ ...c, approved: true })),
      }),
    ),
  );
});

test("per-card mode: cards panel IS rendered (regression)", async () => {
  mockRequestReportVisualCards.mockResolvedValue({ ok: true, payload });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  // default mode is per-card — do not change mode select
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByText("승인된 카드 1개");
  // ReportVisualCardsPanel renders the section; at minimum the count line is present
  expect(screen.getByText("승인된 카드 1개")).toBeInTheDocument();
});

test("poster mode with no poster: shows hint instead of cards panel", async () => {
  mockRequestReportVisualCards.mockResolvedValue({ ok: true, payload });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.change(screen.getByLabelText("카드뉴스 생성 방식"), { target: { value: "poster" } });
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByText(/포스터 모드는 모델/);
  expect(screen.queryByTitle("카드뉴스 포스터 프리뷰")).not.toBeInTheDocument();
  expect(screen.queryByText(/승인된 카드 \d+개/)).not.toBeInTheDocument();
});

test("shows progress bar with gyari-loader and stage label while loading, hides when done", async () => {
  let resolveRequest!: (v: unknown) => void;
  let capturedOnProgress!: (progress: { stage?: string }) => void;

  mockRequestReportVisualCards.mockImplementation((_cwd, _planPath, _reportType, _provider, _mode, onProgress) => {
    capturedOnProgress = onProgress as (progress: { stage?: string }) => void;
    return new Promise((resolve) => { resolveRequest = resolve; });
  });

  render(<ReportVisualCardsCompanion {...defaultProps} />);
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  // Before onProgress fires, progress container should be visible (loading=true)
  expect(screen.getByLabelText("카드뉴스 생성 진행")).toBeInTheDocument();

  // Fire a stage event to simulate the backend progress signal
  capturedOnProgress({ stage: "assets" });

  // Progress container still visible, gyari-loader present, label shows "카드 이미지"
  await waitFor(() => expect(screen.getByLabelText("카드뉴스 생성 진행")).toBeInTheDocument());
  expect(document.querySelector(".gyari-loader")).toBeInTheDocument();
  expect(screen.getByText(/카드 이미지/)).toBeInTheDocument();

  // Resolve the request — loading ends, progress bar disappears
  resolveRequest({ ok: true, payload });
  await waitFor(() => expect(screen.queryByLabelText("카드뉴스 생성 진행")).not.toBeInTheDocument());
});
// === ANCHOR: REPORTVISUALCARDSCOMPANION_TEST_END ===
