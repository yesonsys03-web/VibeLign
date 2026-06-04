import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { COMMANDS } from "../../../lib/commands";
import { ManualCommandDetail } from "../ManualCommandDetail";

describe("ManualCommandDetail", () => {
  afterEach(() => {
    cleanup();
  });

  test("renders_selected_command_detail", () => {
    const command = COMMANDS[0];
    render(<ManualCommandDetail command={command} onBack={() => undefined} />);

    expect(screen.getByText(command.title)).toBeInTheDocument();
    expect(screen.getAllByText(command.usage).length).toBeGreaterThan(0);
    expect(screen.getByText(command.short)).toBeInTheDocument();
    expect(screen.getByText(command.desc)).toBeInTheDocument();
  });

  test("returns_to_manual_list_from_header_button", () => {
    const back = vi.fn();
    render(<ManualCommandDetail command={COMMANDS[0]} onBack={back} />);

    fireEvent.click(screen.getByRole("button", { name: "← 목록" }));

    expect(back).toHaveBeenCalledOnce();
  });
});
