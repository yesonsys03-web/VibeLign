import { categoryColor, categoryLabel, DOC_CATEGORY_ORDER, filterDocsIndex, formatDocDate } from "../../lib/docs";
import type { DocsIndexEntry } from "../../lib/vib";

interface DocsSidebarProps {
  docs: DocsIndexEntry[];
  query: string;
  selectedPath: string | null;
  onQueryChange: (value: string) => void;
  onSelect: (path: string) => void;
}

export default function DocsSidebar({ docs, query, selectedPath, onQueryChange, onSelect }: DocsSidebarProps) {
  const filtered = filterDocsIndex(docs, query);
  const orderedCategories = DOC_CATEGORY_ORDER.filter((category) => filtered.some((entry) => entry.category === category));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="card">
        <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
          Search Docs
        </div>
        <input
          className="input-field"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="제목, 경로, 카테고리 검색..."
        />
      </div>

      <div className="card" style={{ minHeight: 0, flex: 1, overflowY: "auto" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
          Document Index
        </div>

        {filtered.length === 0 ? (
          <div style={{ fontSize: 12, color: "#666", lineHeight: 1.6 }}>검색 결과가 없습니다.</div>
        ) : orderedCategories.map((category) => (
          <div key={category} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ width: 10, height: 10, background: categoryColor(category), border: "1px solid #1A1A1A" }} />
              <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>{categoryLabel(category)}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {filtered.filter((entry) => entry.category === category).map((entry) => {
                const active = entry.path === selectedPath;
                return (
                  <button
                    key={entry.path}
                    className="btn btn-ghost btn-sm"
                    style={{
                      textAlign: "left",
                      justifyContent: "flex-start",
                      alignItems: "flex-start",
                      background: active ? "#1A1A1A" : undefined,
                      color: active ? "#fff" : undefined,
                      textTransform: "none",
                      letterSpacing: 0,
                      minHeight: 74,
                    }}
                    onClick={() => onSelect(entry.path)}
                  >
                    <span style={{ display: "block", width: "100%" }}>
                      <div style={{ fontWeight: 800, fontSize: 13, marginBottom: 4 }}>{entry.title}</div>
                      <div style={{ fontSize: 11, opacity: 0.85, marginBottom: 3 }}>{entry.path}</div>
                      <div style={{ fontSize: 10, opacity: 0.75 }}>{formatDocDate(entry.modified_at_ms)}</div>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
