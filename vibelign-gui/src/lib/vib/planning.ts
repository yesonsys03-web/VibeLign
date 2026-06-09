// === ANCHOR: PLANNING_START ===
import { invoke } from "@tauri-apps/api/core";

import type {
  AppendPlanningChatTurnRequest,
  AppendPlanningAgentsRequest,
  CardUpdateResponse,
  CreatePlanningChatSessionRequest,
  CreatePlanningTemplateRequest,
  CreatePlanningTemplateResponse,
  PlanningChatSessionResponse,
  PlanningSessionSummary,
  RetryPersonaRequest,
  SavePlanningChatPlanRequest,
  UpdateCardRequest,
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
// === ANCHOR: PLANNING_RETRYPLANNINGPERSONA_START ===
export function retryPlanningPersona(request: RetryPersonaRequest): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("retry_planning_persona", { request });
}
// === ANCHOR: PLANNING_RETRYPLANNINGPERSONA_END ===
// === ANCHOR: PLANNING_UPDATECARD_START ===
export function updateCard(request: UpdateCardRequest): Promise<CardUpdateResponse> {
  return invoke<CardUpdateResponse>("update_card", { request });
}
// === ANCHOR: PLANNING_UPDATECARD_END ===
// === ANCHOR: PLANNING_SESSIONS_START ===
export function listPlanningChatSessions(projectDir: string): Promise<PlanningSessionSummary[]> {
  return invoke<PlanningSessionSummary[]>("list_planning_chat_sessions", { projectDir });
}

export function loadPlanningChatSession(projectDir: string, sessionId: string): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("load_planning_chat_session", { projectDir, sessionId });
}
// === ANCHOR: PLANNING_SESSIONS_END ===
// === ANCHOR: PLANNING_END ===
