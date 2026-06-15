// === ANCHOR: TOOLINSTALLPANEL_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ToolInstallPanel } from "../ToolInstallPanel";

const mocks = vi.hoisted(() => ({
  toolInstallStatus: vi.fn(),
  uninstallTool: vi.fn(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => undefined),
}));
vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("../../../lib/tools/installerRegistry", async () => {
  const actual = await vi.importActual<typeof import("../../../lib/tools/installerRegistry")>(
    "../../../lib/tools/installerRegistry",
  );
  return {
    ...actual,
    toolInstallStatus: mocks.toolInstallStatus,
    uninstallTool: mocks.uninstallTool,
    installTool: vi.fn(),
  };
});

describe("ToolInstallPanel uninstall", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.toolInstallStatus.mockReset();
    mocks.uninstallTool.mockReset();
  });

  test("shows_uninstall_button_when_installed", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    render(<ToolInstallPanel id="opencode" />);
    expect(await screen.findByRole("button", { name: /제거/ })).toBeInTheDocument();
  });

  test("confirm_then_calls_uninstallTool", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    mocks.uninstallTool.mockResolvedValue({ removed: true, exitCode: 0, manualHint: "", manualUrl: "" });
    render(<ToolInstallPanel id="opencode" />);
    fireEvent.click(await screen.findByRole("button", { name: /제거/ }));
    fireEvent.click(screen.getByRole("button", { name: "제거" }));
    await waitFor(() => expect(mocks.uninstallTool).toHaveBeenCalledWith("opencode"));
    expect(await screen.findByText(/제거 완료/)).toBeInTheDocument();
  });

  test("cancel_returns_to_usable_state", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    render(<ToolInstallPanel id="opencode" />);
    fireEvent.click(await screen.findByRole("button", { name: /제거/ }));
    fireEvent.click(screen.getByText("취소"));
    expect(await screen.findByRole("button", { name: /제거/ })).toBeInTheDocument();
  });

  test("removed_false_shows_manual_guide", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    mocks.uninstallTool.mockResolvedValue({
      removed: false,
      exitCode: null,
      manualHint: "설정 > 앱에서 제거하세요.",
      manualUrl: "https://antigravity.google/docs/cli-install",
    });
    render(<ToolInstallPanel id="agy" />);
    fireEvent.click(await screen.findByRole("button", { name: /제거/ }));
    fireEvent.click(screen.getByRole("button", { name: "제거" }));
    expect(await screen.findByText(/설정 > 앱에서 제거하세요\./)).toBeInTheDocument();
  });
});
// === ANCHOR: TOOLINSTALLPANEL_TEST_END ===
