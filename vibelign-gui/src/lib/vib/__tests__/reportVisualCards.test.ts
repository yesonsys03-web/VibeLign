// === ANCHOR: REPORTVISUALCARDS_TEST_START ===
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  approvedReportVisualCards,
  parseReportVisualCardsPayload,
  requestReportVisualCards,
  saveReportVisualCards,
} from "../reportVisualCards";

const mocks = vi.hoisted(() => ({
  runVib: vi.fn(),
  writeReportJsonPayload: vi.fn(),
  removeReportRenderPayload: vi.fn(),
}));

vi.mock("../core", () => ({
  runVib: mocks.runVib,
}));

vi.mock("../reportRenderPayload", () => ({
  writeReportJsonPayload: mocks.writeReportJsonPayload,
  removeReportRenderPayload: mocks.removeReportRenderPayload,
}));

const draftCard = {
  id: "c1",
  title: "제안 요약",
  body: "예약 변경 처리 시간을 줄입니다.",
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
} as const;

// === ANCHOR: REPORTVISUALCARDS_TEST_DRAFTPAYLOAD_START ===
function draftPayload() {
  return {
    schema_version: "report-visual-cards-v1",
    provider: "provider-neutral-draft",
    status: "ready",
    cards: [draftCard],
    assets: [],
  } as const;
}
// === ANCHOR: REPORTVISUALCARDS_TEST_DRAFTPAYLOAD_END ===

describe("report visual cards", () => {
  beforeEach(() => {
    mocks.runVib.mockReset();
    mocks.writeReportJsonPayload.mockReset();
    mocks.removeReportRenderPayload.mockReset();
    mocks.writeReportJsonPayload.mockResolvedValue("/repo/.vibelign/reports/render-payloads/render-payload-1.json");
    mocks.removeReportRenderPayload.mockResolvedValue(undefined);
    mocks.runVib.mockImplementation(async (args: readonly string[]) => {
      if (args[0] === "report-card-news") {
        return {
          stdout: JSON.stringify({
            ok: true,
            html_path: "/repo/.vibelign/reports/card-news/cards.html",
            json_path: "/repo/.vibelign/reports/card-news/cards.json",
            storyboard_path: "/repo/.vibelign/reports/card-news/cards.json",
            prompt_dir: "/repo/.vibelign/reports/card-news/prompts/cards",
            prompt_paths: ["/repo/.vibelign/reports/card-news/prompts/cards/generic-prompt.md"],
            card_count: 1,
          }),
          stderr: "",
        };
      }
      return {
        stdout: JSON.stringify({ ok: true, visual_cards: draftPayload() }),
        stderr: "",
      };
    });
  });

  test("parses provider-neutral draft cards without Korean copy in prompts", () => {
    const payload = parseReportVisualCardsPayload({
      provider: "provider-neutral-draft",
      status: "ready",
      cards: [
        {
          id: "c1",
          title: "제안 요약",
          body: "예약 변경 처리 시간을 줄입니다.",
          caption: "출처: 제안 요약",
          visual_prompt: "2D business comic illustration, no readable text in image",
          negative_prompt: "readable text",
          source_refs: [{ source_plan_path: "plan.md", section: 0, block: 0, heading: "제안 요약" }],
          image: { provider: "provider-neutral-draft", asset_path: "", prompt: "prompt", generated: false, source: "template" },
          approved: true,
        },
      ],
    });

    expect(payload.provider).toBe("provider-neutral-draft");
    expect(payload.cards).toHaveLength(1);
    expect(payload.cards[0].source_refs).toHaveLength(1);
    expect(payload.cards[0].visual_prompt).toContain("no readable text in image");
    expect(payload.cards[0].visual_prompt).not.toMatch(/[가-힣]/);
    expect(approvedReportVisualCards(payload.cards)).toHaveLength(1);
  });

  test("requests visual card sidecar through opt-in CLI flags", async () => {
    const result = await requestReportVisualCards("/repo", "plan.md", "proposal", "opencode");

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.payload.cards[0].image.provider).toBe("provider-neutral-draft");
    expect(result.payload.cards[0].title).toBe("제안 요약");
    expect(mocks.runVib).toHaveBeenCalledWith(
      ["report", "plan.md", "--type", "proposal", "--visual-cards", "--visual-card-cli", "opencode", "--json"],
      "/repo",
    );
  });

  test("saves visual cards through a temporary payload file", async () => {
    const result = await saveReportVisualCards("/repo", draftPayload());

    expect(result).toEqual({
      ok: true,
      htmlPath: "/repo/.vibelign/reports/card-news/cards.html",
      jsonPath: "/repo/.vibelign/reports/card-news/cards.json",
      storyboardPath: "/repo/.vibelign/reports/card-news/cards.json",
      promptDir: "/repo/.vibelign/reports/card-news/prompts/cards",
      promptPaths: ["/repo/.vibelign/reports/card-news/prompts/cards/generic-prompt.md"],
      cardCount: 1,
    });
    expect(mocks.writeReportJsonPayload).toHaveBeenCalledWith("/repo", draftPayload());
    expect(mocks.runVib).toHaveBeenCalledWith(
      ["report-card-news", "/repo/.vibelign/reports/render-payloads/render-payload-1.json", "--json"],
      "/repo",
    );
    expect(mocks.removeReportRenderPayload).toHaveBeenCalledWith(
      "/repo",
      "/repo/.vibelign/reports/render-payloads/render-payload-1.json",
    );
  });

  test("cleans temporary payload when visual card save fails", async () => {
    mocks.runVib.mockResolvedValueOnce({
      stdout: JSON.stringify({ ok: false, error: "승인된 카드가 없습니다." }),
      stderr: "",
    });

    const result = await saveReportVisualCards("/repo", draftPayload());

    expect(result).toEqual({ ok: false, error: "승인된 카드가 없습니다." });
    expect(mocks.removeReportRenderPayload).toHaveBeenCalledWith(
      "/repo",
      "/repo/.vibelign/reports/render-payloads/render-payload-1.json",
    );
  });

  test("parses image.source, defaulting to template", () => {
    const payload = parseReportVisualCardsPayload({
      status: "ready",
      provider: "agy",
      cards: [{ id: "c1", image: { provider: "agy", source: "llm" } }],
    });
    expect(payload.cards[0].image.source).toBe("llm");
    const fallback = parseReportVisualCardsPayload({ status: "ready", cards: [{ id: "c2", image: {} }] });
    expect(fallback.cards[0].image.source).toBe("template");
  });

  test("reports stderr instead of JSON parse errors when card news command is missing", async () => {
    mocks.runVib.mockResolvedValueOnce({
      ok: false,
      stdout: "",
      stderr: "invalid choice: 'report-card-news'",
      exit_code: 2,
    });

    const result = await saveReportVisualCards("/repo", draftPayload());

    expect(result).toEqual({
      ok: false,
      error: "카드뉴스 확정 명령을 현재 설치된 vib에서 찾지 못했어요. VibeLign CLI를 업데이트한 뒤 다시 시도하세요.",
    });
    expect(mocks.removeReportRenderPayload).toHaveBeenCalledWith(
      "/repo",
      "/repo/.vibelign/reports/render-payloads/render-payload-1.json",
    );
  });
});
// === ANCHOR: REPORTVISUALCARDS_TEST_END ===
