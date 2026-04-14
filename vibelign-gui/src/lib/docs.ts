import { listDocsIndex, readFile, type DocsIndexEntry, type ReadFileResult } from "./vib";

export interface DocsSection {
  id: string;
  text: string;
  level: number;
}

export const DOC_CATEGORY_ORDER = ["Context", "Manual", "Wiki", "Spec", "Plan"] as const;

export function categoryColor(category: string): string {
  switch (category) {
    case "Context": return "#4D9FFF";
    case "Manual": return "#FF4D8B";
    case "Wiki": return "#4DFF91";
    case "Spec": return "#7B4DFF";
    case "Plan": return "#F5621E";
    default: return "#1A1A1A";
  }
}

export function categoryLabel(category: string): string {
  switch (category) {
    case "Context": return "Context";
    case "Manual": return "Manual";
    case "Wiki": return "Wiki";
    case "Spec": return "Spec";
    case "Plan": return "Plan";
    default: return category;
  }
}

export async function loadDocsIndex(root: string): Promise<DocsIndexEntry[]> {
  return listDocsIndex(root);
}

export function filterDocsIndex(entries: DocsIndexEntry[], query: string): DocsIndexEntry[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return entries;
  return entries.filter((entry) => {
    const haystack = [entry.title, entry.path, entry.category].join(" ").toLowerCase();
    return haystack.includes(normalized);
  });
}

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

export function normalizeDocPath(path: string): string {
  return path.replaceAll("\\", "/");
}

export async function loadDoc(root: string, path: string): Promise<ReadFileResult> {
  return readFile(root, normalizeDocPath(path));
}

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
