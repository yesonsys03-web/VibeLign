import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { GuardResult } from "../../lib/vib";

import Home from "../Home";

const mocks = vi.hoisted(() => ({
  vibGuardMock: vi.fn<(...args: readonly [string]) => Promise<GuardResult>>(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => undefined),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    vibGuard: mocks.vibGuardMock,
  };
});

describe("Simple Home", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.vibGuardMock.mockReset();
    mocks.vibGuardMock.mockResolvedValue({
      status: "pass",
      summary: "ok",
      recommendations: [],
      issues: [],
    });
  });

  test("shows_three_beginner_blocks_by_default", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    expect(screen.getByText("프로젝트 안전 상태")).toBeInTheDocument();
    expect(screen.getByText("지금 할 일")).toBeInTheDocument();
    expect(screen.getByText("되돌리기")).toBeInTheDocument();
  });

  test("keeps_beginner_status_blocks_compact", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    const statusBlock = screen.getByText("프로젝트 안전 상태").closest("section");
    expect(statusBlock).toHaveStyle({ minHeight: "132px" });
  });

  test("keeps_home_content_close_to_header", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    const content = screen.getByText("프로젝트 안전 상태").closest(".page-content");
    expect(content).toHaveStyle({ padding: "12px 20px 20px" });
  });

  test("hides_legacy_terms_on_beginner_surface", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    expect(screen.queryByText(/vib patch/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/CodeSpeak/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/plan-structure/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/target_anchor/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/MCP/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/rules/i)).not.toBeInTheDocument();
  });

  test("keeps_existing_cards_reachable_in_advanced_area", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: "고급 기능 보기" }));

    expect(screen.getByTitle("카드 순서 초기화")).toBeInTheDocument();
  });

  test("returns_from_advanced_area_to_simple_home", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: "고급 기능 보기" }));
    fireEvent.click(screen.getByRole("button", { name: "간단히 보기" }));

    expect(screen.getByText("프로젝트 안전 상태")).toBeInTheDocument();
    expect(screen.queryByTitle("카드 순서 초기화")).not.toBeInTheDocument();
  });

  test("humanizes_watch_failure_on_beginner_surface", () => {
    const retry = vi.fn();
    render(
      <Home
        projectDir="/tmp/demo"
        onNavigate={() => undefined}
        watchError="unhandled backend exception"
        onRetryWatch={retry}
      />
    );

    expect(screen.getByText("자동 안전장치 일부가 꺼져 있어요")).toBeInTheDocument();
    expect(screen.getByText("파일 변경 감시를 시작하지 못했어요. 프로젝트 상태 확인은 계속 사용할 수 있어요.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.queryByText(/backend/i)).not.toBeInTheDocument();
  });

  test("shows_checkpoint_ready_state_when_backups_exist", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} hasCheckpoint />);

    expect(screen.getByText("최근 저장 지점이 있어요")).toBeInTheDocument();
    expect(screen.getByText("필요하면 이전 상태 후보를 확인할 수 있어요.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이전 상태로 돌아가기" })).toBeInTheDocument();
  });

  test("uses_history_copy_when_no_checkpoint_exists", () => {
    const navigate = vi.fn();
    render(<Home projectDir="/tmp/demo" onNavigate={navigate} />);

    fireEvent.click(screen.getByRole("button", { name: "저장 기록 확인하기" }));

    expect(navigate).toHaveBeenCalledWith("backups");
    expect(screen.queryByRole("button", { name: "이전 상태로 돌아가기" })).not.toBeInTheDocument();
  });

  test("runs_guard_from_beginner_next_action", async () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: "상태 확인하기" }));

    expect(mocks.vibGuardMock).toHaveBeenCalledWith("/tmp/demo");
    expect(await screen.findByText("안전장치가 켜져 있어요")).toBeInTheDocument();
    expect(screen.getByText("바로 AI 코딩해도 괜찮아요")).toBeInTheDocument();
  });

  test("describes_beginner_guard_action_as_available_on_home", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    expect(screen.getByText("아래 버튼으로 프로젝트 상태를 바로 확인할 수 있어요.")).toBeInTheDocument();
    expect(screen.queryByText("고급 기능에서 상태 확인을 실행할 수 있어요.")).not.toBeInTheDocument();
  });
});
