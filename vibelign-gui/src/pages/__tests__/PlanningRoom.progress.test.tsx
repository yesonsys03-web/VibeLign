// === ANCHOR: PLANNINGROOM_PROGRESS_TEST_START ===
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

describe("PlanningRoom persona progress summary", () => {
  test("shows_persona_progress_summary_from_message_metadata", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={{
          ok: true,
          sessionId: "chat_1",
          prompt: "예약 앱 만들고 싶어",
          messages: [
            {
              id: "msg_1",
              role: "user",
              personaId: null,
              content: "예약 앱 만들고 싶어",
              status: "ok",
              createdAt: "2026-06-03T00:00:00Z",
            },
            {
              id: "msg_gio",
              role: "assistant",
              personaId: "gio",
              content: "지오가 답변을 준비하고 있어요.",
              status: "pending",
              createdAt: "2026-06-03T00:00:01Z",
            },
            {
              id: "msg_mina",
              role: "assistant",
              personaId: "mina",
              content: "미나 호출이 실패했어요.",
              status: "failed",
              createdAt: "2026-06-03T00:00:02Z",
            },
          ],
        }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("status", { name: "페르소나 진행" })).toBeInTheDocument();
    expect(screen.getByLabelText("클로이 준비됨")).toBeInTheDocument();
    expect(screen.getByLabelText("지오 검토 중")).toBeInTheDocument();
    expect(screen.getByLabelText("미나 실패")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });
});
// === ANCHOR: PLANNINGROOM_PROGRESS_TEST_END ===
