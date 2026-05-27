import type { ReactNode } from "react";

interface CodeExplorerLayoutProps {
  toolbar: ReactNode;
  tree: ReactNode;
  viewer: ReactNode;
}

export default function CodeExplorerLayout({ toolbar, tree, viewer }: CodeExplorerLayoutProps) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12, padding: 12, minHeight: 0 }}>
      {toolbar}
      <div style={{ flex: 1, minHeight: 0, display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: 12 }}>
        <div style={{ minHeight: 0 }}>{tree}</div>
        <div style={{ minHeight: 0 }}>{viewer}</div>
      </div>
    </div>
  );
}
