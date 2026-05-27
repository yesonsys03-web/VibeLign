import { describe, expect, it } from "vitest";

import { buildCodeTree, collectDirectoryPaths, flattenVisibleTree } from "./tree";
import type { CodeFileEntry } from "../vib/types";

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
});
