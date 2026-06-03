// === ANCHOR: CODEEXPLORERTOOLBAR_START ===
interface CodeExplorerToolbarProps {
  query: string;
  fileCount: number;
  isRefreshing: boolean;
  onQueryChange: (value: string) => void;
  onRefresh: () => void;
}

export default function CodeExplorerToolbar({ query, fileCount, isRefreshing, onQueryChange, onRefresh }: CodeExplorerToolbarProps) {
  return (
    <div className="card" style={{ display: "flex", gap: 10, alignItems: "center", padding: 12 }}>
      <input
        className="input-field"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="파일명, 경로, 카테고리, import 검색..."
        style={{ flex: 1 }}
      />
      <span style={{ fontSize: 12, fontWeight: 700 }}>{fileCount} files</span>
      <button className="btn btn-secondary btn-sm" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "새로고침 중…" : "새로고침"}
      </button>
    </div>
  );
}
// === ANCHOR: CODEEXPLORERTOOLBAR_END ===
