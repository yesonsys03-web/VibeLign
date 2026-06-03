// === ANCHOR: FILTERS_START ===
import type { CodeFileEntry } from "../vib/types";

// === ANCHOR: FILTERS_FILTERCODEFILES_START ===
export function filterCodeFiles(files: CodeFileEntry[], query: string): CodeFileEntry[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return files;
  return files.filter((file) => [file.path, file.category, file.imports.join(" ")].join(" ").toLowerCase().includes(normalized));
}
// === ANCHOR: FILTERS_FILTERCODEFILES_END ===
// === ANCHOR: FILTERS_END ===
