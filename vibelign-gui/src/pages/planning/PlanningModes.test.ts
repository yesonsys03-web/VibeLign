// === ANCHOR: PLANNINGMODES_TEST_START ===
import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";

import { allPlanningPersonaIds, planningPersonaLabel } from "./PlanningPersonas";
import { DEFAULT_PLANNING_MODE, PLANNING_MODE_OPTIONS, resolvePlanningMode } from "./PlanningModes";

describe("PlanningModes", () => {
  test("keeps_instant_mode_as_the_default_gio_review_path", () => {
    // Given
    const defaultMode = DEFAULT_PLANNING_MODE;

    // When
    const resolved = resolvePlanningMode("instant");

    // Then
    expect(defaultMode).toMatchObject({ id: "instant", label: "Instant", targetLabel: "지오", personaIds: ["gio"] });
    expect(resolved).toBe(defaultMode);
  });

  test("derives_full_mode_personas_from_planning_persona_metadata", () => {
    // Given
    const allPersonaIds = allPlanningPersonaIds();

    // When
    const fullMode = resolvePlanningMode("full");
    const fallbackMode = resolvePlanningMode("unknown");

    // Then
    expect(PLANNING_MODE_OPTIONS.map((option) => option.id)).toEqual(["instant", "draft", "explore", "assist", "full"]);
    expect(fullMode.personaIds).toEqual(allPersonaIds);
    expect(fallbackMode).toBe(DEFAULT_PLANNING_MODE);
  });

  test("exposes_mina_as_a_standalone_explore_mode", () => {
    // When
    const exploreMode = resolvePlanningMode("explore");

    // Then
    expect(exploreMode.targetLabel).toBe(planningPersonaLabel("mina"));
    expect(exploreMode.personaIds).toEqual(["mina"]);
  });

  test("derives_single_persona_target_labels_from_planning_persona_metadata", () => {
    // Given
    const source = readFileSync("src/pages/planning/PlanningModes.ts", "utf-8");

    // When
    const instantMode = resolvePlanningMode("instant");
    const draftMode = resolvePlanningMode("draft");

    // Then
    expect(instantMode.targetLabel).toBe(planningPersonaLabel("gio"));
    expect(draftMode.targetLabel).toBe(planningPersonaLabel("chloe"));
    expect(source).not.toContain('targetLabel: "지오"');
    expect(source).not.toContain('targetLabel: "클로이"');
  });
});
// === ANCHOR: PLANNINGMODES_TEST_END ===
