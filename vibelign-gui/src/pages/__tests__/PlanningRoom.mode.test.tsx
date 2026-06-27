// === ANCHOR: PLANNINGROOM_MODE_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

describe("PlanningRoom mode selector", () => {
  afterEach(() => {
    cleanup();
  });

  test("keeps_draft_mode_mapped_to_chloe_by_default", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "클로이 설계" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "지오 검토" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "미나 탐색" })).toHaveAttribute("aria-pressed", "false");
  });

  test("maps_mode_selection_to_persona_chips", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("응답 모드"), { target: { value: "full" } });

    expect(screen.getByLabelText("응답 모드")).toHaveValue("full");
    // 클로이(claude)는 기본 OFF(opt-in)라 "전체"에도 선택되지 않는다 — 과금 회피.
    expect(screen.getByRole("button", { name: "클로이 설계" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "지오 검토" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "미나 탐색" })).toHaveAttribute("aria-pressed", "true");
  });
});
// === ANCHOR: PLANNINGROOM_MODE_TEST_END ===
