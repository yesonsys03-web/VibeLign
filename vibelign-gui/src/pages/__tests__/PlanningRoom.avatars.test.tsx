import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

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

describe("PlanningRoom persona avatars", () => {
  afterEach(() => {
    cleanup();
  });

  test("keeps_existing_persona_progress_labels_visible", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByLabelText("클로이 준비됨")).toBeInTheDocument();
    expect(screen.getByLabelText("지오 준비됨")).toBeInTheDocument();
    expect(screen.getByLabelText("미나 준비됨")).toBeInTheDocument();
  });

  test("shows_three_static_persona_avatars_in_the_progress_summary", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByRole("img", { name: "클로이 아바타" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "지오 아바타" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "미나 아바타" })).toBeInTheDocument();
  });
});
