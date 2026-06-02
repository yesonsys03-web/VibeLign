import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import PlanningRoom from "../PlanningRoom";

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
};

describe("PlanningRoom static template view", () => {
  afterEach(() => {
    cleanup();
  });

  test("renders_user_message_and_template_response_without_model_controls", () => {
    render(<PlanningRoom prompt="예약 앱 만들고 싶어" result={result} onBack={vi.fn()} />);

    expect(screen.getByText("예약 앱 만들고 싶어")).toBeInTheDocument();
    expect(screen.getByText("VibeLign 정리")).toBeInTheDocument();
    expect(screen.getByText("지오가 기획안을 한 번 검토했어요.")).toBeInTheDocument();
    expect(screen.getByText("저장 위치: plans/reservation-app.md")).toBeInTheDocument();
    expect(screen.queryByText(/model|모델|plan-structure/i)).not.toBeInTheDocument();
    expect(screen.queryByText("# 예약 앱")).not.toBeInTheDocument();
  });

  test("shows_markdown_pane_after_action", () => {
    render(<PlanningRoom prompt="예약 앱 만들고 싶어" result={result} onBack={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "기획안 보기" }));

    expect(screen.getByRole("heading", { name: "예약 앱" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "한 줄 목표" })).toBeInTheDocument();
  });

  test("renders_fallback_status_without_raw_error_output", () => {
    render(
      <PlanningRoom
        prompt="예약 앱 만들고 싶어"
        result={{
          ...result,
          fallbackReason: "cli_unavailable_template_only",
          llmStatus: "not_logged_in",
          details: "raw stderr",
        }}
        onBack={vi.fn()}
      />,
    );

    expect(screen.getByText("AI 연결은 아직 준비되지 않았지만, 기본 기획안은 저장했어요.")).toBeInTheDocument();
    expect(screen.queryByText("raw stderr")).not.toBeInTheDocument();
  });

  test("renders_pending_state_without_markdown_action", () => {
    render(
      <PlanningRoom
        prompt="예약 앱 만들고 싶어"
        result={{
          ...result,
          outputPath: null,
          markdown: null,
          llmStatus: "pending",
        }}
        onBack={vi.fn()}
      />,
    );

    expect(screen.getByText("지오가 기획안을 검토하는 중이에요.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기획안 보기" })).toBeDisabled();
  });
});
