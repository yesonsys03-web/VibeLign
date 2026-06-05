// === ANCHOR: HOME_START_PLANNING_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { GuardResult } from "../../lib/vib";

import Home from "../Home";

const mocks = vi.hoisted(() => ({
  vibGuardMock: vi.fn<(...args: readonly [string]) => Promise<GuardResult>>(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => undefined),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    vibGuard: mocks.vibGuardMock,
  };
});

describe("Home start planning card", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.vibGuardMock.mockReset();
    mocks.vibGuardMock.mockResolvedValue({ status: "pass", summary: "ok", recommendations: [], issues: [] });
  });

  test("shows_start_card_without_existing_planning", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} onStartPlanning={vi.fn()} />);

    expect(screen.getByPlaceholderText("무엇을 만들고 싶나요?")).toBeInTheDocument();
  });

  test("submitting_idea_calls_on_start_planning", () => {
    const onStartPlanning = vi.fn();
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} onStartPlanning={onStartPlanning} />);

    fireEvent.change(screen.getByPlaceholderText("무엇을 만들고 싶나요?"), { target: { value: "예약 앱 만들기" } });
    fireEvent.click(screen.getByRole("button", { name: "시작" }));

    expect(onStartPlanning).toHaveBeenCalledWith("예약 앱 만들기");
  });
});
// === ANCHOR: HOME_START_PLANNING_TEST_END ===
