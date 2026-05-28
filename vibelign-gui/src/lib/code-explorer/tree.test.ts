import { describe, expect, it } from "vitest";

import { buildCodeTree, categorizeFileEntry, collectDirectoryPaths, flattenVisibleTree } from "./tree";
import type { CodeFileEntry, ChangeStatus } from "../vib/types";

const files: CodeFileEntry[] = [
  { path: "src/App.tsx", category: "ui", imports: [] },
  { path: "src/lib/vib/code.ts", category: "service", imports: ["@tauri-apps/api/core"] },
  { path: "vibelign/core/project_scan.py", category: "core", imports: [] },
];

describe("code explorer tree", () => {
  it("builds a stable nested tree from flat file paths", () => {
    const tree = buildCodeTree(files);

    expect(tree.children.map((node) => node.name)).toEqual(["src", "vibelign"]);
    expect(tree.children[0].children.map((node) => node.name)).toEqual(["lib", "App.tsx"]);
  });

  it("flattens visible folders according to expanded paths", () => {
    const tree = buildCodeTree(files);
    const visible = flattenVisibleTree(tree, new Set(["src", "src/lib", "src/lib/vib"]));

    expect(visible.map((item) => item.node.path)).toContain("src/App.tsx");
    expect(visible.map((item) => item.node.path)).toContain("src/lib/vib/code.ts");
    expect(visible.map((item) => item.node.path)).not.toContain("vibelign/core/project_scan.py");
  });

  it("collects every directory path for search auto-expand", () => {
    const tree = buildCodeTree(files);
    const dirs = collectDirectoryPaths(tree);

    expect(dirs).toEqual(new Set(["src", "src/lib", "src/lib/vib", "vibelign", "vibelign/core"]));
  });

  it("categorizes files and aggregates directory categories", () => {
    expect(categorizeFileEntry({ path: "docs/index.md", category: "docs", imports: [] })).toBe("docs");
    expect(categorizeFileEntry({ path: "docs/superpowers/specs/x.md", category: "docs", imports: [] })).toBe("docs");
    expect(categorizeFileEntry({ path: "tests/api/auth.py", category: "code", imports: [] })).toBe("tests");
    expect(categorizeFileEntry({ path: "src/pages/__tests__/foo.test.tsx", category: "code", imports: [] })).toBe("tests");
    expect(categorizeFileEntry({ path: "src/lib/code.ts", category: "code", imports: [] })).toBe("code");

    const tree = buildCodeTree([
      { path: "docs/index.md", category: "docs", imports: [] },
      { path: "docs/specs/design.md", category: "docs", imports: [] },
      { path: "tests/api/auth.py", category: "code", imports: [] },
      { path: "src/lib/code.ts", category: "code", imports: [] },
    ]);
    const byName = Object.fromEntries(tree.children.map((node) => [node.name, node.category]));
    expect(byName).toMatchObject({ docs: "docs", tests: "tests", src: "code" });
  });
});

describe("buildCodeTree change markers", () => {
  const files = [
    { path: "src/a.ts", category: "code", imports: [] },
    { path: "src/b.ts", category: "code", imports: [] },
    { path: "docs/c.md", category: "docs", imports: [] },
  ];

  it("stamps changeStatus on file nodes and rolls up changedCount on directories", () => {
    const changes = new Map<string, ChangeStatus>([
      ["src/a.ts", "modified"],
      ["src/b.ts", "new"],
    ]);
    const tree = buildCodeTree(files, changes);

    const src = tree.children.find((n) => n.path === "src")!;
    const docs = tree.children.find((n) => n.path === "docs")!;
    const a = src.children.find((n) => n.path === "src/a.ts")!;
    const b = src.children.find((n) => n.path === "src/b.ts")!;
    const c = docs.children.find((n) => n.path === "docs/c.md")!;

    expect(a.changeStatus).toBe("modified");
    expect(b.changeStatus).toBe("new");
    expect(c.changeStatus).toBeUndefined();
    expect(src.changedCount).toBe(2);
    expect(docs.changedCount).toBe(0);
  });

  it("defaults to no markers when changes map is omitted", () => {
    const tree = buildCodeTree(files);
    const src = tree.children.find((n) => n.path === "src")!;
    expect(src.changedCount).toBe(0);
    const a = src.children.find((n) => n.path === "src/a.ts")!;
    expect(a.changeStatus).toBeUndefined();
  });
});
