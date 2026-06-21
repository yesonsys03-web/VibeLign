import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn() }));
vi.mock("@tauri-apps/plugin-opener", () => ({ openPath: vi.fn().mockResolvedValue(undefined) }));
vi.mock("../../../lib/vib/system", () => ({ pickFolder: vi.fn().mockResolvedValue(null) }));
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
import { openPath } from "@tauri-apps/plugin-opener";
import { ReportComposer } from "../ReportComposer";
import { ReportVisualCardsPanel } from "../ReportVisualCardsPanel";

const mockRequestReportVisualCards = vi.mocked(requestReportVisualCards);
const mockSaveReportVisualCards = vi.mocked(saveReportVisualCards);
const mockOpenPath = vi.mocked(openPath);

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

const payload: ReportVisualCardsPayload = {
  schema_version: "report-visual-cards-v1",
  status: "ready",
  provider: "provider-neutral-draft",
  cards: [
    card("card-1", "제안 요약", true),
    card("card-2", "핵심 근거", false),
    card("card-3", "다음 액션", false),
  ],
  assets: [],
};

const noApprovedPayload: ReportVisualCardsPayload = {
  ...payload,
  cards: payload.cards.map((item) => ({ ...item, approved: false })),
};

function card(id: string, title: string, approved: boolean): ReportVisualCard {
  return {
    id,
    title,
    body: `${title} 본문은 한국어 오버레이로 남습니다.`,
    caption: `출처: ${title}`,
    visual_prompt: "2D business comic illustration, no readable text in image",
    negative_prompt: "readable text",
    source_refs: [{ source_plan_path: "plan.md", section: 0, block: 0, heading: title }],
    image: {
      provider: "provider-neutral-draft",
      asset_path: "",
      prompt: "2D business comic illustration, no readable text in image",
      generated: false,
    },
    approved,
  };
}

test("keeps Korean copy as editable summary cards", () => {
  const onExportChange = vi.fn<(cards: readonly ReportVisualCard[]) => void>();
  render(<ReportVisualCardsPanel payload={payload} onExportChange={onExportChange} />);

  const summaryCard = screen.getByLabelText("card-1 요약 카드");
  expect(summaryCard).toHaveAttribute("data-candidate-version", "1");
  expect(summaryCard).toHaveTextContent("1");
  expect(summaryCard.querySelector("[data-sketch-symbols]")).toBeInTheDocument();
  expect(summaryCard).toHaveTextContent("제안 요약 본문은 한국어 오버레이로 남습니다.");

  const title = screen.getByLabelText("제안 요약 카드 제목");
  const body = screen.getByLabelText("제안 요약 요약 본문");
  const caption = screen.getByLabelText("제안 요약 출처 문구");
  expect(title).toHaveValue("제안 요약");
  expect(body).toHaveValue("제안 요약 본문은 한국어 오버레이로 남습니다.");
  expect(caption).toHaveValue("출처: 제안 요약");
  expect(screen.getAllByText(/카드뉴스 요약 포맷/)[0]).toHaveTextContent("2D business comic illustration");
});

test("adapts preview sketch symbols to each plan card content", () => {
  const adaptivePayload: ReportVisualCardsPayload = {
    ...payload,
    cards: [
      {
        ...card("card-1", "일정 알림", true),
        body: "캘린더 날짜마다 반복 알림을 보내고 할일 목록을 확인합니다.",
        visual_prompt: "mobile reminder app with calendar checklist notification",
      },
      {
        ...card("card-2", "결제 정책", true),
        body: "구독 가격과 환불 정책을 보안 인증 뒤에 확인합니다.",
        visual_prompt: "subscription payment policy security screen",
      },
    ],
  };
  render(<ReportVisualCardsPanel payload={adaptivePayload} />);

  expect(screen.getByLabelText("card-1 요약 카드").querySelector("[data-sketch-symbols]")).toHaveAttribute(
    "data-sketch-symbols",
    "calendar,bell,checklist",
  );
  expect(screen.getByLabelText("card-2 요약 카드").querySelector("[data-sketch-symbols]")).toHaveAttribute(
    "data-sketch-symbols",
    "wallet,lock,document",
  );
});

test("production ReportComposer requests and previews visual cards", async () => {
  render(<ReportComposer planPath="plans/p.md" cwd="/proj" layout="inline" onClose={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: "카드뉴스" }));
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByText("요약 카드 초안");
  expect(mockRequestReportVisualCards).toHaveBeenCalledWith("/proj", "plans/p.md", "work");
  await waitFor(() => expect(screen.getByText("승인된 카드 1개")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 확정" }));
  await screen.findByText("카드뉴스 결과물 1장");
  expect(screen.getByText("/proj/.vibelign/reports/card-news/prompts/cards")).toBeInTheDocument();
  expect(mockSaveReportVisualCards).toHaveBeenCalledWith(
    "/proj",
    expect.objectContaining({ cards: [expect.objectContaining({ id: "card-1", approved: true })] }),
  );
  fireEvent.click(screen.getByRole("button", { name: "HTML 열기" }));
  expect(mockOpenPath).toHaveBeenCalledWith("/proj/.vibelign/reports/card-news/cards.html");
  fireEvent.click(screen.getByRole("button", { name: "프롬프트 폴더 열기" }));
  expect(mockOpenPath).toHaveBeenCalledWith("/proj/.vibelign/reports/card-news/prompts/cards");
  fireEvent.click(screen.getByRole("button", { name: "다음 액션 카드 승인" }));
  await waitFor(() => expect(screen.getByText("승인된 카드 2개")).toBeInTheDocument());
});

test("modal ReportComposer keeps the card-news workspace available", async () => {
  render(<ReportComposer planPath="plans/p.md" cwd="/proj" layout="modal" onClose={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: "카드뉴스" }));

  expect(screen.getByRole("button", { name: "카드뉴스 초안 만들기" })).toBeInTheDocument();
});

test("finalizes only approved visual cards", async () => {
  const onFinalize = vi.fn<(cards: readonly ReportVisualCard[]) => void>();
  render(<ReportVisualCardsPanel payload={payload} onFinalize={onFinalize} />);

  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 확정" }));

  expect(onFinalize).toHaveBeenCalledWith([expect.objectContaining({ id: "card-1", approved: true })]);
});

test("does not finalize when no visual cards are approved", () => {
  const onFinalize = vi.fn<(cards: readonly ReportVisualCard[]) => void>();
  render(<ReportVisualCardsPanel payload={noApprovedPayload} onFinalize={onFinalize} />);

  const finalize = screen.getByRole("button", { name: "카드뉴스 확정" });
  expect(finalize).toBeDisabled();
  fireEvent.click(finalize);

  expect(onFinalize).not.toHaveBeenCalled();
});

test("refuses to open card-news HTML outside the project result directory", async () => {
  mockSaveReportVisualCards.mockResolvedValueOnce({
    ok: true,
    htmlPath: "/tmp/outside/cards.html",
    jsonPath: "/tmp/outside/cards.json",
    storyboardPath: "/tmp/outside/cards.json",
    promptDir: "/tmp/outside/prompts/cards",
    promptPaths: ["/tmp/outside/prompts/cards/generic-prompt.md"],
    cardCount: 1,
  });
  render(<ReportComposer planPath="plans/p.md" cwd="/proj" layout="inline" onClose={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: "카드뉴스" }));
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));
  await screen.findByText("요약 카드 초안");
  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 확정" }));
  await screen.findByText("카드뉴스 결과물 1장");
  fireEvent.click(screen.getByRole("button", { name: "HTML 열기" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("현재 프로젝트의 결과물 폴더");
  expect(mockOpenPath).not.toHaveBeenCalled();
});

test("regenerates edits deletes and exports only approved cards", async () => {
  const onExportChange = vi.fn<(cards: readonly ReportVisualCard[]) => void>();
  const onRegenerate = vi.fn((cardId: string, card: ReportVisualCard, nextVersion: number) => {
    const visualPrompt = `${card.visual_prompt}, alternate crop ${nextVersion}`;
    return {
      version: nextVersion,
      visual_prompt: visualPrompt,
      image: {
        provider: "provider-neutral-draft",
        asset_path: "",
        prompt: visualPrompt,
        generated: false,
      },
    };
  });
  render(<ReportVisualCardsPanel payload={payload} onExportChange={onExportChange} onRegenerate={onRegenerate} />);

  fireEvent.click(screen.getByRole("button", { name: "제안 요약 카드 재생성" }));
  expect(onRegenerate).toHaveBeenCalledWith("card-1", expect.objectContaining({ id: "card-1" }), 2);
  expect(screen.getByLabelText("card-1 요약 카드")).toHaveAttribute("data-candidate-version", "2");
  expect(screen.getByLabelText("제안 요약 후보 상태")).toHaveTextContent("후보 v2");
  expect(screen.getByText(/alternate crop 2/)).toHaveTextContent("카드뉴스 요약 포맷");

  fireEvent.change(screen.getByLabelText("제안 요약 카드 제목"), {
    target: { value: "수정된 제안 요약" },
  });
  fireEvent.click(screen.getByRole("button", { name: "핵심 근거 카드 삭제" }));
  fireEvent.click(screen.getByRole("button", { name: "다음 액션 카드 승인" }));

  await waitFor(() => {
    const lastCall = onExportChange.mock.calls.at(-1);
    expect(lastCall?.[0]).toEqual([
      expect.objectContaining({
        id: "card-1",
        title: "수정된 제안 요약",
        visual_prompt: expect.stringContaining("alternate crop 2"),
      }),
      expect.objectContaining({ id: "card-3" }),
    ]);
  });
  expect(screen.queryByLabelText("card-2 요약 카드")).not.toBeInTheDocument();
  expect(screen.getByLabelText("수정된 제안 요약 카드 제목")).toHaveValue("수정된 제안 요약");
});
