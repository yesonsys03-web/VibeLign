import { invoke } from "@tauri-apps/api/core";

import type { CreatePlanningTemplateRequest, CreatePlanningTemplateResponse } from "./types";

export function createPlanningTemplate(
  request: CreatePlanningTemplateRequest,
): Promise<CreatePlanningTemplateResponse> {
  return invoke<CreatePlanningTemplateResponse>("create_planning_template", { request });
}
