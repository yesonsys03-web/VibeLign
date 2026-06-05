// === ANCHOR: PLANNING_START ===
import { invoke } from "@tauri-apps/api/core";

import type {
  AppendPlanningChatTurnRequest,
  AppendPlanningAgentsRequest,
  CreatePlanningChatSessionRequest,
  CreatePlanningTemplateRequest,
  CreatePlanningTemplateResponse,
  PlanningChatSessionResponse,
  SavePlanningChatPlanRequest,
} from "./types";

// === ANCHOR: PLANNING_CREATEPLANNINGTEMPLATE_START ===
export function createPlanningTemplate(
  request: CreatePlanningTemplateRequest,
): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("create_planning_template", { request });
}
// === ANCHOR: PLANNING_CREATEPLANNINGTEMPLATE_END ===

// === ANCHOR: PLANNING_APPENDPLANNINGWITHAGENTS_START ===
export function appendPlanningWithAgents(
  request: AppendPlanningAgentsRequest,
): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("append_planning_with_agents", { request });
}
// === ANCHOR: PLANNING_APPENDPLANNINGWITHAGENTS_END ===

// === ANCHOR: PLANNING_LOADLATESTPLANNINGSESSION_START ===
export function loadLatestPlanningSession(projectDir: string): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("load_latest_planning_session", { projectDir });
}
// === ANCHOR: PLANNING_LOADLATESTPLANNINGSESSION_END ===

// === ANCHOR: PLANNING_CREATEPLANNINGCHATSESSION_START ===
export function createPlanningChatSession(
  request: CreatePlanningChatSessionRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("create_planning_chat_session", { request });
}
// === ANCHOR: PLANNING_CREATEPLANNINGCHATSESSION_END ===

// === ANCHOR: PLANNING_LOADLATESTPLANNINGCHATSESSION_START ===
export function loadLatestPlanningChatSession(projectDir: string): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("load_latest_planning_chat_session", { projectDir });
}
// === ANCHOR: PLANNING_LOADLATESTPLANNINGCHATSESSION_END ===

// === ANCHOR: PLANNING_APPENDPLANNINGCHATTURN_START ===
export function appendPlanningChatTurn(
  request: AppendPlanningChatTurnRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("append_planning_chat_turn", { request });
}
// === ANCHOR: PLANNING_APPENDPLANNINGCHATTURN_END ===

// === ANCHOR: PLANNING_SAVEPLANNINGCHATASMARKDOWN_START ===
export function savePlanningChatAsMarkdown(
  request: SavePlanningChatPlanRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("save_planning_chat_as_markdown", { request });
}
// === ANCHOR: PLANNING_SAVEPLANNINGCHATASMARKDOWN_END ===
// === ANCHOR: PLANNING_END ===
