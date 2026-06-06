// === ANCHOR: ONBOARDING_PR2_START_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import Onboarding from "../Onboarding";
import type { OnboardingSnapshot, VibProgressEvent, VibResult } from "../../lib/vib";

const progressLabels = [
  "프로젝트 확인 중...",
  "안전 규칙 준비 중...",
  "되돌리기 지점 저장 중...",
  "파일 변경 감시 준비 중...",
  "준비 완료",
] as const;

const mocks = vi.hoisted(() => ({
  openDialogMock: vi.fn<(...args: readonly [unknown]) => Promise<string | null>>(),
  getVibPathMock: vi.fn<() => Promise<string | null>>(),
  checkGitInstalledMock: vi.fn<() => Promise<boolean>>(),
  checkXcodeCltMock: vi.fn<() => Promise<boolean>>(),
  getOnboardingSnapshotMock: vi.fn<() => Promise<OnboardingSnapshot>>(),
  detectInstalledToolsMock: vi.fn<() => Promise<string[]>>(),
  runVibWithProgressMock: vi.fn<
    (
      args: readonly string[],
      cwd: string | undefined,
      env: Record<string, string> | undefined,
      onProgress: (event: VibProgressEvent) => void,
    ) => Promise<VibResult>
  >(),
  startWatchMock: vi.fn<(...args: readonly [string]) => Promise<void>>(),
  startNativeInstallMock: vi.fn<(...args: readonly ["native-powershell"]) => Promise<OnboardingSnapshot>>(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: mocks.openDialogMock,
}));

vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: vi.fn(async () => undefined),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    getVibPath: mocks.getVibPathMock,
    checkGitInstalled: mocks.checkGitInstalledMock,
    checkXcodeClt: mocks.checkXcodeCltMock,
    getOnboardingSnapshot: mocks.getOnboardingSnapshotMock,
    detectInstalledTools: mocks.detectInstalledToolsMock,
    runVibWithProgress: mocks.runVibWithProgressMock,
    startWatch: mocks.startWatchMock,
    startNativeInstall: mocks.startNativeInstallMock,
  };
});

// === ANCHOR: ONBOARDING_PR2_START_TEST_RENDERONBOARDING_START ===
function renderOnboarding(): { readonly onComplete: ReturnType<typeof vi.fn> } {
  const onComplete = vi.fn();
  render(<Onboarding onComplete={onComplete} recentDirs={[]} />);
  return { onComplete };
}
// === ANCHOR: ONBOARDING_PR2_START_TEST_RENDERONBOARDING_END ===

// === ANCHOR: ONBOARDING_PR2_START_TEST_RENDERONBOARDINGWITHPLANREQUEST_START ===
function renderOnboardingWithPlanRequest(): ReturnType<typeof vi.fn> {
  const onPlanRequest = vi.fn(async () => undefined);
  render(<Onboarding onComplete={vi.fn()} onPlanRequest={onPlanRequest} recentDirs={[]} />);
  return onPlanRequest;
}
// === ANCHOR: ONBOARDING_PR2_START_TEST_RENDERONBOARDINGWITHPLANREQUEST_END ===

// === ANCHOR: ONBOARDING_PR2_START_TEST_SELECTPROJECTFOLDER_START ===
async function selectProjectFolder(): Promise<void> {
  fireEvent.click(await screen.findByRole("button", { name: "프로젝트 폴더 선택" }));
  await screen.findByText((_content, node) => node?.textContent === "선택한 폴더: demo");
}
// === ANCHOR: ONBOARDING_PR2_START_TEST_SELECTPROJECTFOLDER_END ===

function snapshotWithState(state: string, extra: Partial<OnboardingSnapshot> = {}): OnboardingSnapshot {
  return { state, headline: "", ...extra } as OnboardingSnapshot;
}

describe("Onboarding PR2 auto start", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.openDialogMock.mockReset();
    mocks.getVibPathMock.mockReset();
    mocks.checkGitInstalledMock.mockReset();
    mocks.checkXcodeCltMock.mockReset();
    mocks.getOnboardingSnapshotMock.mockReset();
    mocks.detectInstalledToolsMock.mockReset();
    mocks.runVibWithProgressMock.mockReset();
    mocks.startWatchMock.mockReset();
    mocks.startNativeInstallMock.mockReset();

    mocks.openDialogMock.mockResolvedValue("/tmp/demo");
    mocks.getVibPathMock.mockResolvedValue("/usr/local/bin/vib");
    mocks.checkGitInstalledMock.mockResolvedValue(true);
    mocks.checkXcodeCltMock.mockResolvedValue(true);
    mocks.getOnboardingSnapshotMock.mockRejectedValue(new Error("snapshot unavailable"));
    mocks.detectInstalledToolsMock.mockResolvedValue([]);
    mocks.runVibWithProgressMock.mockImplementation(async (_args, _cwd, _env, onProgress) => {
      progressLabels.forEach((label, index) => {
        onProgress({
          step: "vib_start_progress",
          done: index + 1,
          total: progressLabels.length,
          message: label,
        });
      });
      return { ok: true, stdout: "", stderr: "", exit_code: 0 };
    });
    mocks.startWatchMock.mockResolvedValue();
    mocks.startNativeInstallMock.mockRejectedValue(new Error("installer failed"));
  });

  test("runs_non_interactive_start_and_watch_after_folder_submit", async () => {
    const { onComplete } = renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    await waitFor(() => {
      expect(mocks.runVibWithProgressMock).toHaveBeenCalledWith(
        ["start", "--non-interactive"],
        "/tmp/demo",
        undefined,
        expect.any(Function),
      );
    });
    expect(mocks.startWatchMock).toHaveBeenCalledWith("/tmp/demo");
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith("/tmp/demo", null);
    });
    expect(screen.getByText("준비 완료")).toBeInTheDocument();
  });

  test("renders_five_progress_labels_without_internal_terms", async () => {
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    for (const label of progressLabels) {
      expect(await screen.findByText(label)).toBeInTheDocument();
    }
    expect(screen.queryByText(/watch|anchor|guard|vib start/i)).not.toBeInTheDocument();
  });

  test("shows_claude_failure_as_separate_status_after_start_success", async () => {
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByLabelText("Claude Code도 자동으로 준비하기"));
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText("Claude Code 준비만 실패했어요. 프로젝트 안전장치는 켜져 있어요.")).toBeInTheDocument();
    expect(screen.queryByText("시작 실패")).not.toBeInTheDocument();
  });

  test("requests_planning_after_start_when_prompt_exists", async () => {
    const onPlanRequest = renderOnboardingWithPlanRequest();

    await selectProjectFolder();
    fireEvent.change(screen.getByPlaceholderText("무엇을 만들고 싶나요?"), {
      target: { value: "예약 앱 만들고 싶어" },
    });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    await waitFor(() => {
      expect(onPlanRequest).toHaveBeenCalledWith("/tmp/demo", "예약 앱 만들고 싶어");
    });
  });

  test("shows_login_hint_when_install_snapshot_reaches_login_required", async () => {
    mocks.startNativeInstallMock.mockResolvedValue(snapshotWithState("installing_native"));
    mocks.getOnboardingSnapshotMock.mockResolvedValue(snapshotWithState("login_required"));
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByLabelText("Claude Code도 자동으로 준비하기"));
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText(/claude login/, {}, { timeout: 3000 })).toBeInTheDocument();
  });

  test("shows_background_message_when_install_still_running", async () => {
    mocks.startNativeInstallMock.mockResolvedValue(snapshotWithState("installing_native"));
    mocks.getOnboardingSnapshotMock.mockResolvedValue(snapshotWithState("installing_native"));
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByLabelText("Claude Code도 자동으로 준비하기"));
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText(/백그라운드에서 설치 중/, {}, { timeout: 4000 })).toBeInTheDocument();
  });

  test("shows_real_reason_when_install_snapshot_reaches_blocked", async () => {
    mocks.startNativeInstallMock.mockResolvedValue(snapshotWithState("installing_native"));
    mocks.getOnboardingSnapshotMock.mockResolvedValue(
      snapshotWithState("blocked", {
        lastError: { code: "unknown", summary: "설치 프로세스 spawn 자체가 실패했어요." },
      }),
    );
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByLabelText("Claude Code도 자동으로 준비하기"));
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(
      await screen.findByText(/준비 실패: 설치 프로세스 spawn 자체가 실패했어요/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  test("includes_tools_for_all_installed_tools", async () => {
    mocks.detectInstalledToolsMock.mockResolvedValue(["claude", "codex", "cursor", "opencode", "antigravity"]);
    renderOnboarding();

    await selectProjectFolder();
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    await waitFor(() => {
      expect(mocks.runVibWithProgressMock).toHaveBeenCalledWith(
        ["start", "--non-interactive", "--tools", "claude,codex,cursor,opencode,antigravity"],
        "/tmp/demo",
        undefined,
        expect.any(Function),
      );
    });
  });
});
// === ANCHOR: ONBOARDING_PR2_START_TEST_END ===
