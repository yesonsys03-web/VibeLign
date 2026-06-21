// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_START ===
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import type { ReportVisualCard, ReportVisualCardsPayload } from "../../../lib/vib/reportVisualCards";
import { ReportVisualCardsPanel } from "../ReportVisualCardsPanel";

vi.mock("@tauri-apps/api/core", () => ({ convertFileSrc: (path: string) => `asset://localhost/${encodeURI(path)}` }));

afterEach(cleanup);

const payload: ReportVisualCardsPayload = {
  schema_version: "report-visual-cards-v1",
  status: "ready",
  provider: "provider-neutral-draft",
  cards: [],
  assets: [],
};

// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_CARD_START ===
function card(id: string, title: string, assetPath: string): ReportVisualCard {
  return {
    id,
    title,
    body: `${title} 본문은 한국어 오버레이로 남습니다.`,
    caption: `출처: ${title}`,
    visual_prompt: "2D business comic illustration, no readable text in image",
    negative_prompt: "readable text",
    source_refs: [{ source_plan_path: "plan.md", section: 0, block: 0, heading: title }],
    image: {
      provider: "claude",
      asset_path: assetPath,
      prompt: "search over notes body, no readable text in image",
      generated: true,
    },
    approved: true,
  };
}
// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_CARD_END ===

// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_RENDERASSETCARD_START ===
function renderAssetCard(cwd: string, assetPath: string): void {
  render(<ReportVisualCardsPanel cwd={cwd} payload={{ ...payload, cards: [card("card-1", "본문 전체 검색", assetPath)] }} />);
}
// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_RENDERASSETCARD_END ===

test("renders generated visual asset in draft preview when card has relative asset path", () => {
  renderAssetCard("/proj", ".vibelign/reports/card-news/assets/예약-흐름-card-news/01-예약.svg");

  const summaryCard = screen.getByLabelText("card-1 요약 카드");
  const image = screen.getByRole("img", { name: "본문 전체 검색 생성 이미지" });
  expect(image).toHaveAttribute(
    "src",
    "asset://localhost//proj/.vibelign/reports/card-news/assets/%EC%98%88%EC%95%BD-%ED%9D%90%EB%A6%84-card-news/01-%EC%98%88%EC%95%BD.svg",
  );
  expect(summaryCard.querySelector("[data-sketch-symbols]")).not.toBeInTheDocument();
});

test("converts POSIX absolute generated visual asset path before rendering image", () => {
  const assetPath =
    "/Users/topsphinx/Documents/coding/메모장/.vibelign/reports/card-news/assets/나만의-메모장-card-news/06-본문-전체-검색.svg";
  renderAssetCard("/Users/topsphinx/Documents/coding/메모장", assetPath);

  const image = screen.getByRole("img", { name: "본문 전체 검색 생성 이미지" });
  expect(image).toHaveAttribute("src", `asset://localhost/${encodeURI(assetPath)}`);
  expect(image).not.toHaveAttribute("src", assetPath);
});

test("converts Windows absolute generated visual asset path before rendering image", () => {
  const assetPath =
    "C:\\Users\\topsphinx\\Documents\\coding\\메모장\\.vibelign\\reports\\card-news\\assets\\나만의-메모장-card-news\\06-본문-전체-검색.svg";
  const normalizedAssetPath =
    "C:/Users/topsphinx/Documents/coding/메모장/.vibelign/reports/card-news/assets/나만의-메모장-card-news/06-본문-전체-검색.svg";
  renderAssetCard("C:\\Users\\topsphinx\\Documents\\coding\\메모장", assetPath);

  const image = screen.getByRole("img", { name: "본문 전체 검색 생성 이미지" });
  expect(image).toHaveAttribute("src", `asset://localhost/${encodeURI(normalizedAssetPath)}`);
  expect(image).not.toHaveAttribute("src", assetPath);
});
// === ANCHOR: REPORTVISUALCARDASSETPREVIEW_TEST_END ===
