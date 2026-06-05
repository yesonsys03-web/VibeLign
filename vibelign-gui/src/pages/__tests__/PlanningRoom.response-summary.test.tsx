// === ANCHOR: PLANNINGROOM_RESPONSE_SUMMARY_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const resultWithFailedPersona = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱 만들고 싶어",
  outputPath: "plans/예약-앱-만들고-싶어.md",
  markdown: "# 예약 앱 만들고 싶어\n\n## 한 줄 목표\n예약 앱 만들고 싶어\n",
  details: "raw stderr",
  messages: [
    {
      id: "msg_1",
      role: "user" as const,
      personaId: null,
      content: "예약 앱 만들고 싶어",
      status: "ok",
      createdAt: "2026-06-03T00:00:00Z",
    },
    {
      id: "msg_chloe",
      role: "assistant" as const,
      personaId: "chloe",
      content: "예약 플로우를 정리했어요.",
      status: "ok",
      createdAt: "2026-06-03T00:00:01Z",
    },
    {
      id: "msg_mina",
      role: "assistant" as const,
      personaId: "mina",
      content: "미나 연결이 실패했어요.",
      status: "failed",
      createdAt: "2026-06-03T00:00:02Z",
    },
  ],
};

describe("PlanningRoom persona response summary", () => {
  afterEach(() => {
    cleanup();
  });

  test("keeps_final_preview_available_when_a_persona_failed", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={resultWithFailedPersona} onBack={vi.fn()} onResultChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "기획안 보기" }));

    expect(screen.getByRole("heading", { name: "예약 앱 만들고 싶어", level: 1 })).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });

  test("summarizes_persona_responses_and_failures", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={resultWithFailedPersona} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByRole("region", { name: "페르소나 응답 요약" })).toBeInTheDocument();
    expect(screen.getByText("클로이 완료")).toBeInTheDocument();
    expect(screen.getByText("미나 실패")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });
});
// === ANCHOR: PLANNINGROOM_RESPONSE_SUMMARY_TEST_END ===
