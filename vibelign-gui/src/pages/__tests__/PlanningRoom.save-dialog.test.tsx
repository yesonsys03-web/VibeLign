// === ANCHOR: PLANNINGROOM_SAVE_DIALOG_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  savePlanningChatAsMarkdownMock: vi.fn(),
  appendPlanningChatTurnMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    savePlanningChatAsMarkdown: mocks.savePlanningChatAsMarkdownMock,
    appendPlanningChatTurn: mocks.appendPlanningChatTurnMock,
  };
});

const result = {
  ok: true,
  sessionId: "chat_1",
  prompt: "기획 문서 검토",
  messages: [
    {
      id: "msg_1",
      role: "user" as const,
      personaId: null,
      content: "기획 문서 검토",
      status: "ok",
      createdAt: "2026-06-02T00:00:00Z",
    },
  ],
};

describe("PlanningRoom save dialog for review sessions", () => {
  afterEach(() => {
    cleanup();
    mocks.savePlanningChatAsMarkdownMock.mockReset();
    mocks.appendPlanningChatTurnMock.mockReset();
  });

  test("opens_dialog_and_saves_to_default_review_name_in_source_folder", async () => {
    const onResultChange = vi.fn();
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({
      ...result,
      outputPath: "docs/spec-foo-review.md",
      markdown: "# 기획 문서 검토\n",
    });
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={result}
        sourcePath="docs/spec-foo.md"
        onBack={vi.fn()}
        onResultChange={onResultChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "기획안으로 저장" }));

    expect(screen.getByText("저장 폴더: docs")).toBeInTheDocument();
    const input = screen.getByDisplayValue("spec-foo-review.md");
    expect(input).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
        targetPath: "docs/spec-foo-review.md",
        source: "button",
      });
    });
    expect(onResultChange).toHaveBeenCalledWith(
      expect.objectContaining({ outputPath: "docs/spec-foo-review.md" }),
    );
  });

  test("overwrite_checkbox_saves_to_source_path", async () => {
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({ ...result, outputPath: "docs/spec-foo.md" });
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={result}
        sourcePath="docs/spec-foo.md"
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "기획안으로 저장" }));
    fireEvent.click(screen.getByLabelText("원본 파일(spec-foo.md) 덮어쓰기"));
    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
        targetPath: "docs/spec-foo.md",
        source: "button",
      });
    });
  });

  test("non_review_session_saves_directly_without_dialog", async () => {
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({ ...result, outputPath: "plans/foo.md" });
    render(
      <PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "기획안으로 저장" }));

    expect(screen.queryByText(/저장 폴더:/)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
        source: "button",
      });
    });
  });

  test("slash_save_command_triggers_controlled_save_with_slash_source", async () => {
    // /저장 입력 → 페르소나 호출 없이 통제 저장, 출처는 slash 로 기록.
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({ ...result, outputPath: "plans/foo.md" });
    render(
      <PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />,
    );

    const textarea = screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?");
    fireEvent.change(textarea, { target: { value: "/저장" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
        source: "slash",
      });
    });
    // AC: /저장은 페르소나 호출 없이 즉시 통제 저장 — 대화 턴이 발생하면 안 된다.
    expect(mocks.appendPlanningChatTurnMock).not.toHaveBeenCalled();
  });

  test("slash_prefix_shows_command_hint_and_tab_completes_then_saves", async () => {
    // "/" 입력 → 커맨드 힌트 노출 → Tab 자동완성 → Enter 통제 저장.
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({ ...result, outputPath: "plans/foo.md" });
    render(
      <PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />,
    );

    const textarea = screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "/" } });

    // 힌트(커맨드 + 라벨)가 보인다.
    expect(screen.getByText("/저장")).toBeInTheDocument();
    expect(screen.getByText("기획안 저장")).toBeInTheDocument();

    // Tab → "/저장" 자동완성.
    fireEvent.keyDown(textarea, { key: "Tab" });
    expect(textarea.value).toBe("/저장");

    // Enter → slash 출처로 통제 저장.
    fireEvent.keyDown(textarea, { key: "Enter" });
    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
        source: "slash",
      });
    });
  });
});
// === ANCHOR: PLANNINGROOM_SAVE_DIALOG_TEST_END ===
