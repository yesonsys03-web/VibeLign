import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

const mocks = vi.hoisted(() => ({
  appendPlanningWithAgentsMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    appendPlanningWithAgents: mocks.appendPlanningWithAgentsMock,
  };
});

const result = {
  ok: true,
  outputPath: "plans/reservation-app.md",
  absoluteOutputPath: "/tmp/demo/plans/reservation-app.md",
  markdown: "# 예약 앱\n## 한 줄 목표\n예약을 쉽게 만든다.",
  fallbackReason: null,
  sessionId: "plan_1",
  adapter: "codex",
  personaId: "gio",
  llmStatus: "ok",
  agentsRequested: ["chloe", "gio", "mina"],
  agentsUsed: ["chloe", "gio", "mina"],
  agentStatuses: {
    chloe: "ok",
    gio: "ok",
    mina: "ok",
  },
};

describe("PlanningRoom static template view", () => {
  afterEach(() => {
    cleanup();
    mocks.appendPlanningWithAgentsMock.mockReset();
  });

  test("renders_user_message_and_template_response_without_model_controls", () => {
    render(<PlanningRoom projectDir="/tmp/demo" prompt="예약 앱 만들고 싶어" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    expect(screen.getByText("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("VibeLign 정리")).toBeInTheDocument();
    expect(screen.getByText("클로이 설계")).toBeInTheDocument();
    expect(screen.getByText("지오 검토")).toBeInTheDocument();
    expect(screen.getByText("미나 탐색")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?")).toBeInTheDocument();
    expect(screen.getByText("저장 위치: plans/reservation-app.md")).toBeInTheDocument();
    expect(screen.queryByText(/model|모델|plan-structure/i)).not.toBeInTheDocument();
    expect(screen.queryByText("# 예약 앱")).not.toBeInTheDocument();
  });

  test("shows_markdown_pane_after_action", () => {
    render(<PlanningRoom projectDir="/tmp/demo" prompt="예약 앱 만들고 싶어" result={result} onBack={vi.fn()} onResultChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "기획안 보기" }));

    expect(screen.getByRole("heading", { name: "예약 앱" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "한 줄 목표" })).toBeInTheDocument();
  });

  test("renders_fallback_status_without_raw_error_output", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        prompt="예약 앱 만들고 싶어"
        result={{
          ...result,
          fallbackReason: "cli_unavailable_template_only",
          llmStatus: "not_logged_in",
          agentsUsed: [],
          agentStatuses: {
            chloe: "not_logged_in",
            gio: "not_logged_in",
            mina: "not_logged_in",
          },
          details: "raw stderr",
        }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.getByText("AI 연결은 아직 준비되지 않았지만, 기본 기획안은 저장했어요.")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });

  test("renders_pending_state_without_markdown_action", () => {
    render(
      <PlanningRoom
        projectDir="/tmp/demo"
        prompt="예약 앱 만들고 싶어"
        result={{
          ...result,
          outputPath: null,
          markdown: null,
          llmStatus: "pending",
          agentsUsed: [],
          agentStatuses: {
            chloe: "pending",
            gio: "pending",
            mina: "pending",
          },
        }}
        onBack={vi.fn()}
        onResultChange={vi.fn()}
      />,
    );

    expect(screen.getByText("AI들이 기획안을 나눠서 확인하는 중이에요.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기획안 보기" })).toBeDisabled();
  });

  test("calls_selected_persona_with_followup_message", async () => {
    const onResultChange = vi.fn();
    mocks.appendPlanningWithAgentsMock.mockResolvedValue({
      ...result,
      markdown: `${result.markdown}\n\n## 지오의 검토\n좋아요.`,
    });
    render(<PlanningRoom projectDir="/tmp/demo" prompt="예약 앱 만들고 싶어" result={result} onBack={vi.fn()} onResultChange={onResultChange} />);

    fireEvent.change(screen.getByPlaceholderText("기획안을 어떻게 더 다듬을까요?"), {
      target: { value: "사용 흐름을 더 구체화해줘" },
    });
    fireEvent.click(screen.getByRole("button", { name: "호출" }));

    expect(await screen.findByRole("button", { name: "호출" })).toBeInTheDocument();
    expect(mocks.appendPlanningWithAgentsMock).toHaveBeenCalledWith({
      projectDir: "/tmp/demo",
      outputPath: "plans/reservation-app.md",
      prompt: "사용 흐름을 더 구체화해줘",
      cli: "auto",
      agents: ["gio"],
    });
    expect(onResultChange).toHaveBeenCalled();
  });
});
