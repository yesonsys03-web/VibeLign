import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import CodeExplorer from "../CodeExplorer";

const mocks = vi.hoisted(() => ({
  listChangedFilesMock: vi.fn(),
  listCodeFilesMock: vi.fn(),
  readCodeFileDiffMock: vi.fn(),
  readCodeFileMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    listChangedFiles: mocks.listChangedFilesMock,
    listCodeFiles: mocks.listCodeFilesMock,
    readCodeFile: mocks.readCodeFileMock,
    readCodeFileDiff: mocks.readCodeFileDiffMock,
  };
});

describe("CodeExplorer planning context", () => {
  afterEach(() => {
    cleanup();
    mocks.listChangedFilesMock.mockReset();
    mocks.listCodeFilesMock.mockReset();
    mocks.readCodeFileDiffMock.mockReset();
    mocks.readCodeFileMock.mockReset();
  });

  test("keeps_planning_context_hidden_without_saved_plan", async () => {
    givenCodeExplorerData();

    render(<CodeExplorer projectDir="/tmp/demo" planningPrompt="예약 앱 만들고 싶어" planningOutputPath={null} />);

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    expect(screen.queryByText("작업 기준 기획안")).not.toBeInTheDocument();
  });

  test("shows_saved_plan_context_after_starting_ai_work", async () => {
    givenCodeExplorerData();

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    expect(screen.getByText("작업 기준 기획안")).toBeInTheDocument();
    expect(screen.getByText("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("plans/예약-앱-만들고-싶어.md")).toBeInTheDocument();
  });

  test("copies_saved_plan_work_instruction", async () => {
    givenCodeExplorerData();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 복사" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("저장된 기획안: plans/예약-앱-만들고-싶어.md"));
    expect(screen.getByText("복사했어요. 사용하는 AI CLI에 붙여넣어 시작하세요.")).toBeInTheDocument();
  });

  test("copies_persona_specific_cli_work_instruction", async () => {
    givenCodeExplorerData();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "지오 Codex" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("검토자 지오"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Codex CLI"));
  });

  test("previews_saved_plan_work_instruction_before_copy", async () => {
    givenCodeExplorerData();

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 미리보기" }));

    expect(screen.getByRole("heading", { name: "작업 지시 미리보기" })).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("저장된 기획안: plans/예약-앱-만들고-싶어.md"))).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("공식 CLI"))).toBeInTheDocument();
  });

  test("previews_persona_specific_cli_work_instruction_before_copy", async () => {
    givenCodeExplorerData();

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 미리보기" }));
    fireEvent.click(screen.getByRole("button", { name: "지오 미리보기" }));

    expect(screen.getByRole("heading", { name: "작업 지시 미리보기" })).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("검토자 지오"))).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("Codex CLI"))).toBeInTheDocument();
  });

  test("copies_current_persona_preview_instruction", async () => {
    givenCodeExplorerData();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 미리보기" }));
    fireEvent.click(screen.getByRole("button", { name: "지오 미리보기" }));
    fireEvent.click(screen.getByRole("button", { name: "현재 미리보기 복사" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("검토자 지오"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Codex CLI"));
  });

  test("shows_current_preview_target_label", async () => {
    givenCodeExplorerData();

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 미리보기" }));

    expect(screen.getByText("현재 미리보기: 공통")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "지오 미리보기" }));

    expect(screen.getByText("현재 미리보기: 지오 Codex")).toBeInTheDocument();
  });

  test("marks_current_preview_choice_as_selected", async () => {
    givenCodeExplorerData();

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 미리보기" }));

    const commonPreview = screen.getByRole("button", { name: "공통 미리보기" });
    const gioPreview = screen.getByRole("button", { name: "지오 미리보기" });

    expect(commonPreview).toHaveAttribute("aria-pressed", "true");
    expect(gioPreview).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(gioPreview);

    expect(commonPreview).toHaveAttribute("aria-pressed", "false");
    expect(gioPreview).toHaveAttribute("aria-pressed", "true");
  });

  test("shows_instruction_preview_when_clipboard_copy_fails", async () => {
    givenCodeExplorerData();
    const writeText = vi.fn().mockRejectedValue(new Error("clipboard denied"));
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <CodeExplorer
        projectDir="/tmp/demo"
        planningPrompt="예약 앱 만들고 싶어"
        planningOutputPath="plans/예약-앱-만들고-싶어.md"
      />,
    );

    await waitFor(() => expect(screen.getByText("1 files")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "작업 지시 복사" }));

    expect(await screen.findByText("자동 복사에 실패해서 아래에 작업 지시를 표시했어요.")).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("저장된 기획안: plans/예약-앱-만들고-싶어.md"))).toBeInTheDocument();
  });
});

function givenCodeExplorerData() {
  mocks.listCodeFilesMock.mockResolvedValue([
    { path: "src/App.tsx", category: "ui", imports: [] },
  ]);
  mocks.listChangedFilesMock.mockResolvedValue([]);
  mocks.readCodeFileMock.mockResolvedValue({
    path: "src/App.tsx",
    content: "export function App() { return null; }",
    source_hash: "hash",
    size_bytes: 38,
    line_count: 1,
    language: "tsx",
  });
  mocks.readCodeFileDiffMock.mockResolvedValue({
    path: "src/App.tsx",
    language: "tsx",
    baseline_source: "none",
    added: 0,
    removed: 0,
    lines: [],
  });
}
