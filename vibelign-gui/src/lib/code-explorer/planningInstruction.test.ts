// === ANCHOR: PLANNINGINSTRUCTION_TEST_START ===
import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";

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

  test("derives_persona_labels_from_planning_persona_metadata", () => {
    const helperSource = readFileSync("src/lib/code-explorer/planningInstruction.ts", "utf8");
    const actionsSource = readFileSync("src/components/code-explorer/PlanningInstructionActions.tsx", "utf8");

    expect(helperSource).not.toContain('label: "설계자 클로이"');
    expect(helperSource).not.toContain('label: "검토자 지오"');
    expect(helperSource).not.toContain('label: "탐색자 미나"');
    expect(actionsSource).not.toContain('label: "클로이 Claude"');
    expect(actionsSource).not.toContain('label: "지오 Codex"');
    expect(actionsSource).not.toContain('label: "미나 Antigravity"');
  });

  const CONTRACT = {
    version: 1,
    extractedAt: "1",
    goal: "예약 화면을 만든다",
    scope: [
      { path: "src/pages/Home.tsx", kind: "file" as const, reason: "예약 진입 버튼" },
      { path: "src/components/nav/", kind: "dir" as const, reason: "이동 안내" },
    ],
    exclusions: ["결제 흐름은 건드리지 않음"],
    doneCriteria: ["예약 버튼을 누르면 예약 화면이 뜬다"],
  };

  test("injects_contract_block_when_contract_present", () => {
    const instruction = buildPlanningWorkInstruction({
      prompt: "예약 앱 만들고 싶어",
      outputPath: "plans/예약.md",
      contract: CONTRACT,
    });

    expect(instruction).toContain("이번 작업의 계약(기획안에서 추출):");
    expect(instruction).toContain("- 목표: 예약 화면을 만든다");
    expect(instruction).toContain("- 손댈 범위(이 밖은 건드리기 전에 사용자에게 확인): src/pages/Home.tsx, src/components/nav/");
    expect(instruction).toContain("- 건드리지 말 것: 결제 흐름은 건드리지 않음");
    expect(instruction).toContain("- 완료 기준: 예약 버튼을 누르면 예약 화면이 뜬다");
    expect(instruction).toContain("토큰, 쿠키, 세션 파일을 읽지 마세요"); // 기존 안전 수칙 유지
  });

  test("omits_scope_line_when_scope_empty_and_is_identical_without_contract", () => {
    const scopeless = buildPlanningWorkInstruction({
      prompt: "p",
      outputPath: "plans/p.md",
      contract: { ...CONTRACT, scope: [], exclusions: [], doneCriteria: [] },
    });
    expect(scopeless).toContain("- 목표: 예약 화면을 만든다");
    expect(scopeless).not.toContain("손댈 범위");

    // 계약 부재 = 현행 출력과 완전 동일(퇴행 0 — spec §5·§8)
    const without = buildPlanningWorkInstruction({ prompt: "p", outputPath: "plans/p.md" });
    const withNull = buildPlanningWorkInstruction({ prompt: "p", outputPath: "plans/p.md", contract: null });
    expect(withNull).toBe(without);
  });
});
// === ANCHOR: PLANNINGINSTRUCTION_TEST_END ===
