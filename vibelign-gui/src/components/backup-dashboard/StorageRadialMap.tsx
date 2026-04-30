import { useMemo, useState } from "react";
import type { BackupEntry } from "../../lib/vib";
import { formatBytes } from "./model";

interface StorageRadialMapProps {
  entries: BackupEntry[];
}

interface FileTreeNode {
  id: string;
  name: string;
  path: string;
  sizeBytes: number;
  children: Map<string, FileTreeNode>;
}

interface ArcSegment {
  id: string;
  label: string;
  detail: string;
  start: number;
  end: number;
  inner: number;
  outer: number;
  color: string;
  depth: number;
  path: string;
  hasChildren: boolean;
}

const TRACK_COLORS = ["#26F75C", "#8DFF31", "#FFE847", "#FFB83E", "#43F0EA", "#4D7CFF", "#7B4DFF", "#FF3CEB"];
const GAP_DEGREES = 0.8;
const MIN_SEGMENT_SWEEP = 0.35;
const MAX_DEPTH = 5;

export default function StorageRadialMap({ entries }: StorageRadialMapProps) {
  const [activePath, setActivePath] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const tree = useMemo(() => buildFileTree(entries), [entries]);
  const activeNode = findNodeByPath(tree, activePath) ?? tree;
  const parentPath = getParentPath(activeNode.path);
  const topNodes = sortedChildren(activeNode).slice(0, 6);
  const segments = activeNode.sizeBytes > 0 ? buildFileSegments(activeNode) : [];
  const largest = topNodes[0];
  const isRootView = activeNode.path === "";

  if (tree.sizeBytes <= 0) {
    return (
      <div style={emptyStyle}>
        <div style={{ fontSize: 28, fontWeight: 900 }}>?</div>
        <div>파일별 백업 크기 데이터가 생기면 공간 지도가 채워져요.</div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 220px) minmax(0, 1fr)", gap: 14, alignItems: "center" }}>
      <div style={mapShellStyle} aria-label="백업 파일과 폴더 크기 방사형 지도">
        <svg viewBox="0 0 240 240" role="img" aria-label="백업 파일과 폴더 크기 지도" style={{ width: "100%", display: "block", filter: "drop-shadow(4px 5px 0 rgba(26, 26, 26, 0.18))" }}>
          <defs>
            <radialGradient id="backup-radial-core" cx="48%" cy="44%" r="62%">
              <stop offset="0%" stopColor="#38105F" />
              <stop offset="100%" stopColor="#1A1A1A" />
            </radialGradient>
          </defs>
          <circle cx="120" cy="120" r="116" fill="#3B135B" />
          {segments.map((segment) => (
            <path
              key={segment.id}
              d={describeArc(120, 120, segment.inner, segment.outer, segment.start, segment.end)}
              fill={segment.color}
              opacity={selectedPath === segment.path ? 1 : Math.max(0.62, 1 - segment.depth * 0.055)}
              stroke="#35104E"
              strokeWidth={selectedPath === segment.path ? "2.4" : "1.05"}
              style={{ cursor: segment.hasChildren ? "zoom-in" : "pointer" }}
              onClick={() => {
                if (segment.hasChildren) {
                  setActivePath(segment.path);
                  setSelectedPath("");
                  return;
                }
                setSelectedPath(segment.path);
              }}
            >
              <title>{`${segment.label} · ${segment.detail}${segment.hasChildren ? " · 클릭해서 내부 보기" : ""}`}</title>
            </path>
          ))}
          <circle
            cx="120"
            cy="120"
            r="43"
            fill="url(#backup-radial-core)"
            stroke="#2C0D3F"
            strokeWidth="2"
            style={{ cursor: isRootView ? "default" : "zoom-out" }}
            onClick={() => {
              if (!isRootView) {
                setActivePath(parentPath);
                setSelectedPath("");
              }
            }}
          />
          <text x="120" y="108" textAnchor="middle" fill="#D8C8EE" fontSize="8" fontWeight="800">{isRootView ? "전체 백업" : "현재 폴더"}</text>
          <text x="120" y="123" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="900">{formatBytes(activeNode.sizeBytes)}</text>
          <text x="120" y="138" textAnchor="middle" fill="#D8C8EE" fontSize="8" fontWeight="700">{isRootView ? "CLICK FOLDERS" : "CENTER = UP"}</text>
        </svg>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        <div style={breadcrumbStyle}>
          {breadcrumbParts(activeNode).map((crumb, index, crumbs) => (
            <button
              key={crumb.path || "root"}
              type="button"
              style={breadcrumbButtonStyle}
              onClick={() => {
                setActivePath(crumb.path);
                setSelectedPath("");
              }}
            >
              {crumb.name}{index < crumbs.length - 1 ? " /" : ""}
            </button>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "#333", lineHeight: 1.55 }}>
          폴더 조각을 클릭하면 그 내부 구조로 들어가요. 가운데 원은 상위 폴더로 돌아가는 버튼처럼 동작합니다.
        </div>
        {!isRootView ? (
          <button
            type="button"
            style={upButtonStyle}
            onClick={() => {
              setActivePath(parentPath);
              setSelectedPath("");
            }}
          >
            상위 폴더로
          </button>
        ) : null}
        <div style={legendGridStyle}>
          {topNodes.map((node, index) => (
            <button
              key={node.id}
              type="button"
              style={legendItemStyle}
              onClick={() => {
                if (node.children.size > 0) {
                  setActivePath(node.path);
                  setSelectedPath("");
                  return;
                }
                setSelectedPath(node.path);
              }}
            >
              <span style={{ ...legendDotStyle, background: colorForIndex(index) }} />
              <span style={{ fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
              <span style={{ marginLeft: "auto", fontFamily: "IBM Plex Mono, monospace" }}>{formatBytes(node.sizeBytes)}</span>
            </button>
          ))}
        </div>
        {largest ? (
          <div style={{ fontSize: 11, color: "#555", lineHeight: 1.45 }}>
            현재 위치에서 가장 큰 경로는 <strong>{largest.path}</strong>이며 이 범위의 {Math.round((largest.sizeBytes / activeNode.sizeBytes) * 100)}%입니다.
          </div>
        ) : null}
      </div>
    </div>
  );
}

function buildFileTree(entries: BackupEntry[]): FileTreeNode {
  const root = createNode("root", "백업", "");
  for (const entry of entries) {
    for (const file of entry.files) {
      const sizeBytes = Math.max(0, file.sizeBytes);
      if (sizeBytes <= 0) continue;
      const parts = file.path.split("/").filter(Boolean);
      if (parts.length === 0) continue;
      root.sizeBytes += sizeBytes;
      let current = root;
      parts.forEach((part, index) => {
        const path = parts.slice(0, index + 1).join("/");
        let child = current.children.get(part);
        if (!child) {
          child = createNode(path, part, path);
          current.children.set(part, child);
        }
        child.sizeBytes += sizeBytes;
        current = child;
      });
    }
  }
  return root;
}

function createNode(id: string, name: string, path: string): FileTreeNode {
  return { id, name, path, sizeBytes: 0, children: new Map() };
}

function buildFileSegments(root: FileTreeNode): ArcSegment[] {
  const segments: ArcSegment[] = [];
  appendChildSegments(segments, root, -116, 224, 0, root.sizeBytes, 0);
  return segments;
}

function appendChildSegments(
  segments: ArcSegment[],
  parent: FileTreeNode,
  start: number,
  end: number,
  depth: number,
  parentSize: number,
  colorOffset: number,
) {
  if (depth >= MAX_DEPTH || parentSize <= 0) return;
  const children = sortedChildren(parent);
  let cursor = start;
  children.forEach((child, index) => {
    const sweep = ((end - start) * child.sizeBytes) / parentSize;
    const childStart = cursor;
    const childEnd = cursor + sweep;
    cursor = childEnd;
    if (childEnd - childStart <= MIN_SEGMENT_SWEEP) return;

    const inner = 48 + depth * 18;
    const outer = inner + 17;
    const arcStart = childStart + GAP_DEGREES;
    const arcEnd = childEnd - GAP_DEGREES;
    if (arcEnd - arcStart > MIN_SEGMENT_SWEEP) {
      segments.push({
        id: `${depth}-${child.id}`,
        label: child.path,
        detail: formatBytes(child.sizeBytes),
        start: arcStart,
        end: arcEnd,
        inner,
        outer,
        color: colorForIndex(colorOffset + index),
        depth,
        path: child.path,
        hasChildren: child.children.size > 0,
      });
    }
    appendChildSegments(segments, child, childStart, childEnd, depth + 1, child.sizeBytes, colorOffset + index + 1);
  });
}

function sortedChildren(node: FileTreeNode): FileTreeNode[] {
  return Array.from(node.children.values()).sort((left, right) => right.sizeBytes - left.sizeBytes || left.name.localeCompare(right.name));
}

function findNodeByPath(root: FileTreeNode, path: string): FileTreeNode | undefined {
  if (path === "") return root;
  let current = root;
  for (const part of path.split("/").filter(Boolean)) {
    const next = current.children.get(part);
    if (!next) return undefined;
    current = next;
  }
  return current;
}

function getParentPath(path: string): string {
  const parts = path.split("/").filter(Boolean);
  parts.pop();
  return parts.join("/");
}

function breadcrumbParts(node: FileTreeNode): Array<{ name: string; path: string }> {
  const parts = node.path.split("/").filter(Boolean);
  return [
    { name: "백업", path: "" },
    ...parts.map((part, index) => ({ name: part, path: parts.slice(0, index + 1).join("/") })),
  ];
}

function colorForIndex(index: number): string {
  return TRACK_COLORS[index % TRACK_COLORS.length] ?? TRACK_COLORS[0];
}

function describeArc(cx: number, cy: number, inner: number, outer: number, startAngle: number, endAngle: number): string {
  const safeEnd = Math.max(startAngle + MIN_SEGMENT_SWEEP, endAngle);
  const outerStart = polarToCartesian(cx, cy, outer, safeEnd);
  const outerEnd = polarToCartesian(cx, cy, outer, startAngle);
  const innerStart = polarToCartesian(cx, cy, inner, startAngle);
  const innerEnd = polarToCartesian(cx, cy, inner, safeEnd);
  const largeArcFlag = safeEnd - startAngle <= 180 ? "0" : "1";

  return [
    "M", outerStart.x, outerStart.y,
    "A", outer, outer, 0, largeArcFlag, 0, outerEnd.x, outerEnd.y,
    "L", innerStart.x, innerStart.y,
    "A", inner, inner, 0, largeArcFlag, 1, innerEnd.x, innerEnd.y,
    "Z",
  ].join(" ");
}

function polarToCartesian(cx: number, cy: number, radius: number, angleInDegrees: number) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleInRadians),
    y: cy + radius * Math.sin(angleInRadians),
  };
}

const mapShellStyle = {
  border: "2px solid #1A1A1A",
  background: "radial-gradient(circle at 48% 42%, #5B1A73 0%, #35104E 58%, #210A36 100%)",
  boxShadow: "3px 3px 0 #1A1A1A",
  padding: 8,
};

const emptyStyle = {
  minHeight: 160,
  border: "2px dashed #1A1A1A",
  display: "grid",
  placeItems: "center",
  textAlign: "center" as const,
  gap: 6,
  background: "#FFF8D8",
  color: "#555",
  fontSize: 12,
  fontWeight: 800,
};

const legendGridStyle = {
  display: "grid",
  gap: 5,
};

const legendItemStyle = {
  display: "flex",
  alignItems: "center",
  gap: 7,
  border: "1px solid #1A1A1A",
  background: "#FFFDF4",
  padding: "5px 7px",
  fontSize: 11,
  minWidth: 0,
  width: "100%",
  cursor: "pointer",
  textAlign: "left" as const,
};

const legendDotStyle = {
  width: 10,
  height: 10,
  border: "1px solid #1A1A1A",
  flex: "0 0 auto",
};

const breadcrumbStyle = {
  display: "flex",
  flexWrap: "wrap" as const,
  gap: 3,
  alignItems: "center",
};

const breadcrumbButtonStyle = {
  border: 0,
  background: "transparent",
  padding: 0,
  color: "#4B1B6B",
  fontSize: 11,
  fontWeight: 900,
  cursor: "pointer",
};

const upButtonStyle = {
  border: "2px solid #1A1A1A",
  background: "#F3E5FF",
  boxShadow: "2px 2px 0 #1A1A1A",
  padding: "6px 8px",
  fontSize: 11,
  fontWeight: 900,
  cursor: "pointer",
};
