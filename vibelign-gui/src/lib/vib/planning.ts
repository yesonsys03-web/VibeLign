import { invoke } from "@tauri-apps/api/core";

import type { AppendPlanningAgentsRequest, CreatePlanningTemplateRequest, CreatePlanningTemplateResponse } from "./types";

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
