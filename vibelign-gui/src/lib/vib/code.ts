import { invoke } from "@tauri-apps/api/core";

import { normalizeBridgePath } from "./core";
import type { CodeFileEntry, CodeFileReadResult } from "./types";

export async function listCodeFiles(root: string): Promise<CodeFileEntry[]> {
  // 엔진 project_scan 은 anchor/patch_suggester 등 코드 분석 파이프라인과 공유되어
  // docs/*.md 같은 문서 파일이 제외된다. 사이드바는 별도의 Tauri 스캐너로 docs 를
  // 포함하는 더 넓은 트리를 보여준다 (코드 분석에는 영향 없음).
  const files = await invoke<CodeFileEntry[]>("list_code_files", { root });
  return [...files].sort((left, right) => left.path.localeCompare(right.path));
}

export async function readCodeFile(root: string, path: string): Promise<CodeFileReadResult> {
  return invoke<CodeFileReadResult>("read_code_file", {
    root,
    path: normalizeBridgePath(path),
  });
}
