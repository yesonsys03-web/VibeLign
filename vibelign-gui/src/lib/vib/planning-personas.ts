import { invoke } from "@tauri-apps/api/core";

export type PlanningProviderId = "claude" | "codex" | "agy" | "opencode";

export interface PlanningPersonaConfig {
  enabled: boolean;
  role: string;
}

/** 페르소나 id → 설정. 비어있는 항목은 호출자가 기본값으로 채운다. */
export type PlanningPersonaConfigMap = Record<string, Partial<PlanningPersonaConfig>>;

export async function getPlanningPersonas(): Promise<PlanningPersonaConfigMap> {
  return (await invoke<PlanningPersonaConfigMap>("get_planning_personas")) ?? {};
}

export async function setPlanningPersonas(personas: PlanningPersonaConfigMap): Promise<void> {
  await invoke("set_planning_personas", { personas });
}

export async function probePlanningProviders(): Promise<string[]> {
  return (await invoke<string[]>("planning_provider_status")) ?? [];
}
