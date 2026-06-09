// === ANCHOR: PLANNINGROOM_STATIC_TEST_START ===
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  appendPlanningChatTurnMock: vi.fn(),
  savePlanningChatAsMarkdownMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    appendPlanningChatTurn: mocks.appendPlanningChatTurnMock,
    savePlanningChatAsMarkdown: mocks.savePlanningChatAsMarkdownMock,
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
    mocks.savePlanningChatAsMarkdownMock.mockReset();
  });

  test("renders_saved_chat_message_and_persona_composer", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByText("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("클로이 설계")).toBeInTheDocument();
    expect(screen.getByText("지오 검토")).toBeInTheDocument();
    expect(screen.getByText("미나 탐색")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?")).toBeInTheDocument();
    expect(screen.queryByText("저장 위치:")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기획안으로 저장" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "기획안 보기" })).toBeDisabled();
  });

  test("saves_chat_messages_as_markdown_plan", async () => {
    const onResultChange = vi.fn();
    mocks.savePlanningChatAsMarkdownMock.mockResolvedValue({
      ...result,
      outputPath: "plans/예약-앱-만들고-싶어.md",
      absoluteOutputPath: "/tmp/demo/plans/예약-앱-만들고-싶어.md",
      markdown: "# 예약 앱 만들고 싶어\n",
    });
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={onResultChange} />);

    fireEvent.click(screen.getByRole("button", { name: "기획안으로 저장" }));

    await waitFor(() => {
      expect(mocks.savePlanningChatAsMarkdownMock).toHaveBeenCalledWith({
        projectDir: "/tmp/demo",
        sessionId: "chat_1",
      });
    });
    expect(onResultChange).toHaveBeenCalledWith(
      expect.objectContaining({
        outputPath: "plans/예약-앱-만들고-싶어.md",
        markdown: "# 예약 앱 만들고 싶어\n",
      }),
    );
  });

  test("renders_saved_markdown_plan", () => {
    const onBack = vi.fn();
    const onStartWork = vi.fn();
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        result={{
          ...result,
          outputPath: "plans/예약-앱-만들고-싶어.md",
          markdown: "# 예약 앱 만들고 싶어\n\n## 한 줄 목표\n예약 앱 만들고 싶어\n",
        }}
        onBack={onBack}
        onStartWork={onStartWork}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.getByText("저장 위치: plans/예약-앱-만들고-싶어.md")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AI 작업 시작" }));
    expect(onStartWork).toHaveBeenCalledOnce();
    expect(onBack).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "기획안 보기" }));

    expect(screen.getByRole("heading", { name: "예약 앱 만들고 싶어", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "한 줄 목표", level: 2 })).toBeInTheDocument();
  });

  test("hides_start_work_action_until_plan_is_saved", () => {
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "AI 작업 시작" })).not.toBeInTheDocument();
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
      includeUserMessage: true,
      extractCards: true,
    });
    expect(onResultChange).toHaveBeenCalled();
  });

  test("shows_pending_messages_immediately_and_calls_selected_personas_one_by_one", async () => {
    const onResultChange = vi.fn();
    mocks.appendPlanningChatTurnMock
      .mockResolvedValueOnce({
        ...result,
        messages: [
          ...result.messages,
          {
            id: "msg_2",
            role: "user",
            personaId: null,
            content: "세 명이 차례로 봐줘",
            status: "ok",
            createdAt: "2026-06-02T00:01:00Z",
          },
          {
            id: "msg_chloe",
            role: "assistant",
            personaId: "chloe",
            content: "클로이 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:01Z",
          },
        ],
      })
      .mockResolvedValueOnce({
        ...result,
        messages: [
          ...result.messages,
          {
            id: "msg_2",
            role: "user",
            personaId: null,
            content: "세 명이 차례로 봐줘",
            status: "ok",
            createdAt: "2026-06-02T00:01:00Z",
          },
          {
            id: "msg_chloe",
            role: "assistant",
            personaId: "chloe",
            content: "클로이 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:01Z",
          },
          {
            id: "msg_gio",
            role: "assistant",
            personaId: "gio",
            content: "지오 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:02Z",
          },
        ],
      })
      .mockResolvedValueOnce({
        ...result,
        messages: [
          ...result.messages,
          {
            id: "msg_2",
            role: "user",
            personaId: null,
            content: "세 명이 차례로 봐줘",
            status: "ok",
            createdAt: "2026-06-02T00:01:00Z",
          },
          {
            id: "msg_chloe",
            role: "assistant",
            personaId: "chloe",
            content: "클로이 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:01Z",
          },
          {
            id: "msg_gio",
            role: "assistant",
            personaId: "gio",
            content: "지오 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:02Z",
          },
          {
            id: "msg_mina",
            role: "assistant",
            personaId: "mina",
            content: "미나 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:03Z",
          },
        ],
      })
      .mockResolvedValueOnce({
        ...result,
        messages: [
          ...result.messages,
          {
            id: "msg_2",
            role: "user",
            personaId: null,
            content: "세 명이 차례로 봐줘",
            status: "ok",
            createdAt: "2026-06-02T00:01:00Z",
          },
          {
            id: "msg_deepseek",
            role: "assistant",
            personaId: "deepseek",
            content: "딥시기 답변",
            status: "ok",
            createdAt: "2026-06-02T00:01:04Z",
          },
        ],
      });
    render(<PlanningRoom projectDir="/tmp/demo" result={result} onBack={vi.fn()} onResultChange={onResultChange} />);

    fireEvent.click(screen.getByRole("button", { name: "모두" }));
    fireEvent.change(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?"), {
      target: { value: "세 명이 차례로 봐줘" },
    });
    fireEvent.click(screen.getByRole("button", { name: "호출" }));

    await waitFor(() => {
      expect(onResultChange).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: expect.arrayContaining([
            expect.objectContaining({ content: "세 명이 차례로 봐줘", role: "user" }),
            expect.objectContaining({ content: "클로이가 답변을 준비하고 있어요.", personaId: "chloe", status: "pending" }),
          ]),
        }),
      );
    });
    await waitFor(() => expect(mocks.appendPlanningChatTurnMock).toHaveBeenCalledTimes(4));
    expect(mocks.appendPlanningChatTurnMock).toHaveBeenNthCalledWith(1, {
      projectDir: "/tmp/demo",
      sessionId: "chat_1",
      prompt: "세 명이 차례로 봐줘",
      agents: ["chloe"],
      includeUserMessage: true,
      extractCards: false,
    });
    expect(mocks.appendPlanningChatTurnMock).toHaveBeenNthCalledWith(2, {
      projectDir: "/tmp/demo",
      sessionId: "chat_1",
      prompt: "세 명이 차례로 봐줘",
      agents: ["gio"],
      includeUserMessage: false,
      extractCards: false,
    });
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
// === ANCHOR: PLANNINGROOM_STATIC_TEST_END ===
