import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  openFolderMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    openFolder: mocks.openFolderMock,
  };
});

const savedResult = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱 만들고 싶어",
  outputPath: "plans/예약-앱-만들고-싶어.md",
  absoluteOutputPath: "/tmp/demo/plans/예약-앱-만들고-싶어.md",
  markdown: "# 예약 앱 만들고 싶어\n",
  messages: [
    {
      id: "msg_1",
      role: "user" as const,
      personaId: null,
      content: "예약 앱 만들고 싶어",
      status: "ok",
      createdAt: "2026-06-02T00:00:00Z",
    },
  ],
};

describe("PlanningRoom saved plan open action", () => {
  afterEach(() => {
    cleanup();
    mocks.openFolderMock.mockReset();
  });

  test("keeps_existing_saved_plan_actions_visible", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={savedResult} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "기획안 다시 저장" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "기획안 보기" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "AI 작업 시작" })).toBeEnabled();
  });

  test("opens_saved_plan_file_with_absolute_output_path", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={savedResult} onBack={vi.fn()} onResultChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "저장 파일 열기" }));

    expect(mocks.openFolderMock).toHaveBeenCalledWith("/tmp/demo/plans/예약-앱-만들고-싶어.md");
  });

  test("resolves_relative_output_path_against_project_dir", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={{ ...savedResult, absoluteOutputPath: null }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "저장 파일 열기" }));

    expect(mocks.openFolderMock).toHaveBeenCalledWith("/tmp/demo/plans/예약-앱-만들고-싶어.md");
  });

  test("hides_open_action_until_plan_is_saved", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={{
          ok: true,
          sessionId: "chat_1",
          prompt: "예약 앱 만들고 싶어",
          messages: savedResult.messages,
        }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "저장 파일 열기" })).not.toBeInTheDocument();
  });
});
