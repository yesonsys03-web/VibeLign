// === ANCHOR: SYSTEM_START ===
import { invoke } from "@tauri-apps/api/core";
import { open as dialogOpen } from "@tauri-apps/plugin-dialog";

import type { ProjectSummary } from "./types";

// === ANCHOR: SYSTEM_PICKFILE_START ===
export async function pickFile(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ multiple: false, defaultPath: defaultPath ?? undefined });
  return typeof result === "string" ? result : null;
}
// === ANCHOR: SYSTEM_PICKFILE_END ===
// === ANCHOR: SYSTEM_OPENFOLDER_START ===
export async function openFolder(path: string): Promise<void> {
  return invoke<void>("open_folder", { path });
}
// === ANCHOR: SYSTEM_OPENFOLDER_END ===

// === ANCHOR: SYSTEM_PICKFOLDER_START ===
export async function pickFolder(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ directory: true, multiple: false, defaultPath });
  return typeof result === "string" ? result : null;
}
// === ANCHOR: SYSTEM_PICKFOLDER_END ===

/** vib 실행 파일 경로 반환. 없으면 null. */
// === ANCHOR: SYSTEM_GETVIBPATH_START ===
export async function getVibPath(): Promise<string | null> {
  return invoke<string | null>("get_vib_path");
}
// === ANCHOR: SYSTEM_GETVIBPATH_END ===

// === ANCHOR: SYSTEM_SAVERECENTPROJECTS_START ===
export async function saveRecentProjects(dirs: string[]): Promise<void> {
  return invoke<void>("save_recent_projects", { dirs });
}
// === ANCHOR: SYSTEM_SAVERECENTPROJECTS_END ===

// === ANCHOR: SYSTEM_LOADRECENTPROJECTS_START ===
export async function loadRecentProjects(): Promise<string[]> {
  return invoke<string[]>("load_recent_projects");
}
// === ANCHOR: SYSTEM_LOADRECENTPROJECTS_END ===

// === ANCHOR: SYSTEM_READPROJECTSUMMARY_START ===
export async function readProjectSummary(dir: string): Promise<ProjectSummary> {
  return invoke<ProjectSummary>("read_project_summary", { dir });
}
// === ANCHOR: SYSTEM_READPROJECTSUMMARY_END ===

// === ANCHOR: SYSTEM_CHECKGITINSTALLED_START ===
export async function checkGitInstalled(): Promise<boolean> {
  return invoke<boolean>("check_git_installed");
}
// === ANCHOR: SYSTEM_CHECKGITINSTALLED_END ===

// === ANCHOR: SYSTEM_CHECKXCODECLT_START ===
export async function checkXcodeClt(): Promise<boolean> {
  return invoke<boolean>("check_xcode_clt");
}
// === ANCHOR: SYSTEM_CHECKXCODECLT_END ===
// === ANCHOR: SYSTEM_END ===
