import { invoke } from "@tauri-apps/api/core";

import type {
  AppendPlanningChatTurnRequest,
  AppendPlanningAgentsRequest,
  CreatePlanningChatSessionRequest,
  CreatePlanningTemplateRequest,
  CreatePlanningTemplateResponse,
  PlanningChatSessionResponse,
} from "./types";

export function createPlanningTemplate(
  request: CreatePlanningTemplateRequest,
): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("create_planning_template", { request });
}

export function appendPlanningWithAgents(
  request: AppendPlanningAgentsRequest,
): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("append_planning_with_agents", { request });
}

export function loadLatestPlanningSession(projectDir: string): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("load_latest_planning_session", { projectDir });
}

export function createPlanningChatSession(
  request: CreatePlanningChatSessionRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("create_planning_chat_session", { request });
}

export function loadLatestPlanningChatSession(projectDir: string): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("load_latest_planning_chat_session", { projectDir });
}

export function appendPlanningChatTurn(
  request: AppendPlanningChatTurnRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("append_planning_chat_turn", { request });
}
