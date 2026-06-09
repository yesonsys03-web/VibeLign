// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_START ===
import type { PlanningChatMessage, PlanningChatSessionResponse } from "../../lib/vib";
import { planningPersonaLabel } from "./PlanningPersonas";

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_ISSAVECOMMAND_START ===
/// `/저장` 슬래시 저장 입구 감지. 결정적 매칭(정확히 "/저장")이라 오발동 0.
/// NFC 정규화로 NFD 분해형 붙여넣기(특히 macOS産 텍스트)도 동일하게 인식한다.
export const SLASH_SAVE_COMMAND = "/저장";

export function isSaveCommand(message: string): boolean {
  return message.trim().normalize("NFC") === SLASH_SAVE_COMMAND;
}

export interface PlanningSlashCommand {
  readonly command: string;
  readonly label: string;
}

/// 입력란에서 `/` 입력 시 보여줄 커맨드 목록(Tab/클릭 자동완성용).
export const PLANNING_SLASH_COMMANDS: readonly PlanningSlashCommand[] = [
  { command: SLASH_SAVE_COMMAND, label: "기획안 저장" },
];

/// 현재 입력의 prefix 에 매칭되는 슬래시 커맨드 제안. `/` 로 시작할 때만 동작.
/// NFC 정규화로 NFD 부분 입력도 동일하게 인식한다.
export function matchingSlashCommands(message: string): readonly PlanningSlashCommand[] {
  const normalized = message.trim().normalize("NFC");
  if (!normalized.startsWith("/")) {
    return [];
  }
  return PLANNING_SLASH_COMMANDS.filter((entry) => entry.command.startsWith(normalized));
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_ISSAVECOMMAND_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TOGGLEPERSONA_START ===
export function togglePersona(current: readonly string[], personaId: string): readonly string[] {
  if (current.includes(personaId)) {
    return current.filter((id) => id !== personaId);
  }
  return [...current, personaId];
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_TOGGLEPERSONA_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_APPENDMENTION_START ===
export function appendMention(current: string, mention: string): string {
  const words = current.trim().split(/\s+/).filter(Boolean);
  if (words.includes(mention)) {
    return current;
  }
  return [...words, mention].join(" ");
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_APPENDMENTION_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_WITHPENDINGTURN_START ===
export function withPendingTurn(
  result: PlanningChatSessionResponse,
  prompt: string,
  agents: readonly string[],
  createdAt: string,
): PlanningChatSessionResponse {
  const userMessage: PlanningChatMessage = {
    id: `pending_user_${Date.now()}`,
    role: "user",
    personaId: null,
    content: prompt,
    status: "ok",
    createdAt,
  };
  return {
    ...result,
    messages: [
      ...result.messages,
      userMessage,
      ...pendingAgentMessages(agents, createdAt),
    ],
  };
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_WITHPENDINGTURN_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_WITHPENDINGAGENTS_START ===
export function withPendingAgents(
  result: PlanningChatSessionResponse,
  agents: readonly string[],
  createdAt: string,
): PlanningChatSessionResponse {
  if (agents.length === 0) {
    return result;
  }
  return {
    ...result,
    messages: [
      ...result.messages,
      ...pendingAgentMessages(agents, createdAt),
    ],
  };
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_WITHPENDINGAGENTS_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_PENDINGAGENTMESSAGES_START ===
export function pendingAgentMessages(agents: readonly string[], createdAt: string): readonly PlanningChatMessage[] {
  return agents.map((agent, index) => ({
    id: `pending_${agent}_${Date.now()}_${index}`,
    role: "assistant",
    personaId: agent,
    content: `${planningPersonaLabel(agent)}가 답변을 준비하고 있어요.`,
    status: "pending",
    createdAt,
  }));
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_PENDINGAGENTMESSAGES_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_MARKAGENTFAILED_START ===
/// 해당 페르소나의 대기(pending) 말풍선을 실패(failed)로 바꾼다.
/// 하드 에러로 호출이 실패해도 나머지 페르소나는 계속 진행하므로, 멈춘 대기 말풍선을 정리한다.
export function markAgentFailed(
  result: PlanningChatSessionResponse,
  agent: string,
  createdAt: string,
): PlanningChatSessionResponse {
  return {
    ...result,
    messages: result.messages.map((message) =>
      message.personaId === agent && message.status === "pending"
        ? {
            ...message,
            status: "failed",
            content: `${planningPersonaLabel(agent)} 호출에 실패했어요. 다시 시도해 주세요.`,
            createdAt,
          }
        : message,
    ),
  };
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_MARKAGENTFAILED_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_MARKMESSAGEPENDING_START ===
/// 재시도 시 해당 메시지를 다시 대기 상태로 표시한다(낙관적 UI).
export function markMessagePending(
  result: PlanningChatSessionResponse,
  messageId: string,
): PlanningChatSessionResponse {
  return {
    ...result,
    messages: result.messages.map((message) =>
      message.id === messageId
        ? {
            ...message,
            status: "pending",
            content: `${planningPersonaLabel(message.personaId ?? "")}가 답변을 준비하고 있어요.`,
          }
        : message,
    ),
  };
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_MARKMESSAGEPENDING_END ===

// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_PRECEDINGUSERPROMPT_START ===
/// 주어진 메시지 바로 앞의 사용자 발화 내용을 찾는다(재시도 시 그 턴의 프롬프트).
/// 못 찾으면 null.
export function precedingUserPrompt(
  messages: readonly PlanningChatMessage[],
  messageId: string,
): string | null {
  const index = messages.findIndex((message) => message.id === messageId);
  const from = index >= 0 ? index : messages.length;
  for (let i = from - 1; i >= 0; i -= 1) {
    if (messages[i].role === "user") {
      return messages[i].content;
    }
  }
  return null;
}
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_PRECEDINGUSERPROMPT_END ===
// === ANCHOR: PLANNINGPERSONACOMPOSERSTATE_END ===
