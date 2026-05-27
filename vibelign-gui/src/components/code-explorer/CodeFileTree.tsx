import { useMemo, useState } from "react";

import { buildCodeTree, collectDirectoryPaths, flattenVisibleTree } from "../../lib/code-explorer/tree";
import type { CodeFileEntry } from "../../lib/vib";

interface CodeFileTreeProps {
  files: CodeFileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  // query가 활성화되면(검색 중) 매칭 파일의 모든 상위 폴더를 자동으로 펼친다.
  // CodeExplorer가 query 비어있지 않을 때 true로 넘긴다.
  autoExpandAll: boolean;
}

export default function CodeFileTree({ files, selectedPath, onSelect, autoExpandAll }: CodeFileTreeProps) {
  const tree = useMemo(() => buildCodeTree(files), [files]);
  // 기본 펼침: 프로젝트가 무엇이든(VibeLign 레포 가정 금지) 1단계 디렉터리를 펼친다.
  const firstLevelDirs = useMemo(
    () => new Set(tree.children.filter((node) => node.kind === "directory").map((node) => node.path)),
    [tree],
  );
  const [userExpanded, setUserExpanded] = useState<Set<string> | null>(null);
  const expandedPaths = useMemo(() => {
    if (autoExpandAll) return collectDirectoryPaths(tree); // 검색 중에는 매칭 결과가 항상 보이도록 전부 펼침
    return userExpanded ?? firstLevelDirs;
  }, [autoExpandAll, tree, userExpanded, firstLevelDirs]);
  const visible = useMemo(() => flattenVisibleTree(tree, expandedPaths), [tree, expandedPaths]);

  function toggle(path: string) {
    if (autoExpandAll) return; // 검색 중에는 자동 펼침이 우선하므로 수동 토글 무시
    setUserExpanded((prev) => {
      const next = new Set(prev ?? firstLevelDirs); // 최초 토글은 현재 기본(1단계 펼침)에서 시작
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  return (
    <div className="card" style={{ height: "100%", overflow: "auto", padding: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 800, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
        Project Code
      </div>
      {visible.length === 0 ? (
        <div style={{ fontSize: 12, color: "#666" }}>표시할 코드 파일이 없습니다.</div>
      ) : visible.map(({ node, depth }) => {
        const active = node.path === selectedPath;
        const isDirectory = node.kind === "directory";
        return (
          <button
            key={`${node.kind}:${node.path}`}
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => isDirectory ? toggle(node.path) : onSelect(node.path)}
            title={node.path}
            style={{
              width: "100%",
              justifyContent: "flex-start",
              textAlign: "left",
              paddingLeft: 8 + depth * 14,
              marginBottom: 3,
              background: active ? "#1A1A1A" : undefined,
              color: active ? "#fff" : undefined,
              textTransform: "none",
              letterSpacing: 0,
              overflow: "hidden",
            }}
          >
            <span style={{ width: 16, display: "inline-block" }}>{isDirectory ? (expandedPaths.has(node.path) ? "▾" : "▸") : ""}</span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
          </button>
        );
      })}
    </div>
  );
}
