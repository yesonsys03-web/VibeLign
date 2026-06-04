import { describe, expect, test } from "vitest";

import { BEGINNER_COMMANDS, COMMANDS, getPatchCommand } from "./commands";

describe("legacy command surface", () => {
  test("marks_patch_and_plan_structure_as_legacy", () => {
    expect(getPatchCommand().visibility).toBe("legacy");
    expect(COMMANDS.find((command) => command.name === "plan-structure")?.visibility).toBe("legacy");
  });

  test("keeps_legacy_commands_out_of_beginner_command_list", () => {
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("patch");
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("plan-structure");
  });
});
