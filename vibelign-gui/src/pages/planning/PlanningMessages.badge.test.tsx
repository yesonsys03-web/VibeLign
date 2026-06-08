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
  it("appends the reason label when fallbackReason present", () => {
    expect(fallbackBadgeLabel(msg({ providerUsed: "claude", fallbackReason: "not_logged_in" })))
      .toBe("claude로 대체됨 · 로그인 필요");
    expect(fallbackBadgeLabel(msg({ providerUsed: "claude", fallbackReason: "not_installed" })))
      .toBe("claude로 대체됨 · 미설치");
  });
  it("falls back to plain label when reason unknown or absent", () => {
    expect(fallbackBadgeLabel(msg({ providerUsed: "claude" }))).toBe("claude로 대체됨");
    expect(fallbackBadgeLabel(msg({ providerUsed: "claude", fallbackReason: "weird" }))).toBe("claude로 대체됨");
  });
});
