// === ANCHOR: RUNPANEL_NO_RECIPE_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RunPanel from "../RunPanel";

const runDetect = vi.fn();

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(() => Promise.resolve(() => undefined)),
}));

vi.mock("../../lib/vib/run", () => ({
  openPreview: vi.fn(),
  runDetect: (...args: unknown[]) => runDetect(...args),
  runStart: vi.fn(),
  runStatus: vi.fn(() => Promise.resolve({ running: false })),
  runStop: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RunPanel no recipe state", () => {
  it("hands missing runnable entrypoints back to the work room", async () => {
    runDetect.mockResolvedValue(null);
    const onRequestWorkHandoff = vi.fn();

    render(
      <RunPanel
        projectDir="/tmp/no-entry"
        onNavigate={vi.fn()}
        onRequestWorkHandoff={onRequestWorkHandoff}
      />,
    );

    await screen.findByText("실행 방법을 못 찾았어요");
    const runButton = screen.getByRole("button", { name: "▶ 실행해보기" });
    expect(runButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "작업방에서 실행 형태 만들기 →" }));

    await waitFor(() => expect(onRequestWorkHandoff).toHaveBeenCalledTimes(1));
    expect(onRequestWorkHandoff).toHaveBeenCalledWith({
      kind: "error",
      text: expect.stringContaining("index.html"),
    });
    expect(onRequestWorkHandoff.mock.calls[0][0].text).toContain("package.json");
    expect(onRequestWorkHandoff.mock.calls[0][0].text).toContain("dev");
    expect(onRequestWorkHandoff.mock.calls[0][0].text).toContain("start");
  });
});
// === ANCHOR: RUNPANEL_NO_RECIPE_TEST_END ===
