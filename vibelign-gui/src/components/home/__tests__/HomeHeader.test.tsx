// === ANCHOR: HOMEHEADER_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { HomeHeader } from "../HomeHeader";

describe("HomeHeader", () => {
  afterEach(() => {
    cleanup();
  });

  test("shows_home_title_and_version_badge", () => {
    render(<HomeHeader version="2.2.25" advancedOpen={false} onResetOrder={() => undefined} onShowSimple={() => undefined} />);

    expect(screen.getByText("HOME")).toBeInTheDocument();
    expect(screen.getByText("바이브라인")).toBeInTheDocument();
    expect(screen.getByText("v2.2.25")).toBeInTheDocument();
  });

  test("shows_reset_button_only_when_advanced_home_is_open", () => {
    const resetOrder = vi.fn();
    const { rerender } = render(<HomeHeader version="2.2.25" advancedOpen={false} onResetOrder={resetOrder} onShowSimple={() => undefined} />);

    expect(screen.queryByRole("button", { name: "카드 순서 초기화" })).not.toBeInTheDocument();

    rerender(<HomeHeader version="2.2.25" advancedOpen onResetOrder={resetOrder} onShowSimple={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: "카드 순서 초기화" }));
    expect(resetOrder).toHaveBeenCalledOnce();
  });

  test("returns_to_simple_home_when_advanced_home_is_open", () => {
    const showSimple = vi.fn();

    render(<HomeHeader version="2.2.25" advancedOpen onResetOrder={() => undefined} onShowSimple={showSimple} />);

    fireEvent.click(screen.getByRole("button", { name: "간단히 보기" }));

    expect(showSimple).toHaveBeenCalledOnce();
  });
});
// === ANCHOR: HOMEHEADER_TEST_END ===
