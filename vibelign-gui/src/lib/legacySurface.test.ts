// === ANCHOR: LEGACYSURFACE_TEST_START ===
import { describe, expect, test } from "vitest";

import { BEGINNER_COMMANDS, COMMANDS } from "./commands";

describe("legacy command surface", () => {
  test("removes_patch_and_plan_structure_commands", () => {
    expect(COMMANDS.map((command) => command.name)).not.toContain("patch");
    expect(COMMANDS.map((command) => command.name)).not.toContain("plan-structure");
  });

  test("keeps_legacy_commands_out_of_beginner_command_list", () => {
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("patch");
    expect(BEGINNER_COMMANDS.map((command) => command.name)).not.toContain("plan-structure");
  });
});
// === ANCHOR: LEGACYSURFACE_TEST_END ===
