// === ANCHOR: DOCS_START ===
import { invoke } from "@tauri-apps/api/core";

import { callEngineDirect, normalizeBridgePath, runVib } from "./core";
import type {
  DocSourcesResponse,
  DocsHtmlReadResult,
  DocsIndexEntry,
  DocsVisualReadResult,
  EnhanceDocResult,
  ReadFileResult,
} from "./types";

// === ANCHOR: DOCS_READFILE_START ===
export async function readFile(root: string, path: string): Promise<ReadFileResult> {
  return invoke<ReadFileResult>("read_file", { root, path: normalizeBridgePath(path) });
}
// === ANCHOR: DOCS_READFILE_END ===

// === ANCHOR: DOCS_LISTDOCSINDEX_START ===
export async function listDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("list_docs_index", { root });
}
// === ANCHOR: DOCS_LISTDOCSINDEX_END ===

// === ANCHOR: DOCS_REBUILDDOCSINDEX_START ===
export async function rebuildDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return invoke<DocsIndexEntry[]>("rebuild_docs_index", { root });
}
// === ANCHOR: DOCS_REBUILDDOCSINDEX_END ===

// === ANCHOR: DOCS_READDOCSVISUAL_START ===
export async function readDocsVisual(root: string, path: string): Promise<DocsVisualReadResult | null> {
  return invoke<DocsVisualReadResult | null>("read_docs_visual", { root, path: normalizeBridgePath(path) });
}
// === ANCHOR: DOCS_READDOCSVISUAL_END ===

// === ANCHOR: DOCS_READDOCSHTML_START ===
export async function readDocsHtml(root: string, path: string): Promise<DocsHtmlReadResult | null> {
  return invoke<DocsHtmlReadResult | null>("read_docs_html", { root, path: normalizeBridgePath(path) });
}
// === ANCHOR: DOCS_READDOCSHTML_END ===

// === ANCHOR: DOCS_LISTEXTRADOCSOURCES_START ===
export async function listExtraDocSources(root: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("list_extra_doc_sources", { root });
}
// === ANCHOR: DOCS_LISTEXTRADOCSOURCES_END ===

// === ANCHOR: DOCS_ADDEXTRADOCSOURCE_START ===
export async function addExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("add_extra_doc_source", { root, path });
}
// === ANCHOR: DOCS_ADDEXTRADOCSOURCE_END ===

// === ANCHOR: DOCS_REMOVEEXTRADOCSOURCE_START ===
export async function removeExtraDocSource(root: string, path: string): Promise<DocSourcesResponse> {
  return invoke<DocSourcesResponse>("remove_extra_doc_source", { root, path });
}
// === ANCHOR: DOCS_REMOVEEXTRADOCSOURCE_END ===

// === ANCHOR: DOCS_ENHANCEDOCWITHAI_START ===
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
// === ANCHOR: DOCS_ENHANCEDOCWITHAI_END ===

// === ANCHOR: DOCS_GETAIENHANCEMENT_START ===
export async function getAiEnhancement(cwd: string): Promise<boolean> {
  const parsed = await callEngineDirect<{ enabled?: boolean }>({
    command: "ai_enhancement_status",
    root: cwd,
  });
  return Boolean(parsed.enabled);
}
// === ANCHOR: DOCS_GETAIENHANCEMENT_END ===

// === ANCHOR: DOCS_SETAIENHANCEMENT_START ===
export async function setAiEnhancement(cwd: string, enabled: boolean): Promise<boolean> {
  const parsed = await callEngineDirect<{ enabled?: boolean }>({
    command: "ai_enhancement_set",
    root: cwd,
    enabled,
  });
  return Boolean(parsed.enabled);
}
// === ANCHOR: DOCS_SETAIENHANCEMENT_END ===

// === ANCHOR: DOCS_GETMANUALJSON_START ===
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
// === ANCHOR: DOCS_GETMANUALJSON_END ===
// === ANCHOR: DOCS_END ===
