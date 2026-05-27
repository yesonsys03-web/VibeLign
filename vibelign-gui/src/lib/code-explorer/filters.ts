import type { CodeFileEntry } from "../vib/types";

export function filterCodeFiles(files: CodeFileEntry[], query: string): CodeFileEntry[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return files;
  return files.filter((file) => [file.path, file.category, file.imports.join(" ")].join(" ").toLowerCase().includes(normalized));
}
