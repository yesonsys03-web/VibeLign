import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { PlanningChatMessage } from "../../lib/vib";
import { PlanningMessages } from "./PlanningMessages";

describe("PlanningMessages status badges", () => {
  test("renders_persona_status_badges_without_tagging_user_messages", () => {
    const messages: readonly PlanningChatMessage[] = [
      {
        id: "user_1",
        role: "user",
        personaId: null,
        content: "예약 앱 만들고 싶어",
        status: "ok",
        createdAt: "2026-06-03T00:00:00Z",
      },
      {
        id: "gio_pending",
        role: "assistant",
        personaId: "gio",
        content: "지오가 답변을 준비하고 있어요.",
        status: "pending",
        createdAt: "2026-06-03T00:00:01Z",
      },
      {
        id: "chloe_ok",
        role: "assistant",
        personaId: "chloe",
        content: "초안을 구조화했어요.",
        status: "ok",
        createdAt: "2026-06-03T00:00:02Z",
      },
      {
        id: "mina_failed",
        role: "assistant",
        personaId: "mina",
        content: "미나 호출이 실패했어요.",
        status: "failed",
        createdAt: "2026-06-03T00:00:03Z",
      },
    ];

    render(<PlanningMessages messages={messages} outputPath={null} />);

    expect(screen.getByText("지오")).toBeInTheDocument();
    expect(screen.getByText("준비 중")).toBeInTheDocument();
    expect(screen.getByText("완료")).toBeInTheDocument();
    expect(screen.getByText("실패")).toBeInTheDocument();
    expect(screen.queryByText("사용자 완료")).not.toBeInTheDocument();
  });
});
