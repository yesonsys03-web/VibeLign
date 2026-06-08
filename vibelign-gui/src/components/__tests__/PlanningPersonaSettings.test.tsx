import { describe, it, expect } from "vitest";
import {
  PLANNING_PROVIDER_OPTIONS,
  applyPersonaChange,
  effectivePersona,
} from "../PlanningPersonaSettings";

describe("PlanningPersonaSettings logic", () => {
  it("exposes the four provider options", () => {
    expect(PLANNING_PROVIDER_OPTIONS).toEqual(["claude", "codex", "agy", "opencode"]);
  });

  it("effectivePersona falls back to default provider and enabled=true", () => {
    expect(effectivePersona({}, "chloe")).toEqual({ enabled: true, provider: "claude" });
    expect(effectivePersona({ chloe: { provider: "codex" } }, "chloe")).toEqual({ enabled: true, provider: "codex" });
    expect(effectivePersona({ gio: { enabled: false } }, "gio")).toEqual({ enabled: false, provider: "codex" });
  });

  it("applyPersonaChange writes a full entry without touching others", () => {
    const next = applyPersonaChange({ mina: { provider: "agy" } }, "chloe", { enabled: false });
    expect(next.chloe).toEqual({ enabled: false, provider: "claude" });
    expect(next.mina).toEqual({ provider: "agy" });
  });
});
