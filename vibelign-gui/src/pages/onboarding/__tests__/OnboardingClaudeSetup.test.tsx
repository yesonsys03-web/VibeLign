// === ANCHOR: ONBOARDINGCLAUDESETUP_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { OnboardingClaudeSetup } from "../OnboardingClaudeSetup";
import type { OnboardingSnapshot } from "../../../lib/vib";

const mocks = vi.hoisted(() => ({
  getOnboardingSnapshotMock: vi.fn<() => Promise<OnboardingSnapshot>>(),
  listenOnboardingProgressMock: vi.fn<(...args: readonly [unknown]) => Promise<() => void>>(),
  getOnboardingLogsMock: vi.fn<() => Promise<{ text: string }>>(),
  startNativeInstallMock: vi.fn<(...args: readonly [string]) => Promise<OnboardingSnapshot>>(),
  addClaudeToUserPathMock: vi.fn<() => Promise<OnboardingSnapshot>>(),
  retryOnboardingVerificationMock: vi.fn<() => Promise<OnboardingSnapshot>>(),
  startOnboardingLoginProbeMock: vi.fn<() => Promise<OnboardingSnapshot>>(),
  uninstallClaudeCodeMock: vi.fn<(...args: readonly [string]) => Promise<OnboardingSnapshot>>(),
}));

vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: vi.fn(async () => undefined),
}));

vi.mock("../../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../../lib/vib")>("../../../lib/vib");
  return {
    ...actual,
    getOnboardingSnapshot: mocks.getOnboardingSnapshotMock,
    listenOnboardingProgress: mocks.listenOnboardingProgressMock,
    getOnboardingLogs: mocks.getOnboardingLogsMock,
    startNativeInstall: mocks.startNativeInstallMock,
    addClaudeToUserPath: mocks.addClaudeToUserPathMock,
    retryOnboardingVerification: mocks.retryOnboardingVerificationMock,
    startOnboardingLoginProbe: mocks.startOnboardingLoginProbeMock,
    uninstallClaudeCode: mocks.uninstallClaudeCodeMock,
  };
});

function snap(extra: Partial<OnboardingSnapshot>): OnboardingSnapshot {
  return {
    state: "ready_to_install",
    os: "windows",
    installPathKind: "unknown",
    shellTargets: [],
    nextAction: "none",
    headline: "",
    logsAvailable: false,
    diagnostics: {},
    ...extra,
  } as OnboardingSnapshot;
}

describe("OnboardingClaudeSetup", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    mocks.getOnboardingSnapshotMock.mockReset();
    mocks.listenOnboardingProgressMock.mockReset();
    mocks.getOnboardingLogsMock.mockReset();
    mocks.startNativeInstallMock.mockReset();
    mocks.uninstallClaudeCodeMock.mockReset();

    mocks.listenOnboardingProgressMock.mockResolvedValue(() => {});
    mocks.getOnboardingLogsMock.mockResolvedValue({ text: "" });
  });

  test("renders_status_and_starts_install_on_primary_click", async () => {
    mocks.getOnboardingSnapshotMock.mockResolvedValue(
      snap({ state: "ready_to_install", nextAction: "start_install", headline: "자동 설치를 시작할 수 있어요", primaryButtonLabel: "자동 설치 시작" }),
    );
    mocks.startNativeInstallMock.mockResolvedValue(snap({ state: "installing_native" }));

    render(<OnboardingClaudeSetup />);

    expect(await screen.findByText("자동 설치를 시작할 수 있어요")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "자동 설치 시작" }));

    await waitFor(() => {
      expect(mocks.startNativeInstallMock).toHaveBeenCalledWith("native-powershell");
    });
  });

  test("uninstall_button_calls_command_with_all", async () => {
    mocks.getOnboardingSnapshotMock.mockResolvedValue(
      snap({ state: "login_required", nextAction: "start_login", headline: "로그인만 남았어요", primaryButtonLabel: "로그인", installPathKind: "native-powershell" }),
    );
    mocks.uninstallClaudeCodeMock.mockResolvedValue(snap({ state: "ready_to_install" }));
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<OnboardingClaudeSetup />);

    fireEvent.click(await screen.findByRole("button", { name: "전체 삭제" }));

    await waitFor(() => {
      expect(mocks.uninstallClaudeCodeMock).toHaveBeenCalledWith("all");
    });
    confirmSpy.mockRestore();
  });

  test("shows_live_logs_during_active_state", async () => {
    mocks.getOnboardingSnapshotMock.mockResolvedValue(
      snap({ state: "installing_native", logsAvailable: true, headline: "설치하고 있어요" }),
    );
    mocks.getOnboardingLogsMock.mockResolvedValue({ text: "$ irm install.ps1 | iex" });

    render(<OnboardingClaudeSetup />);

    expect(await screen.findByText(/irm install\.ps1/)).toBeInTheDocument();
  });
});
// === ANCHOR: ONBOARDINGCLAUDESETUP_TEST_END ===
