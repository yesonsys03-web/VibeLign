import { describe, it, expect } from "vitest";
import { fallbackBadgeLabel } from "./PlanningMessages";
import type { PlanningChatMessage } from "../../lib/vib";

function msg(extra: Partial<PlanningChatMessage>): PlanningChatMessage {
  return { id: "m", role: "assistant", personaId: "chloe", content: "x", status: "ok", createdAt: "t", ...extra };
}

describe("fallbackBadgeLabel", () => {
  it("returns null when no providerUsed", () => {
    expect(fallbackBadgeLabel(msg({}))).toBeNull();
    expect(fallbackBadgeLabel(msg({ providerUsed: null }))).toBeNull();
  });
  it("labels the fallback provider when present", () => {
    expect(fallbackBadgeLabel(msg({ providerUsed: "codex" }))).toBe("codex로 대체됨");
  });
});
