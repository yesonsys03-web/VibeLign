// === ANCHOR: DESIGNJOBCHIP_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, test, expect, vi } from "vitest";
import { DesignJobChip } from "../DesignJobChip";

afterEach(cleanup);

describe("DesignJobChip", () => {
  test("running·타페이지면 칩이 보이고 클릭 시 onOpen", () => {
    const onOpen = vi.fn();
    render(<DesignJobChip status="running" page="home" onOpen={onOpen} />);
    const btn = screen.getByRole("button", { name: /생성 중/ });
    fireEvent.click(btn);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  test("design-preview 페이지면 렌더 안 함", () => {
    const { container } = render(<DesignJobChip status="running" page="design-preview" onOpen={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  test("idle이면 렌더 안 함", () => {
    const { container } = render(<DesignJobChip status="idle" page="home" onOpen={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });
});
// === ANCHOR: DESIGNJOBCHIP_TEST_END ===
