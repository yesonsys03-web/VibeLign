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

    fireEvent.click(screen.getByRole("button", { name: "클로이 설계" }));

    expect(composer).toHaveValue("@클로이");

    fireEvent.click(screen.getByRole("button", { name: "클로이 설계" }));
    fireEvent.click(screen.getByRole("button", { name: "모두" }));

    expect(composer).toHaveValue("@클로이 @모두");
  });
});
// === ANCHOR: PLANNINGROOM_MENTIONS_TEST_END ===
