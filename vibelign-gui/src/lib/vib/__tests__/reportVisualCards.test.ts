import { describe, expect, test, vi } from "vitest";

import {
  approvedReportVisualCards,
  parseReportVisualCardsPayload,
  requestReportVisualCards,
} from "../reportVisualCards";

vi.mock("../core", () => ({
  runVib: vi.fn(async () => ({
    stdout: JSON.stringify({
      ok: true,
      visual_cards: {
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
            image: {
              provider: "provider-neutral-draft",
              asset_path: "",
              prompt: "2D business comic illustration, no readable text in image",
              generated: false,
            },
            approved: true,
          },
        ],
        assets: [],
      },
    }),
    stderr: "",
  })),
}));

describe("report visual cards", () => {
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
          image: { provider: "provider-neutral-draft", asset_path: "", prompt: "prompt", generated: false },
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
    const result = await requestReportVisualCards("/repo", "plan.md", "proposal");

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.payload.cards[0].image.provider).toBe("provider-neutral-draft");
    expect(result.payload.cards[0].title).toBe("제안 요약");
  });
});
