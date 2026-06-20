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
  return { ...actual, requestReportVisualCards: vi.fn() };
});

import {
  requestReportVisualCards,
  type ReportVisualCard,
  type ReportVisualCardsPayload,
} from "../../../lib/vib/reportVisualCards";
import { ReportComposer } from "../ReportComposer";
import { ReportVisualCardsPanel } from "../ReportVisualCardsPanel";

const mockRequestReportVisualCards = vi.mocked(requestReportVisualCards);

beforeEach(() => {
  vi.clearAllMocks();
  mockRequestReportVisualCards.mockResolvedValue({ ok: true, payload });
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

test("keeps Korean copy as editable overlays", () => {
  const onExportChange = vi.fn<(cards: readonly ReportVisualCard[]) => void>();
  render(<ReportVisualCardsPanel payload={payload} onExportChange={onExportChange} />);

  const imageLayer = screen.getByLabelText("card-1 이미지 레이어");
  expect(imageLayer).toHaveAttribute("data-asset-path", "");
  expect(imageLayer).toHaveAttribute("data-candidate-version", "1");
  expect(imageLayer).not.toHaveTextContent("제안 요약");
  expect(imageLayer.parentElement).not.toHaveStyle({ background: "linear-gradient(135deg, #DDEBFF, #FFE1C8)" });

  const title = screen.getByLabelText("제안 요약 제목 오버레이");
  const body = screen.getByLabelText("제안 요약 본문 오버레이");
  const caption = screen.getByLabelText("제안 요약 캡션 오버레이");
  expect(title).toHaveValue("제안 요약");
  expect(body).toHaveValue("제안 요약 본문은 한국어 오버레이로 남습니다.");
  expect(caption).toHaveValue("출처: 제안 요약");
  expect(screen.getAllByText("2D business comic illustration, no readable text in image")[0]).not.toHaveTextContent(/[가-힣]/);
});

test("production ReportComposer requests and previews visual cards", async () => {
  render(<ReportComposer planPath="plans/p.md" cwd="/proj" layout="inline" onClose={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "카드뉴스 초안 만들기" }));

  await screen.findByText("시각 카드 초안");
  expect(mockRequestReportVisualCards).toHaveBeenCalledWith("/proj", "plans/p.md", "work");
  await waitFor(() => expect(screen.getByText("승인된 카드 1개")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "다음 액션 카드 승인" }));
  await waitFor(() => expect(screen.getByText("승인된 카드 2개")).toBeInTheDocument());
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
  expect(screen.getByLabelText("card-1 이미지 레이어")).toHaveAttribute("data-asset-path", "");
  expect(screen.getByLabelText("card-1 이미지 레이어")).toHaveAttribute("data-candidate-version", "2");
  expect(screen.getByLabelText("제안 요약 후보 상태")).toHaveTextContent("후보 v2");
  expect(screen.getByText(/alternate crop 2/)).not.toHaveTextContent(/[가-힣]/);

  fireEvent.change(screen.getByLabelText("제안 요약 제목 오버레이"), {
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
  expect(screen.queryByLabelText("card-2 이미지 레이어")).not.toBeInTheDocument();
  expect(screen.getByLabelText("수정된 제안 요약 제목 오버레이")).toHaveValue("수정된 제안 요약");
});
