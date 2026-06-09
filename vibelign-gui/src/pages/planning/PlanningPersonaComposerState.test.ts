// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TEST_START ===
import { describe, expect, test } from "vitest";

import type { PlanningChatSessionResponse } from "../../lib/vib";
import {
  appendMention,
  markAgentFailed,
  markMessagePending,
  pendingAgentMessages,
  precedingUserPrompt,
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

  test("marks_only_the_pending_bubble_of_the_failed_agent", () => {
    // Given: chloe 는 정상 답변, gio 는 아직 대기
    const result: PlanningChatSessionResponse = {
      ...baseResult,
      messages: [
        { id: "u1", role: "user", personaId: null, content: "검토해줘", status: "ok", createdAt: "1" },
        { id: "a1", role: "assistant", personaId: "chloe", content: "클로이 답", status: "ok", createdAt: "1" },
        { id: "a2", role: "assistant", personaId: "gio", content: "지오가 답변을 준비하고 있어요.", status: "pending", createdAt: "1" },
      ],
    };

    // When
    const next = markAgentFailed(result, "gio", "2");

    // Then: gio 대기 → 실패, 나머지는 그대로
    expect(next.messages[1]).toMatchObject({ personaId: "chloe", status: "ok" });
    expect(next.messages[2]).toMatchObject({ personaId: "gio", status: "failed" });
    expect(next.messages[2].content).toContain("다시 시도");
  });

  test("marks_a_specific_message_pending_for_retry", () => {
    // Given
    const result: PlanningChatSessionResponse = {
      ...baseResult,
      messages: [
        { id: "a1", role: "assistant", personaId: "gio", content: "지오 호출에 실패했어요.", status: "failed", createdAt: "1" },
      ],
    };

    // When
    const next = markMessagePending(result, "a1");

    // Then
    expect(next.messages[0]).toMatchObject({ status: "pending" });
    expect(next.messages[0].content).toContain("준비하고");
  });

  test("finds_the_preceding_user_prompt_for_a_message", () => {
    // Given
    const messages = [
      { id: "u1", role: "user", personaId: null, content: "첫 질문", status: "ok", createdAt: "1" },
      { id: "a1", role: "assistant", personaId: "chloe", content: "답", status: "ok", createdAt: "1" },
      { id: "u2", role: "user", personaId: null, content: "둘째 질문", status: "ok", createdAt: "1" },
      { id: "a2", role: "assistant", personaId: "gio", content: "실패", status: "failed", createdAt: "1" },
    ] as const;

    // Then
    expect(precedingUserPrompt(messages, "a2")).toBe("둘째 질문");
    expect(precedingUserPrompt(messages, "a1")).toBe("첫 질문");
    expect(precedingUserPrompt(messages, "ghost")).toBe("둘째 질문"); // 못 찾으면 끝에서부터
    expect(precedingUserPrompt([], "x")).toBeNull();
  });
});
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TEST_END ===
