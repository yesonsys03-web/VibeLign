// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TEST_START ===
import { describe, expect, test } from "vitest";

import type { PlanningChatSessionResponse } from "../../lib/vib";
import {
  appendMention,
  isSaveCommand,
  markAgentFailed,
  markMessagePending,
  matchingSlashCommands,
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

  test("detects_only_the_exact_slash_save_command", () => {
    // 결정적 입구: 정확히 /저장 일 때만 true (오발동 0).
    expect(isSaveCommand("/저장")).toBe(true);
    expect(isSaveCommand("   /저장   ")).toBe(true);
    // macOS 등에서 붙여넣은 NFD 분해형도 동일하게 인식해야 한다(NFC 정규화).
    expect(isSaveCommand("/저장".normalize("NFD"))).toBe(true);

    // 유사/오타/일반 문장은 트리거하지 않는다.
    expect(isSaveCommand("/저자")).toBe(false);
    expect(isSaveCommand("/저장해줘")).toBe(false);
    expect(isSaveCommand("이거 저장하면 좋겠다")).toBe(false);
    expect(isSaveCommand("저장")).toBe(false);
    expect(isSaveCommand("/save")).toBe(false);
    expect(isSaveCommand("")).toBe(false);
  });

  test("suggests_slash_commands_by_prefix_for_the_command_hint", () => {
    // "/" 또는 부분 입력이 커맨드의 prefix 이면 힌트로 제안한다(Tab 자동완성용).
    expect(matchingSlashCommands("/").map((c) => c.command)).toEqual(["/저장"]);
    expect(matchingSlashCommands("/저").map((c) => c.command)).toEqual(["/저장"]);
    expect(matchingSlashCommands("/저장").map((c) => c.command)).toEqual(["/저장"]);
    expect(matchingSlashCommands("   /저   ").map((c) => c.command)).toEqual(["/저장"]);
    // NFD 분해형 부분 입력도 동일하게 매칭(NFC 정규화).
    expect(matchingSlashCommands("/저".normalize("NFD")).map((c) => c.command)).toEqual(["/저장"]);

    // 커맨드를 벗어났거나 슬래시가 아니면 제안 없음.
    expect(matchingSlashCommands("/저장해줘")).toEqual([]);
    expect(matchingSlashCommands("/저자")).toEqual([]);
    expect(matchingSlashCommands("/save")).toEqual([]);
    expect(matchingSlashCommands("안녕")).toEqual([]);
    expect(matchingSlashCommands("")).toEqual([]);
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
