// === ANCHOR: CODE_START ===
import { invoke } from "@tauri-apps/api/core";

import { normalizeBridgePath } from "./core";
import type { CodeFileEntry, CodeFileReadResult, CodeFileDiffResult, ChangedEntry } from "./types";

// === ANCHOR: CODE_LISTCODEFILES_START ===
export async function listCodeFiles(root: string): Promise<CodeFileEntry[]> {
  // 엔진 project_scan 은 anchor/project-map 등 코드 분석 파이프라인과 공유되어
  // docs/*.md 같은 문서 파일이 제외된다. 사이드바는 별도의 Tauri 스캐너로 docs 를
  // 포함하는 더 넓은 트리를 보여준다 (코드 분석에는 영향 없음).
  const files = await invoke<CodeFileEntry[]>("list_code_files", { root });
  return [...files].sort((left, right) => left.path.localeCompare(right.path));
}
// === ANCHOR: CODE_LISTCODEFILES_END ===

// === ANCHOR: CODE_READCODEFILE_START ===
export async function readCodeFile(root: string, path: string): Promise<CodeFileReadResult> {
  return invoke<CodeFileReadResult>("read_code_file", {
    root,
    path: normalizeBridgePath(path),
  });
}
// === ANCHOR: CODE_READCODEFILE_END ===

export async function readCodeFileDiff(root: string, path: string): Promise<CodeFileDiffResult> {
  return invoke<CodeFileDiffResult>("read_code_file_diff", {
    root,
    path: normalizeBridgePath(path),
  });
}

export async function listChangedFiles(root: string): Promise<ChangedEntry[]> {
  return invoke<ChangedEntry[]>("list_changed_files", { root });
}
// === ANCHOR: CODE_END ===
