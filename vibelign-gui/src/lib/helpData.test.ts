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
});
