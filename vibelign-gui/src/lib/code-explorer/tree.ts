import type { CodeFileEntry } from "../vib/types";

export interface CodeTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: CodeTreeNode[];
  file?: CodeFileEntry;
}

export interface VisibleCodeTreeItem {
  node: CodeTreeNode;
  depth: number;
}

function createNode(name: string, path: string, kind: "directory" | "file", file?: CodeFileEntry): CodeTreeNode {
  return { name, path, kind, children: [], file };
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
