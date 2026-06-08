import { describe, it, expect } from "vitest";
import { PLANNING_ROLE_OPTIONS, effectivePersona, applyRoleSwap } from "../PlanningPersonaSettings";

describe("PlanningPersonaSettings role swap", () => {
  it("exposes the four roles in order", () => {
    expect(PLANNING_ROLE_OPTIONS.map((r) => r.id)).toEqual(["design", "review", "explore", "assist"]);
  });

  it("effectivePersona falls back to default role + enabled true", () => {
    expect(effectivePersona({}, "chloe")).toEqual({ enabled: true, role: "design" });
    expect(effectivePersona({ gio: { role: "design" } }, "gio")).toEqual({ enabled: true, role: "design" });
    expect(effectivePersona({ mina: { enabled: false } }, "mina")).toEqual({ enabled: false, role: "explore" });
  });

  it("applyRoleSwap swaps with whoever currently holds the target role", () => {
    // defaults: chloe=design, gio=review. Give chloe 'review' -> gio gets chloe's old 'design'.
    const next = applyRoleSwap({}, "chloe", "review");
    expect(next.chloe.role).toBe("review");
    expect(next.gio.role).toBe("design");
  });

  it("applyRoleSwap is a no-op when assigning the same role", () => {
    expect(applyRoleSwap({}, "chloe", "design")).toEqual({});
  });
});
