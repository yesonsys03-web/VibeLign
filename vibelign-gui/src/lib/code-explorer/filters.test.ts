// === ANCHOR: FILTERS_TEST_START ===
import { describe, expect, it } from "vitest";

import { filterCodeFiles } from "./filters";

describe("filterCodeFiles", () => {
  const files = [
    { path: "src/App.tsx", category: "ui", imports: [] },
    { path: "vibelign/core/project_scan.py", category: "core", imports: [] },
  ];

  it("matches path and category case-insensitively", () => {
    expect(filterCodeFiles(files, "APP").map((file) => file.path)).toEqual(["src/App.tsx"]);
    expect(filterCodeFiles(files, "core").map((file) => file.path)).toEqual(["vibelign/core/project_scan.py"]);
  });
});
// === ANCHOR: FILTERS_TEST_END ===
