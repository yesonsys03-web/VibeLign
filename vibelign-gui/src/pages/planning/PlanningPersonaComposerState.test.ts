// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TEST_START ===
import { describe, expect, test } from "vitest";

import type { PlanningChatSessionResponse } from "../../lib/vib";
import {
  appendMention,
  pendingAgentMessages,
  togglePersona,
  withPendingAgents,
  withPendingTurn,
} from "./PlanningPersonaComposerState";

const baseResult: PlanningChatSessionResponse = {
  ok: true,
  sessionId: "chat_1",
  prompt: "예약 앱",
  messages: [],
};

describe("PlanningPersonaComposerState", () => {
  test("appends_unique_mentions_when_the_persona_chip_is_selected", () => {
    // Given
    const current = "예약 앱 @클로이";

    // When
    const next = appendMention(current, "@클로이");
    const allNext = appendMention(next, "@모두");

    // Then
    expect(next).toBe("예약 앱 @클로이");
    expect(allNext).toBe("예약 앱 @클로이 @모두");
  });

  test("toggles_persona_selection_without_mutating_the_previous_selection", () => {
    // Given
    const current = ["gio"] as const;

    // When
    const added = togglePersona(current, "chloe");
    const removed = togglePersona(added, "gio");

    // Then
    expect(current).toEqual(["gio"]);
    expect(added).toEqual(["gio", "chloe"]);
    expect(removed).toEqual(["chloe"]);
  });

  test("composes_pending_user_and_persona_messages_for_the_visible_chat", () => {
    // Given
    const createdAt = "2026-06-03T00:00:00.000Z";

    // When
    const withTurn = withPendingTurn(baseResult, "검토해줘", ["gio", "mina"], createdAt);
    const pending = pendingAgentMessages(["chloe"], createdAt);
    const withAgents = withPendingAgents(baseResult, ["chloe"], createdAt);

    // Then
    expect(withTurn.messages).toHaveLength(3);
    expect(withTurn.messages[0]).toMatchObject({ role: "user", content: "검토해줘", status: "ok", createdAt });
    expect(withTurn.messages[1]).toMatchObject({
      role: "assistant",
      personaId: "gio",
      content: "지오가 답변을 준비하고 있어요.",
      status: "pending",
      createdAt,
    });
    expect(pending[0]).toMatchObject({ personaId: "chloe", content: "클로이가 답변을 준비하고 있어요." });
    expect(withAgents.messages).toHaveLength(1);
  });
});
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TEST_END ===
