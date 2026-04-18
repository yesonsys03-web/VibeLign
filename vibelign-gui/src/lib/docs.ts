// === ANCHOR: DOCS_START ===
import { listDocsIndex, readFile, rebuildDocsIndex, type DocsIndexEntry, type ReadFileResult } from "./vib";

export interface DocsSection {
  id: string;
  text: string;
  level: number;
}

export const DOC_CATEGORY_ORDER = ["Context", "Readme", "Manual", "Wiki", "Spec", "Plan", "Root", "Docs"] as const;

// === ANCHOR: DOCS_CATEGORYCOLOR_START ===
export function categoryColor(category: string): string {
  switch (category) {
    case "Context": return "#4D9FFF";
    case "Readme": return "#FFB84D";
    case "Manual": return "#FF4D8B";
    case "Wiki": return "#4DFF91";
    case "Spec": return "#7B4DFF";
    case "Plan": return "#F5621E";
    case "Root": return "#888888";
    case "Docs": return "#3DBFA8";
    default: return "#1A1A1A";
  }
}
// === ANCHOR: DOCS_CATEGORYCOLOR_END ===

// === ANCHOR: DOCS_CATEGORYLABEL_START ===
export function categoryLabel(category: string): string {
  switch (category) {
    case "Context": return "Context";
    case "Readme": return "Readme";
    case "Manual": return "Manual";
    case "Wiki": return "Wiki";
    case "Spec": return "Spec";
    case "Plan": return "Plan";
    case "Root": return "Root";
    case "Docs": return "Docs";
    default: return category;
  }
}
// === ANCHOR: DOCS_CATEGORYLABEL_END ===

// === ANCHOR: DOCS_LOADDOCSINDEX_START ===
export async function loadDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return listDocsIndex(root);
}
// === ANCHOR: DOCS_LOADDOCSINDEX_END ===

// === ANCHOR: DOCS_RELOADDOCSINDEX_START ===
export async function reloadDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return rebuildDocsIndex(root);
}
// === ANCHOR: DOCS_RELOADDOCSINDEX_END ===

// === ANCHOR: DOCS_FILTERDOCSINDEX_START ===
export function filterDocsIndex(entries: DocsIndexEntry[], query: string): DocsIndexEntry[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return entries;
  return entries.filter((entry) => {
    const haystack = [entry.title, entry.path, entry.category].join(" ").toLowerCase();
    return haystack.includes(normalized);
  });
}
// === ANCHOR: DOCS_FILTERDOCSINDEX_END ===

// === ANCHOR: DOCS_FORMATDOCDATE_START ===
export function formatDocDate(timestamp: number): string {
  if (!Number.isFinite(timestamp)) return "";
  return new Date(timestamp).toLocaleString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
// === ANCHOR: DOCS_FORMATDOCDATE_END ===

// === ANCHOR: DOCS_NORMALIZEDOCPATH_START ===
export function normalizeDocPath(path: string): string {
  return path.replaceAll("\\", "/");
}
// === ANCHOR: DOCS_NORMALIZEDOCPATH_END ===

// === ANCHOR: DOCS_LOADDOC_START ===
export async function loadDoc(root: string, path: string): Promise<ReadFileResult> {
  return readFile(root, normalizeDocPath(path));
}
// === ANCHOR: DOCS_LOADDOC_END ===

// === ANCHOR: DOCS_SLUGIFYHEADING_START ===
export function slugifyHeading(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[`*_~]/g, "")
    .replace(/[^a-z0-9가-힣\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "section";
}
// === ANCHOR: DOCS_SLUGIFYHEADING_END ===

// === ANCHOR: DOCS_EXTRACTSECTIONS_START ===
export function extractSections(content: string): DocsSection[] {
  const counts = new Map<string, number>();
  return content
    .split("\n")
    .map((line) => line.match(/^(#{1,6})\s+(.+)$/))
    .filter((match): match is RegExpMatchArray => Boolean(match))
    .map((match) => {
      const text = match[2].trim();
      const baseId = slugifyHeading(text);
      const seen = counts.get(baseId) ?? 0;
      counts.set(baseId, seen + 1);
      return {
        id: seen === 0 ? baseId : `${baseId}-${seen + 1}`,
        text,
        level: match[1].length,
      };
    });
}
// === ANCHOR: DOCS_EXTRACTSECTIONS_END ===
// === ANCHOR: DOCS_END ===
