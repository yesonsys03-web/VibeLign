import { useState } from "react";
import { categoryColor, categoryLabel, DOC_CATEGORY_ORDER, filterDocsIndex, formatDocDate } from "../../lib/docs";
import type { DocsIndexEntry } from "../../lib/vib";

interface DocsSidebarProps {
  docs: DocsIndexEntry[];
  query: string;
  selectedPath: string | null;
  onQueryChange: (value: string) => void;
  onSelect: (path: string) => void;
}

// 기본적으로 접히는 무거운 카테고리 — 사용자가 필요할 때만 펼치도록.
const DEFAULT_COLLAPSED: ReadonlySet<string> = new Set(["Docs", "Root"]);

export default function DocsSidebar({ docs, query, selectedPath, onQueryChange, onSelect }: DocsSidebarProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(DEFAULT_COLLAPSED));
  const filtered = filterDocsIndex(docs, query);
  const orderedCategories = DOC_CATEGORY_ORDER.filter((category) => filtered.some((entry) => entry.category === category));
  const searching = query.trim().length > 0;

  function toggleCategory(category: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  }

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
        ) : orderedCategories.map((category) => {
          const items = filtered.filter((entry) => entry.category === category);
          const isCollapsed = !searching && collapsed.has(category);
          return (
            <div key={category} style={{ marginBottom: 14 }}>
              <button
                type="button"
                onClick={() => toggleCategory(category)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 8,
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                }}
                aria-expanded={!isCollapsed}
              >
                <span style={{ fontSize: 10, fontWeight: 800, width: 10, textAlign: "center" }}>{isCollapsed ? "▸" : "▾"}</span>
                <span style={{ width: 10, height: 10, background: categoryColor(category), border: "1px solid #1A1A1A" }} />
                <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>{categoryLabel(category)}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: "#888", marginLeft: "auto" }}>{items.length}</span>
              </button>
              {isCollapsed ? null : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {items.map((entry) => {
                    const active = entry.path === selectedPath;
                    return (
                      <button
                        key={entry.path}
                        className="btn btn-ghost btn-sm"
                        title={entry.path}
                        style={{
                          textAlign: "left",
                          justifyContent: "flex-start",
                          alignItems: "flex-start",
                          background: active ? "#1A1A1A" : undefined,
                          color: active ? "#fff" : undefined,
                          textTransform: "none",
                          letterSpacing: 0,
                          padding: "8px 10px",
                          whiteSpace: "normal",
                          overflow: "hidden",
                        }}
                        onClick={() => onSelect(entry.path)}
                      >
                        <span style={{ display: "block", width: "100%", minWidth: 0 }}>
                          <div
                            style={{
                              fontWeight: 800,
                              fontSize: 13,
                              marginBottom: 3,
                              overflowWrap: "anywhere",
                              wordBreak: "break-word",
                              lineHeight: 1.3,
                            }}
                          >
                            {entry.title}
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              opacity: 0.75,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {entry.path}
                          </div>
                          <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>{formatDocDate(entry.modified_at_ms)}</div>
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
