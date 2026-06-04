import { describe, expect, test } from "vitest";

import { BEGINNER_COMMANDS, COMMANDS, getPlanStructureCommand } from "./commands";

describe("legacy command surface", () => {
  test("removes_patch_and_keeps_plan_structure_legacy", () => {
    expect(COMMANDS.map((command) => command.name)).not.toContain("patch");
    expect(getPlanStructureCommand().visibility).toBe("legacy");
  });

  test("keeps_legacy_commands_out_of_beginner_command_list", () => {
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("patch");
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("plan-structure");
  });
});
