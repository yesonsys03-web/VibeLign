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
  TrashedSessionSummary,
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

/** 저장 후 백그라운드 보강(준비상태·계약 AI 분석) — 저장을 즉시화하면서 분리한 무거운 부분. */
export function enrichPlanningChatPlan(
  request: SavePlanningChatPlanRequest,
): Promise<PlanningChatSessionResponse> {
  return invoke<PlanningChatSessionResponse>("enrich_planning_chat_plan", { request });
}

/** 턴 종료 직후 선행 분석(프리웜) — 미리 분석해 두면 저장 시 enrich 가 캐시 히트로 즉시 끝난다. */
export function prewarmPlanningEnrich(projectDir: string, sessionId: string): Promise<void> {
  return invoke<void>("prewarm_planning_enrich", { projectDir, sessionId });
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

/** 기획 세션 1개를 휴지통으로(소프트 삭제). 복구·자동정리(30일) 가능. */
export function deletePlanningChatSession(projectDir: string, sessionId: string): Promise<void> {
  return invoke<void>("delete_planning_chat_session", { projectDir, sessionId });
}

/** 휴지통의 기획 세션을 원위치로 복구. */
export function restorePlanningChatSession(projectDir: string, sessionId: string): Promise<void> {
  return invoke<void>("restore_planning_chat_session", { projectDir, sessionId });
}

/** 휴지통에 있는 기획안 목록. */
export function listTrashedPlanningSessions(projectDir: string): Promise<TrashedSessionSummary[]> {
  return invoke<TrashedSessionSummary[]>("list_trashed_planning_sessions", { projectDir });
}

/** 휴지통 전체 비우기(영구 삭제). */
export function emptyPlanningTrash(projectDir: string): Promise<void> {
  return invoke<void>("empty_planning_trash", { projectDir });
}
// === ANCHOR: PLANNING_SESSIONS_END ===
// === ANCHOR: PLANNING_END ===
