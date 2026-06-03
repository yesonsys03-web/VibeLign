import { describe, expect, test } from "vitest";

import { buildPlanningWorkInstruction } from "./planningInstruction";

describe("buildPlanningWorkInstruction", () => {
  test("builds_saved_plan_work_instruction_for_official_cli_use", () => {
    const instruction = buildPlanningWorkInstruction({
      prompt: "예약 앱 만들고 싶어",
      outputPath: "plans/예약-앱-만들고-싶어.md",
    });

    expect(instruction).toContain("저장된 기획안: plans/예약-앱-만들고-싶어.md");
    expect(instruction).toContain("요청 요약: 예약 앱 만들고 싶어");
    expect(instruction).toContain("공식 CLI");
    expect(instruction).toContain("토큰, 쿠키, 세션 파일을 읽지 마세요");
  });

  test("builds_persona_specific_official_cli_instruction", () => {
    const instruction = buildPlanningWorkInstruction({
      prompt: "예약 앱 만들고 싶어",
      outputPath: "plans/예약-앱-만들고-싶어.md",
      persona: "gio",
    });

    expect(instruction).toContain("검토자 지오");
    expect(instruction).toContain("Codex CLI");
    expect(instruction).toContain("저장된 기획안: plans/예약-앱-만들고-싶어.md");
    expect(instruction).toContain("토큰, 쿠키, 세션 파일을 읽지 마세요");
  });
});
