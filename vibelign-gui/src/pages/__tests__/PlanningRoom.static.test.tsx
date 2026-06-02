import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  appendPlanningChatTurnMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    appendPlanningChatTurn: mocks.appendPlanningChatTurnMock,
  };
});

const result = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱 만들고 싶어",
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

describe("PlanningRoom chat session view", () => {
  afterEach(() => {
    cleanup();
    mocks.appendPlanningChatTurnMock.mockReset();
  });

  test("renders_saved_chat_message_and_persona_composer", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByText("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("클로이 설계")).toBeInTheDocument();
    expect(screen.getByText("지오 검토")).toBeInTheDocument();
    expect(screen.getByText("미나 탐색")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?")).toBeInTheDocument();
    expect(screen.queryByText("저장 위치:")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기획안 보기" })).toBeDisabled();
  });

  test("appends_followup_message_to_chat_state", async () => {
    const onResultChange = vi.fn();
    mocks.appendPlanningChatTurnMock.mockResolvedValue({
      ...result,
      messages: [
        ...result.messages,
        {
          id: "msg_2",
          role: "user",
          personaId: null,
          content: "사용 흐름을 더 구체화해줘",
          status: "ok",
          createdAt: "2026-06-02T00:01:00Z",
        },
      ],
    });
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={onResultChange} />);

    fireEvent.change(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?"), {
      target: { value: "사용 흐름을 더 구체화해줘" },
    });
    fireEvent.click(screen.getByRole("button", { name: "호출" }));

    expect(await screen.findByRole("button", { name: "호출" })).toBeInTheDocument();
    expect(mocks.appendPlanningChatTurnMock).toHaveBeenCalledWith({
      projectDir: "/tmp/demo",
      sessionId: "chat_1",
      prompt: "사용 흐름을 더 구체화해줘",
      agents: ["gio"],
    });
    expect(onResultChange).toHaveBeenCalled();
  });

  test("renders_error_without_raw_details", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={{
          ok: false,
          sessionId: null,
          prompt: null,
          messages: [],
          message: "기획방 대화를 준비하지 못했어요.",
          details: "raw stderr",
        }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.getByText("기획방 대화를 준비하지 못했어요.")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });
});
