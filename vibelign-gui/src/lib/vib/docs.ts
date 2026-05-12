import { invoke } from "@tauri-apps/api/core";

import { normalizeBridgePath, runVib } from "./core";
import type {
  DocSourcesResponse,
  DocsHtmlReadResult,
  DocsIndexEntry,
  DocsVisualReadResult,
  EnhanceDocResult,
  ReadFileResult,
} from "./types";

export async function readFile(root: string, path: string): Promise<ReadFileResult> {
  return invoke<ReadFileResult>("read_file", { root, path: normalizeBridgePath(path) });
}

export async function listDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("list_docs_index", { root });
}

export async function rebuildDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("rebuild_docs_index", { root });
}

export async function readDocsVisual(root: string, path: string): Promise<DocsVisualReadResult | null> {
  return invoke<DocsVisualReadResult | null>("read_docs_visual", { root, path: normalizeBridgePath(path) });
}

export async function readDocsHtml(root: string, path: string): Promise<DocsHtmlReadResult | null> {
  return invoke<DocsHtmlReadResult | null>("read_docs_html", { root, path: normalizeBridgePath(path) });
}

export async function listExtraDocSources(root: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("list_extra_doc_sources", { root });
}

export async function addExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("add_extra_doc_source", { root, path });
}

export async function removeExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("remove_extra_doc_source", { root, path });
}

export async function enhanceDocWithAi(
  root: string,
  path: string,
  models?: Record<string, string>,
): Promise<EnhanceDocResult> {
  const raw = await invoke<string>("enhance_doc_with_ai", {
    root,
    path: normalizeBridgePath(path),
    models: models ?? null,
  });
  return JSON.parse(raw) as EnhanceDocResult;
}

// ai-enhance 설정은 Settings 토글로만 바뀌고 같은 세션 동안 반복 조회되므로
// 프로젝트별 메모리 캐시로 중복 `vib config` subprocess 호출을 제거한다.
// Why: Doctor 페이지 mount 마다 `vib config --ai-enhance status` 가 PyInstaller
//      콜드스타트를 맞아 지연을 만들었다.
const aiEnhancementCache = new Map<string, boolean>();

export async function getAiEnhancement(cwd: string): Promise<boolean> {
  const cached = aiEnhancementCache.get(cwd);
  if (cached !== undefined) return cached;
  const res = await runVib(["config", "--ai-enhance", "status", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { ai_enhancement?: boolean } };
  const value = Boolean(parsed.data?.ai_enhancement);
  aiEnhancementCache.set(cwd, value);
  return value;
}

export async function setAiEnhancement(cwd: string, enabled: boolean): Promise<boolean> {
  const res = await runVib(["config", "--ai-enhance", enabled ? "enable" : "disable", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as { ok?: boolean; data?: { ai_enhancement?: boolean } };
  const value = Boolean(parsed.data?.ai_enhancement);
  aiEnhancementCache.set(cwd, value);
  return value;
}

export async function getManualJson(): Promise<Record<string, unknown>> {
  const res = await runVib(["manual", "--json"]);
  const raw = res.stdout.trim();
  if (!raw) {
    throw new Error(res.stderr || `exit ${res.exit_code}`);
  }
  const parsed = JSON.parse(raw) as unknown;
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    const data = parsed as Record<string, unknown>;
    if ("data" in data && data.data && typeof data.data === "object" && !Array.isArray(data.data)) {
      return data.data as Record<string, unknown>;
    }
    return data;
  }
  throw new Error("manual json parse failed");
}
