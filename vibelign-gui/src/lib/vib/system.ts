import { invoke } from "@tauri-apps/api/core";
import { open as dialogOpen } from "@tauri-apps/plugin-dialog";

import type { ProjectSummary } from "./types";

export async function pickFile(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ multiple: false, defaultPath: defaultPath ?? undefined });
  return typeof result === "string" ? result : null;
}
export async function openFolder(path: string): Promise<void> {
  return invoke<void>("open_folder", { path });
}

export async function pickFolder(defaultPath?: string): Promise<string | null> {
  const result = await dialogOpen({ directory: true, multiple: false, defaultPath });
  return typeof result === "string" ? result : null;
}

/** vib 실행 파일 경로 반환. 없으면 null. */
export async function getVibPath(): Promise<string | null> {
  return invoke<string | null>("get_vib_path");
}

export async function saveRecentProjects(dirs: string[]): Promise<void> {
  return invoke<void>("save_recent_projects", { dirs });
}

export async function loadRecentProjects(): Promise<string[]> {
  return invoke<string[]>("load_recent_projects");
}

export async function readProjectSummary(dir: string): Promise<ProjectSummary> {
  return invoke<ProjectSummary>("read_project_summary", { dir });
}

export async function checkGitInstalled(): Promise<boolean> {
  return invoke<boolean>("check_git_installed");
}

export async function checkXcodeClt(): Promise<boolean> {
  return invoke<boolean>("check_xcode_clt");
}
