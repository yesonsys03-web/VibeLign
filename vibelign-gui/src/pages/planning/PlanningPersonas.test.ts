import { describe, expect, test } from "vitest";

import {
  allPlanningPersonaIds,
  planningPersonaLabel,
  planningPersonaMeta,
  PLANNING_PERSONAS,
} from "./PlanningPersonas";

describe("PlanningPersonas", () => {
  test("exposes_ordered_persona_metadata_for_planning_room_surfaces", () => {
    // Given
    const personas = PLANNING_PERSONAS;

    // When
    const ids = allPlanningPersonaIds();

    // Then
    expect(ids).toEqual(["chloe", "gio", "mina"]);
    expect(personas).toEqual([
      expect.objectContaining({ id: "chloe", label: "클로이", role: "설계", mention: "@클로이", initial: "클" }),
      expect.objectContaining({ id: "gio", label: "지오", role: "검토", mention: "@지오", initial: "지" }),
      expect.objectContaining({ id: "mina", label: "미나", role: "탐색", mention: "@미나", initial: "미" }),
    ]);
  });

  test("preserves_unknown_persona_fallback_metadata", () => {
    // Given
    const unknownId = "custom";

    // When
    const fallback = planningPersonaMeta(unknownId, "커스텀");

    // Then
    expect(planningPersonaLabel("gio")).toBe("지오");
    expect(planningPersonaLabel(unknownId)).toBe(unknownId);
    expect(fallback).toMatchObject({
      id: unknownId,
      label: "커스텀",
      role: "",
      mention: "",
      initial: "커",
      avatarBackground: "#FFFFFF",
      avatarBorder: "#1A1A1A",
      avatarColor: "#1A1A1A",
    });
  });
});
