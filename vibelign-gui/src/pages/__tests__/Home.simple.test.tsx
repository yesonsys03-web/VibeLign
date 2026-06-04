import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import Home from "../Home";

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => undefined),
}));

describe("Simple Home", () => {
  afterEach(() => {
    cleanup();
  });

  test("shows_three_beginner_blocks_by_default", () => {
    render(<Home projectDir="/tmp/demo" onNavigate={() => undefined} />);

    expect(screen.getByText("프로젝트 안전 상태")).toBeInTheDocument();
    expect(screen.getByText("지금 할 일")).toBeInTheDocument();
    expect(screen.getByText("되돌리기")).toBeInTheDocument();
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
  });
});
