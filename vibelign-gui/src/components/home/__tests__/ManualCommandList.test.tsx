import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { COMMANDS, getPatchCommand, getPlanStructureCommand } from "../../../lib/commands";
import { ManualCommandList } from "../ManualCommandList";

describe("ManualCommandList", () => {
  afterEach(() => {
    cleanup();
  });

  test("renders_command_count_and_selects_a_command", () => {
    const selectCommand = vi.fn();
    render(<ManualCommandList onBack={() => undefined} onSelectCommand={selectCommand} />);

    const firstCommand = COMMANDS[0];
    expect(screen.getByText("MANUAL")).toBeInTheDocument();
    expect(screen.getByText(`커맨드 ${COMMANDS.length}개`)).toBeInTheDocument();
    fireEvent.click(screen.getByText(firstCommand.title));

    expect(selectCommand).toHaveBeenCalledWith(firstCommand);
  });

  test("returns_to_home_from_header_button", () => {
    const back = vi.fn();
    render(<ManualCommandList onBack={back} onSelectCommand={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: "← 홈" }));

    expect(back).toHaveBeenCalledOnce();
  });

  test("keeps_legacy_commands_findable_with_badges", () => {
    const selectCommand = vi.fn();
    const patchCommand = getPatchCommand();
    const planStructureCommand = getPlanStructureCommand();

    render(<ManualCommandList onBack={() => undefined} onSelectCommand={selectCommand} />);

    expect(screen.getByText(patchCommand.title)).toBeInTheDocument();
    expect(screen.getByText(planStructureCommand.title)).toBeInTheDocument();
    expect(screen.getAllByText("legacy")).toHaveLength(2);

    fireEvent.click(screen.getByText(patchCommand.title));

    expect(selectCommand).toHaveBeenCalledWith(patchCommand);
  });
});
