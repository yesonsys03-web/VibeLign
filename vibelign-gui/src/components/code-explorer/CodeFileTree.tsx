import { useMemo, useState } from "react";

import { buildCodeTree, CATEGORY_COLORS, collectDirectoryPaths, flattenVisibleTree } from "../../lib/code-explorer/tree";
import type { CodeFileEntry, ChangeStatus } from "../../lib/vib";

interface CodeFileTreeProps {
  files: CodeFileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  // query가 활성화되면(검색 중) 매칭 파일의 모든 상위 폴더를 자동으로 펼친다.
  // CodeExplorer가 query 비어있지 않을 때 true로 넘긴다.
  autoExpandAll: boolean;
  changes: ReadonlyMap<string, ChangeStatus>;
}

export default function CodeFileTree({ files, selectedPath, onSelect, autoExpandAll, changes }: CodeFileTreeProps) {
  const tree = useMemo(() => buildCodeTree(files, changes), [files, changes]);
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
        const categoryColor = CATEGORY_COLORS[node.category];
        // 디렉터리는 진하게(~40% alpha), 파일은 적당히(~25% alpha) — 폴더가 더 강조되고
        // 파일은 같은 색 그룹 안에서 차분하게 보이게.
        const tint = `${categoryColor}${isDirectory ? "66" : "40"}`;
        // 변경된 파일 행은 diff 스타일 배경 색조로 강하게 강조한다(카테고리 tint를 덮어씀).
        // 선택된 행은 다크 배경을 유지해 선택 상태가 항상 우선 보이게 한다.
        const changeWash =
          isDirectory || !node.changeStatus
            ? null
            : node.changeStatus === "new"
            ? "rgba(34, 197, 94, 0.22)"   // 신규 = 녹색
            : "rgba(245, 158, 11, 0.24)"; // 수정 = 주황
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
              paddingLeft: 12 + depth * 14,
              marginBottom: 3,
              background: active ? "#1A1A1A" : (changeWash ?? tint),
              color: active ? "#fff" : undefined,
              textTransform: "none",
              letterSpacing: 0,
              overflow: "hidden",
              // 왼쪽 액센트 바(4px) — 카테고리 색을 가장 잘 드러내는 요소.
              // .btn-ghost 의 var(--shadow-sm) 도 함께 보존(브루탈리즘 테두리 효과 유지).
              boxShadow: `inset 4px 0 0 ${categoryColor}, var(--shadow-sm)`,
            }}
          >
            <span style={{ width: 16, display: "inline-block" }}>{isDirectory ? (expandedPaths.has(node.path) ? "▾" : "▸") : ""}</span>
            <span
              aria-hidden="true"
              title={node.category}
              style={{
                width: 8,
                height: 8,
                borderRadius: 4,
                display: "inline-block",
                marginRight: 6,
                verticalAlign: "middle",
                // 폴더는 채우고 파일은 외곽선만 — 동일 색 안에서도 둘을 구분하기 쉽게.
                background: isDirectory ? CATEGORY_COLORS[node.category] : "transparent",
                border: isDirectory ? "none" : `2px solid ${CATEGORY_COLORS[node.category]}`,
                boxSizing: "border-box",
              }}
            />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
            {!isDirectory && node.changeStatus && (
              <span
                aria-label={node.changeStatus === "new" ? "신규 파일" : "수정된 파일"}
                title={node.changeStatus === "new" ? "신규 (untracked)" : "수정됨"}
                style={{
                  marginLeft: "auto",
                  flexShrink: 0,
                  fontSize: 11,
                  fontWeight: 800,
                  fontFamily: "ui-monospace, Menlo, Consolas, monospace",
                  // 행 색조 위에서도 또렷하도록 진한 톤을 쓴다(선택 행은 흰색).
                  color: active ? "#fff" : node.changeStatus === "new" ? "#166534" : "#92400e",
                }}
              >
                {node.changeStatus === "new" ? "U" : "M"}
              </span>
            )}
            {isDirectory && node.changedCount > 0 && (
              <span
                aria-label={`변경 파일 ${node.changedCount}개`}
                title={`하위 변경 파일 ${node.changedCount}개`}
                style={{
                  marginLeft: "auto",
                  flexShrink: 0,
                  fontSize: 10,
                  fontWeight: 800,
                  lineHeight: 1,
                  padding: "2px 7px",
                  borderRadius: 999,
                  background: active ? "rgba(255,255,255,0.25)" : "rgba(0,0,0,0.10)",
                  color: active ? "#fff" : "#444",
                }}
              >
                {node.changedCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
