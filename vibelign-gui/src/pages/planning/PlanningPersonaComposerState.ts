import type { PlanningChatMessage, PlanningChatSessionResponse } from "../../lib/vib";
import { planningPersonaLabel } from "./PlanningPersonas";

export function togglePersona(current: readonly string[], personaId: string): readonly string[] {
  if (current.includes(personaId)) {
    return current.filter((id) => id !== personaId);
  }
  return [...current, personaId];
}

export function appendMention(current: string, mention: string): string {
  const words = current.trim().split(/\s+/).filter(Boolean);
  if (words.includes(mention)) {
    return current;
  }
  return [...words, mention].join(" ");
}

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
