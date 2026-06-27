import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import TutorialPicker from "../TutorialPicker";
import { TUTORIALS } from "../../../lib/tutorial/scripts";

describe("TutorialPicker", () => {
  afterEach(() => {
    cleanup();
  });

  it("등록된 튜토리얼들을 카드로 보여준다", () => {
    render(<TutorialPicker onPick={() => {}} onClose={() => {}} />);
    for (const t of TUTORIALS) {
      expect(screen.getByText(t.title)).toBeTruthy();
    }
  });

  it("카드를 누르면 해당 id로 onPick한다", () => {
    const onPick = vi.fn();
    render(<TutorialPicker onPick={onPick} onClose={() => {}} />);
    fireEvent.click(screen.getByText(TUTORIALS[0].title));
    expect(onPick).toHaveBeenCalledWith(TUTORIALS[0].id);
  });

  it("'나중에 할게요'는 onClose한다", () => {
    const onClose = vi.fn();
    render(<TutorialPicker onPick={() => {}} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /나중에/ }));
    expect(onClose).toHaveBeenCalled();
  });
});
