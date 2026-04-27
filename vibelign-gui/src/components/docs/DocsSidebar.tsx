import { useState, type ReactNode } from "react";
import { categoryColor, categoryLabel, DOC_CATEGORY_ORDER, filterDocsIndex, formatCategoryWithSource, formatDocDate } from "../../lib/docs";
import type { DocsIndexEntry } from "../../lib/vib";

interface DocsSidebarProps {
  docs: DocsIndexEntry[];
  query: string;
  selectedPath: string | null;
  onQueryChange: (value: string) => void;
  onSelect: (path: string) => void;
}

interface DocsTreeNode {
  name: string;
  path: string;
  children: Map<string, DocsTreeNode>;
  entries: DocsIndexEntry[];
}

// Docs Viewer 진입 시 전체 카테고리를 접어 두고, 사용자가 필요한 묶음만 펼치도록 한다.
const DEFAULT_COLLAPSED: ReadonlySet<string> = new Set(DOC_CATEGORY_ORDER);

function createTreeNode(name: string, path: string): DocsTreeNode {
  return { name, path, children: new Map(), entries: [] };
}

function buildDocsTree(entries: DocsIndexEntry[]): DocsTreeNode {
  const root = createTreeNode("", "");
  for (const entry of entries) {
    const segments = entry.path.split("/").filter(Boolean);
    const folderSegments = segments.slice(0, -1);
    let current = root;
    for (const segment of folderSegments) {
      const childPath = current.path ? `${current.path}/${segment}` : segment;
      let child = current.children.get(segment);
      if (!child) {
        child = createTreeNode(segment, childPath);
        current.children.set(segment, child);
      }
      current = child;
    }
    current.entries.push(entry);
  }
  return root;
}

export default function DocsSidebar({ docs, query, selectedPath, onQueryChange, onSelect }: DocsSidebarProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(DEFAULT_COLLAPSED));
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(() => new Set());
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

  function toggleFolder(path: string) {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function renderDocButton(entry: DocsIndexEntry, compactPath = false) {
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
            {compactPath ? entry.path.split("/").pop() ?? entry.path : entry.path}
          </div>
          {entry.category === "Custom" && entry.source_root ? (
            <div style={{ fontSize: 10, opacity: 0.6, marginTop: 1, color: "#8B4DFF" }}>
              {formatCategoryWithSource(entry)}
            </div>
          ) : null}
          <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>{formatDocDate(entry.modified_at_ms)}</div>
        </span>
      </button>
    );
  }

  function renderDocsTreeNode(node: DocsTreeNode, depth: number): ReactNode {
    const childNodes = Array.from(node.children.values()).sort((a, b) => a.name.localeCompare(b.name));
    const files = [...node.entries].sort((a, b) => a.path.localeCompare(b.path));
    return (
      <div key={node.path || "docs-root"} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {childNodes.map((child) => {
          const folderCollapsed = !searching && !expandedFolders.has(child.path);
          const fileCount = countTreeFiles(child);
          return (
            <div key={child.path} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <button
                type="button"
                onClick={() => toggleFolder(child.path)}
                aria-expanded={!folderCollapsed}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 2px",
                  paddingLeft: depth * 12,
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <span style={{ fontSize: 10, fontWeight: 800, width: 10 }}>{folderCollapsed ? "▸" : "▾"}</span>
                <span style={{ fontSize: 12, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{child.name}</span>
                <span style={{ marginLeft: "auto", fontSize: 10, color: "#888", fontWeight: 700 }}>{fileCount}</span>
              </button>
              {folderCollapsed ? null : renderDocsTreeNode(child, depth + 1)}
            </div>
          );
        })}
        {files.map((entry) => (
          <div key={entry.path} style={{ paddingLeft: depth * 12 }}>
            {renderDocButton(entry, true)}
          </div>
        ))}
      </div>
    );
  }

  function countTreeFiles(node: DocsTreeNode): number {
    return node.entries.length + Array.from(node.children.values()).reduce((total, child) => total + countTreeFiles(child), 0);
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
                  {category === "Docs" ? renderDocsTreeNode(buildDocsTree(items), 0) : items.map((entry) => renderDocButton(entry))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
