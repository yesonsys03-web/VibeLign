import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const resultWithBackendStatuses = {
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
    {
      id: "msg_chloe",
      role: "assistant" as const,
      personaId: "chloe",
      content: "클로이 연결이 필요해요.",
      status: "not_installed",
      createdAt: "2026-06-03T00:00:01Z",
    },
    {
      id: "msg_mina",
      role: "assistant" as const,
      personaId: "mina",
      content: "미나는 이번 실행에서 건너뛰었어요.",
      status: "timeout",
      createdAt: "2026-06-03T00:00:02Z",
    },
  ],
};

describe("PlanningRoom persona status labels", () => {
  test("maps_backend_status_codes_to_user_facing_persona_states", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={resultWithBackendStatuses} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByLabelText("클로이 연결 필요")).toBeInTheDocument();
    expect(screen.getByLabelText("미나 건너뜀")).toBeInTheDocument();
    expect(screen.getByText("클로이 연결 필요")).toBeInTheDocument();
    expect(screen.getByText("미나 건너뜀")).toBeInTheDocument();
    expect(screen.queryByText("not_installed")).not.toBeInTheDocument();
    expect(screen.queryByText("timeout")).not.toBeInTheDocument();
  });
});
