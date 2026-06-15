// === ANCHOR: PLANNINGROOM_MENTIONS_TEST_START ===
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const result = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱 만들고 싶어",
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

describe("PlanningRoom mention chips", () => {
  test("inserts_persona_mentions_into_the_composer", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);
    const composer = screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?");

    // 클로이는 기본 OFF(opt-in, 비활성)라 클릭 불가 → 활성 페르소나(지오)로 멘션 삽입 검증.
    fireEvent.click(screen.getByRole("button", { name: "지오 검토" }));

    expect(composer).toHaveValue("@지오");

    fireEvent.click(screen.getByRole("button", { name: "지오 검토" }));
    fireEvent.click(screen.getByRole("button", { name: "모두" }));

    expect(composer).toHaveValue("@지오 @모두");
  });
});
// === ANCHOR: PLANNINGROOM_MENTIONS_TEST_END ===
