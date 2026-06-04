import { describe, expect, test } from "vitest";

import { getHelpAnswer } from "./helpData";

describe("helpData beginner surface", () => {
  test("omits_legacy_commands_from_primary_command_overview", () => {
    const answer = getHelpAnswer("무슨 명령어가 있어?");

    expect(answer).toContain("vib start");
    expect(answer).toContain("guard");
    expect(answer).not.toContain("patch");
    expect(answer).not.toContain("plan-structure");
  });

  test("does_not_route_patch_help_topic", () => {
    const answer = getHelpAnswer("patch");

    expect(answer).not.toContain("vib patch");
    expect(answer).not.toContain("패치");
  });

  test("does_not_route_plan_structure_help_topic", () => {
    const answer = getHelpAnswer("plan-structure");

    expect(answer).not.toContain("vib plan-structure");
    expect(answer).not.toContain("plan-structure");
  });
});
