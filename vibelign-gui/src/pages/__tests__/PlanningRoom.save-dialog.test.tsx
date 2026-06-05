// === ANCHOR: PLANNINGROOM_SAVE_DIALOG_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  savePlanningChatAsMarkdownMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    savePlanningChatAsMarkdown: mocks.savePlanningChatAsMarkdownMock,
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
      });
    });
  });
});
// === ANCHOR: PLANNINGROOM_SAVE_DIALOG_TEST_END ===
