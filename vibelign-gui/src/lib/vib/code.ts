import { invoke } from "@tauri-apps/api/core";

import { callEngineDirect, normalizeBridgePath } from "./core";
import type { CodeFileEntry, CodeFileReadResult, ProjectScanResult } from "./types";

export async function listCodeFiles(root: string): Promise<CodeFileEntry[]> {
  const result = await callEngineDirect<ProjectScanResult>({
    command: "project_scan",
    root,
  });
  return [...(result.files ?? [])].sort((left, right) => left.path.localeCompare(right.path));
}

export async function readCodeFile(root: string, path: string): Promise<CodeFileReadResult> {
  return invoke<CodeFileReadResult>("read_code_file", {
    root,
    path: normalizeBridgePath(path),
  });
}
