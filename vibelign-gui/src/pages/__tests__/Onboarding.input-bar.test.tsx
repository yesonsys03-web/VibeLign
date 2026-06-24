// === ANCHOR: ONBOARDING_INPUT_BAR_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import Onboarding from "../Onboarding";
import type { VibResult } from "../../lib/vib";

const mocks = vi.hoisted(() => ({
  openDialogMock: vi.fn<(...args: readonly [unknown]) => Promise<string | null>>(),
  openUrlMock: vi.fn<(...args: readonly [string]) => Promise<void>>(),
  getVibPathMock: vi.fn<() => Promise<string | null>>(),
  checkGitInstalledMock: vi.fn<() => Promise<boolean>>(),
  checkXcodeCltMock: vi.fn<() => Promise<boolean>>(),
  getOnboardingSnapshotMock: vi.fn<() => Promise<never>>(),
  listenOnboardingProgressMock: vi.fn<(...args: readonly [unknown]) => Promise<() => void>>(),
  getOnboardingLogsMock: vi.fn<() => Promise<{ text: string }>>(),
  vibStartMock: vi.fn<(...args: readonly [string, readonly string[]?]) => Promise<VibResult>>(),
  readProjectSummaryMock: vi.fn<() => Promise<never>>(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: mocks.openDialogMock,
}));

vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: mocks.openUrlMock,
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    getVibPath: mocks.getVibPathMock,
    checkGitInstalled: mocks.checkGitInstalledMock,
    checkXcodeClt: mocks.checkXcodeCltMock,
    getOnboardingSnapshot: mocks.getOnboardingSnapshotMock,
    listenOnboardingProgress: mocks.listenOnboardingProgressMock,
    getOnboardingLogs: mocks.getOnboardingLogsMock,
    vibStart: mocks.vibStartMock,
    readProjectSummary: mocks.readProjectSummaryMock,
    loadProviderApiKeys: vi.fn(async () => null),
    retryOnboardingVerification: vi.fn(),
    startNativeInstall: vi.fn(),
    startOnboardingLoginProbe: vi.fn(),
    addClaudeToUserPath: vi.fn(),
    uninstallClaudeCode: vi.fn(),
  };
});

// === ANCHOR: ONBOARDING_INPUT_BAR_TEST_RENDERONBOARDING_START ===
function renderOnboarding(): void {
  render(<Onboarding onComplete={vi.fn()} onResume={vi.fn()} onRemoveRecent={vi.fn()} recentDirs={["/tmp/demo"]} />);
}
// === ANCHOR: ONBOARDING_INPUT_BAR_TEST_RENDERONBOARDING_END ===

describe("Onboarding input bar", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.openDialogMock.mockReset();
    mocks.openUrlMock.mockReset();
    mocks.getVibPathMock.mockReset();
    mocks.checkGitInstalledMock.mockReset();
    mocks.checkXcodeCltMock.mockReset();
    mocks.getOnboardingSnapshotMock.mockReset();
    mocks.listenOnboardingProgressMock.mockReset();
    mocks.getOnboardingLogsMock.mockReset();
    mocks.vibStartMock.mockReset();
    mocks.readProjectSummaryMock.mockReset();

    mocks.openDialogMock.mockResolvedValue(null);
    mocks.openUrlMock.mockResolvedValue(undefined);
    mocks.getVibPathMock.mockResolvedValue("/usr/local/bin/vib");
    mocks.checkGitInstalledMock.mockResolvedValue(true);
    mocks.checkXcodeCltMock.mockResolvedValue(true);
    mocks.getOnboardingSnapshotMock.mockRejectedValue(new Error("snapshot unavailable"));
    mocks.listenOnboardingProgressMock.mockResolvedValue(() => {});
    mocks.getOnboardingLogsMock.mockResolvedValue({ text: "" });
    mocks.vibStartMock.mockResolvedValue({ ok: true, stdout: "", stderr: "", exit_code: 0 });
    mocks.readProjectSummaryMock.mockRejectedValue(new Error("summary unavailable"));
  });

  test("test_default_screen_centers_prompt_bar_and_hides_legacy_surface", async () => {
    renderOnboarding();

    expect(await screen.findByText("계획부터, 바이브까지, 되돌림은 언제든")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("무엇을 만들고 싶나요?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /AI 도구/ })).toBeInTheDocument();
    expect(screen.getByLabelText("VibeLign 온보딩 영상")).toBeInTheDocument();
    expect(screen.getByText("Instant")).toBeInTheDocument();

    expect(screen.queryByText("코드맵 생성")).not.toBeInTheDocument();
    expect(screen.queryByText("AI 폭주 방지")).not.toBeInTheDocument();
    expect(screen.queryByText("원클릭 복구")).not.toBeInTheDocument();
    expect(screen.queryByText("AI 이동 자유")).not.toBeInTheDocument();
    expect(screen.queryByText(/vibelign start/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/GitHub/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Threads/i)).not.toBeInTheDocument();
    expect(screen.queryByText("바이브라인 첫걸음")).not.toBeInTheDocument();
    expect(screen.queryByText("patch")).not.toBeInTheDocument();
    expect(screen.queryByText("CodeSpeak")).not.toBeInTheDocument();
    expect(screen.queryByText("plan-structure")).not.toBeInTheDocument();
  });

  test("test_intro_video_autoplays_loops_and_stays_at_bottom", async () => {
    renderOnboarding();

    const setupToggle = await screen.findByRole("button", { name: /AI 도구/ });
    const guideButton = screen.getByRole("button", { name: "갸리카 길잡이" });
    const video = screen.getByLabelText("VibeLign 온보딩 영상 플레이어");

    expect(guideButton.compareDocumentPosition(setupToggle) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(setupToggle.compareDocumentPosition(video) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(guideButton.compareDocumentPosition(video) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(video).toHaveAttribute("autoplay");
    expect(video).toHaveAttribute("controls");
    expect(video).toHaveAttribute("loop");
    expect(video).toHaveAttribute("playsinline");
    expect(video).toHaveProperty("muted", true);
    expect(video).toHaveAttribute("src", expect.stringContaining("raw=1"));
    expect(video).toHaveStyle({ aspectRatio: "16 / 9", objectFit: "contain" });
  });

  test("test_intro_video_title_opens_threads_profile", async () => {
    renderOnboarding();

    const title = await screen.findByRole("button", { name: "VibeLign 시작 영상" });
    fireEvent.click(title);

    expect(mocks.openUrlMock).toHaveBeenCalledWith("https://www.threads.com/@jongjatdon");
  });

  test("test_text_submit_without_folder_keeps_prompt_and_shows_folder_hint", async () => {
    renderOnboarding();
    const prompt = await screen.findByPlaceholderText("무엇을 만들고 싶나요?");

    fireEvent.change(prompt, { target: { value: "예약 앱 만들고 싶어" } });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(screen.getByDisplayValue("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("먼저 프로젝트 폴더를 선택해 주세요.")).toBeInTheDocument();
    expect(mocks.vibStartMock).not.toHaveBeenCalled();
    expect(screen.queryByText("프로젝트 확인 중...")).not.toBeInTheDocument();
  });

  test("test_shift_enter_adds_new_line_without_submitting", async () => {
    renderOnboarding();
    const prompt = await screen.findByPlaceholderText("무엇을 만들고 싶나요?");

    fireEvent.change(prompt, { target: { value: "예약 앱" } });
    fireEvent.keyDown(prompt, { key: "Enter", shiftKey: true });
    fireEvent.change(prompt, { target: { value: "예약 앱\n관리자 화면" } });

    expect(prompt).toHaveValue("예약 앱\n관리자 화면");
    expect(screen.queryByText("먼저 프로젝트 폴더를 선택해 주세요.")).not.toBeInTheDocument();
    expect(mocks.vibStartMock).not.toHaveBeenCalled();
  });

  test("test_folder_cancel_keeps_prompt_without_error", async () => {
    renderOnboarding();
    const prompt = await screen.findByPlaceholderText("무엇을 만들고 싶나요?");

    fireEvent.change(prompt, { target: { value: "예약 앱 만들고 싶어" } });
    fireEvent.click(screen.getByRole("button", { name: "프로젝트 폴더 선택" }));

    expect(await screen.findByDisplayValue("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.queryByText("시작 실패")).not.toBeInTheDocument();
    expect(mocks.openDialogMock).toHaveBeenCalledWith({ directory: true, multiple: false, title: "프로젝트 폴더 선택" });
  });

  test("test_advanced_toggle_reveals_secondary_details", async () => {
    renderOnboarding();

    expect(screen.queryByText("최근 프로젝트")).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /AI 도구/ }));

    expect(screen.getByText("최근 프로젝트")).toBeInTheDocument();
    expect(screen.getByText("시스템 상태")).toBeInTheDocument();
    expect(screen.queryByText("patch")).not.toBeInTheDocument();
    expect(screen.queryByText("CodeSpeak")).not.toBeInTheDocument();
    expect(screen.queryByText("plan-structure")).not.toBeInTheDocument();
  });
});
// === ANCHOR: ONBOARDING_INPUT_BAR_TEST_END ===
