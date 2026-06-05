// === ANCHOR: HOMEPLANNINGENTRY_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { HomePlanningEntry } from "../HomePlanningEntry";

describe("HomePlanningEntry", () => {
  afterEach(() => {
    cleanup();
  });

  test("opens_current_planning_room_again", () => {
    const onOpen = vi.fn();
    render(
      <HomePlanningEntry
        prompt="자동 스크린샷 앱 만들기"
        outputPath="plans/자동-스크린샷-앱-만들기.md"
        isPending={false}
        onOpen={onOpen}
      />,
    );

    expect(screen.getByText("현재 기획안")).toBeInTheDocument();
    expect(screen.getByText("자동 스크린샷 앱 만들기")).toBeInTheDocument();
    expect(screen.getByText("저장 위치: plans/자동-스크린샷-앱-만들기.md")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "기획방으로 돌아가기" }));

    expect(onOpen).toHaveBeenCalledOnce();
  });

  test("keeps_current_planning_entry_compact", () => {
    render(
      <HomePlanningEntry
        prompt="자동 스크린샷 앱 만들기"
        outputPath="plans/자동-스크린샷-앱-만들기.md"
        isPending={false}
        onOpen={vi.fn()}
      />,
    );

    const entry = screen.getByText("현재 기획안").closest("section");
    expect(entry).toHaveStyle({ padding: "10px" });
  });

  test("shows_pending_state", () => {
    render(
      <HomePlanningEntry
        prompt="자동 스크린샷 앱 만들기"
        outputPath={null}
        isPending={true}
        onOpen={vi.fn()}
      />,
    );

    expect(screen.getByText("기획안을 만드는 중...")).toBeInTheDocument();
  });
});
// === ANCHOR: HOMEPLANNINGENTRY_TEST_END ===
