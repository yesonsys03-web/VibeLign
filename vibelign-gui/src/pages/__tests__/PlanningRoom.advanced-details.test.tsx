// === ANCHOR: PLANNINGROOM_ADVANCED_DETAILS_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const successfulResultWithDetails = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱 만들고 싶어",
  outputPath: "plans/예약-앱-만들고-싶어.md",
  markdown: "# 예약 앱 만들고 싶어\n",
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
  ],
};

const failedResultWithDetails = {
  ok: false,
  sessionId: null,
  prompt: null,
  messages: [],
  message: "기획방 대화를 준비하지 못했어요.",
  details: "raw stderr",
};

describe("PlanningRoom advanced details", () => {
  afterEach(() => {
    cleanup();
  });

  test("reveals_success_details_only_after_expanding_advanced_details", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={successfulResultWithDetails} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "고급 상세 보기" }));

    expect(screen.getByText("raw stderr")).toBeVisible();
    expect(screen.getByText("문제 원인을 확인할 때만 펼쳐보세요.")).toBeInTheDocument();
  });

  test("reveals_failure_details_only_after_expanding_advanced_details", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={failedResultWithDetails} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByText("기획방 대화를 준비하지 못했어요.")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "고급 상세 보기" }));

    expect(screen.getByText("raw stderr")).toBeVisible();
  });
});
// === ANCHOR: PLANNINGROOM_ADVANCED_DETAILS_TEST_END ===
