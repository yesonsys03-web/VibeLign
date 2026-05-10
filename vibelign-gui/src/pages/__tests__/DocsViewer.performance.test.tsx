import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import DocsViewer from "../DocsViewer";
import type { DocsHtmlReadResult, DocsIndexEntry, DocsVisualReadResult, ReadFileResult } from "../../lib/vib";

const docsIndex: DocsIndexEntry[] = [
  { category: "Context", path: "PROJECT_CONTEXT.md", title: "Perf Doc", modified_at_ms: 1 },
];

const docPayload: ReadFileResult = {
  path: "PROJECT_CONTEXT.md",
  content: "# Perf Doc\n\nSource first paint content.",
  source_hash: "hash-perf",
};

const visualPayload: DocsVisualReadResult = {
  path: "PROJECT_CONTEXT.md",
  contract: { schema_version: 2, generator_version: "heuristic-v3" },
  artifact: {
    source_path: "/tmp/project/PROJECT_CONTEXT.md",
    source_hash: "hash-perf",
    generated_at: "2026-05-10T00:00:00Z",
    generator_version: "heuristic-v3",
    schema_version: 2,
    title: "Perf Doc",
    summary: "Performance fixture",
    sections: [],
    glossary: [],
    action_items: [],
    diagram_blocks: [],
    warnings: [],
    heuristic_fields: {
      tldr_one_liner: "Performance fixture",
      key_rules: [],
      success_criteria: [],
      edge_cases: [],
      components: [],
      provenance: "heuristic",
      generator: "heuristic-v3",
      generated_at: "2026-05-10T00:00:00Z",
    },
    ai_fields: null,
  },
};

const htmlPayload: DocsHtmlReadResult = {
  path: "PROJECT_CONTEXT.md",
  contract: { schema_version: 1, generator_version: "raw-html-v1" },
  artifact: {
    source_path: "/tmp/project/PROJECT_CONTEXT.md",
    source_hash: "hash-perf",
    generated_at: "2026-05-10T00:00:00Z",
    generator_version: "raw-html-v1",
    schema_version: 1,
    title: "Perf Doc",
    html: "<!doctype html><html><body><main>Perf Raw HTML</main></body></html>",
    csp: "default-src 'none'",
    mode: "raw_html",
  },
};

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    listDocsIndex: vi.fn(async () => docsIndex),
    listExtraDocSources: vi.fn(async () => ({ ok: true, sources: [], entries: docsIndex, warnings: [] })),
    readFile: vi.fn(async () => docPayload),
    readDocsVisual: vi.fn(async () => visualPayload),
    readDocsHtml: vi.fn(async () => htmlPayload),
    pickFolder: vi.fn(async () => null),
    addExtraDocSource: vi.fn(),
    removeExtraDocSource: vi.fn(),
  };
});

function percentile95(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.ceil(sorted.length * 0.95) - 1] ?? 0;
}

describe("DocsViewer performance spot checks", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("source_first_paint_and_canvas_mode_switch_stay_within_budget", async () => {
    const sourcePaintMs: number[] = [];
    const modeSwitchMs: number[] = [];

    for (let index = 0; index < 20; index += 1) {
      const sourceStart = performance.now();
      const rendered = render(<DocsViewer projectDir="/tmp/project" />);
      await screen.findByText("Source first paint content.");
      sourcePaintMs.push(performance.now() - sourceStart);

      const modeStart = performance.now();
      fireEvent.click(screen.getByText("Canvas"));
      await screen.findByTitle("Perf Doc HTML Canvas");
      modeSwitchMs.push(performance.now() - modeStart);
      rendered.unmount();
    }

    const sourceP95 = percentile95(sourcePaintMs);
    const switchP95 = percentile95(modeSwitchMs);
    console.info(`DocsViewer perf spot-check: source_p95=${sourceP95.toFixed(2)}ms canvas_switch_p95=${switchP95.toFixed(2)}ms samples=20`);

    expect(sourceP95).toBeLessThanOrEqual(200);
    expect(switchP95).toBeLessThanOrEqual(50);
  });
});
