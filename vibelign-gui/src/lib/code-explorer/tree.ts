import type { CodeFileEntry } from "../vib/types";

export type CategoryKey = "code" | "docs" | "tests" | "other";

// 사이드바 가독성을 위한 카테고리별 색. 다크 테마와 라이트 테마 모두에서
// 인식 가능한 채도의 톤만 골랐다.
export const CATEGORY_COLORS: Record<CategoryKey, string> = {
  code: "#22c55e",
  docs: "#f97316",
  tests: "#a855f7",
  other: "#9ca3af",
};

const TEST_SEGMENTS = new Set(["tests", "test", "__tests__", "spec", "specs"]);
const TEST_FILE_PATTERN = /\.(test|spec)\.[tj]sx?$|^test_[^/]*\.py$|_test\.py$/i;

export interface CodeTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: CodeTreeNode[];
  file?: CodeFileEntry;
  // 파일은 자신의 카테고리, 디렉터리는 하위 파일의 다수결 카테고리.
  category: CategoryKey;
}

export interface VisibleCodeTreeItem {
  node: CodeTreeNode;
  depth: number;
}

export function categorizeFileEntry(entry: CodeFileEntry): CategoryKey {
  // .md 등 문서 파일이면 어디에 있든 docs (docs/superpowers/specs/*.md 포함).
  if (entry.category === "docs") return "docs";
  const lower = entry.path.toLowerCase();
  const segments = lower.split("/").filter(Boolean);
  const last = segments[segments.length - 1] ?? "";
  if (segments.some((segment) => TEST_SEGMENTS.has(segment)) || TEST_FILE_PATTERN.test(last)) return "tests";
  if (entry.category === "code") return "code";
  return "other";
}

function createNode(name: string, path: string, kind: "directory" | "file", file?: CodeFileEntry): CodeTreeNode {
  return {
    name,
    path,
    kind,
    children: [],
    file,
    category: file ? categorizeFileEntry(file) : "other",
  };
}

function pickDominantCategory(counts: Record<CategoryKey, number>): CategoryKey {
  // 다수결, 동률일 때는 docs > tests > code > other 우선 (더 의미 있는 분류가 이긴다).
  const priority: CategoryKey[] = ["docs", "tests", "code", "other"];
  let best: CategoryKey = "other";
  let bestCount = -1;
  for (const key of priority) {
    if (counts[key] > bestCount) {
      best = key;
      bestCount = counts[key];
    }
  }
  return best;
}

function assignDirectoryCategories(node: CodeTreeNode): Record<CategoryKey, number> {
  const counts: Record<CategoryKey, number> = { code: 0, docs: 0, tests: 0, other: 0 };
  for (const child of node.children) {
    if (child.kind === "file") {
      counts[child.category] += 1;
    } else {
      const childCounts = assignDirectoryCategories(child);
      counts.code += childCounts.code;
      counts.docs += childCounts.docs;
      counts.tests += childCounts.tests;
      counts.other += childCounts.other;
    }
  }
  if (node.kind === "directory") {
    node.category = pickDominantCategory(counts);
  }
  return counts;
}

export function buildCodeTree(files: CodeFileEntry[]): CodeTreeNode {
  const root = createNode("", "", "directory");
  for (const file of [...files].sort((left, right) => left.path.localeCompare(right.path))) {
    const segments = file.path.split("/").filter(Boolean);
    let current = root;
    for (let index = 0; index < segments.length; index += 1) {
      const segment = segments[index];
      const childPath = current.path ? `${current.path}/${segment}` : segment;
      const isFile = index === segments.length - 1;
      let child = current.children.find((item) => item.name === segment && item.kind === (isFile ? "file" : "directory"));
      if (!child) {
        child = createNode(segment, childPath, isFile ? "file" : "directory", isFile ? file : undefined);
        current.children.push(child);
        current.children.sort(compareNodes);
      }
      current = child;
    }
  }
  assignDirectoryCategories(root);
  return root;
}

export function flattenVisibleTree(root: CodeTreeNode, expandedPaths: ReadonlySet<string>): VisibleCodeTreeItem[] {
  const result: VisibleCodeTreeItem[] = [];
  function visit(node: CodeTreeNode, depth: number) {
    for (const child of node.children) {
      result.push({ node: child, depth });
      if (child.kind === "directory" && expandedPaths.has(child.path)) {
        visit(child, depth + 1);
      }
    }
  }
  visit(root, 0);
  return result;
}

export function collectDirectoryPaths(root: CodeTreeNode): Set<string> {
  const paths = new Set<string>();
  function visit(node: CodeTreeNode) {
    for (const child of node.children) {
      if (child.kind === "directory") {
        paths.add(child.path);
        visit(child);
      }
    }
  }
  visit(root);
  return paths;
}

function compareNodes(left: CodeTreeNode, right: CodeTreeNode): number {
  if (left.kind !== right.kind) return left.kind === "directory" ? -1 : 1;
  return left.name.localeCompare(right.name);
}
