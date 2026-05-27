// === ANCHOR: DOCSVIEWER_EPOCH_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import DocsViewer from "../DocsViewer";
import type { DocsHtmlReadResult, DocsIndexEntry, DocsVisualReadResult, ReadFileResult, VibResult } from "../../lib/vib";

const docsIndex: DocsIndexEntry[] = [
  { category: "Context", path: "PROJECT_CONTEXT.md", title: "Doc A", modified_at_ms: 1 },
  { category: "Readme", path: "README.md", title: "Doc B", modified_at_ms: 2 },
];

const docPayloads: Record<string, ReadFileResult> = {
  "PROJECT_CONTEXT.md": { path: "PROJECT_CONTEXT.md", content: "# Doc A\n\nAlpha", source_hash: "hash-a" },
  "README.md": { path: "README.md", content: "# Doc B\n\nBeta", source_hash: "hash-b" },
};

const readyArtifact: DocsVisualReadResult = {
  path: "PROJECT_CONTEXT.md",
  contract: { schema_version: 2, generator_version: "heuristic-v3" },
  artifact: {
    source_path: "/tmp/project/PROJECT_CONTEXT.md",
    source_hash: "hash-a",
    generated_at: "2026-05-10T00:00:00Z",
    generator_version: "heuristic-v3",
    schema_version: 2,
    title: "Doc A",
    summary: "Ready artifact",
    sections: [],
    glossary: [],
    action_items: [],
    diagram_blocks: [],
    warnings: [],
    heuristic_fields: null,
    ai_fields: null,
  },
};

const visualMindmapArtifact: DocsVisualReadResult = {
  ...readyArtifact,
  artifact: {
    ...readyArtifact.artifact,
    diagram_blocks: [{ id: "mindmap", kind: "mermaid", title: "문서 구조", source: "mindmap\n  root((\"Doc A\"))\n    \"Intro\"\n    \"Rules\"\n    \"Actions\"" }],
    sections: Array.from({ length: 16 }, (_, index) => ({ id: `section-${index}`, title: index === 15 ? "Late Section" : `Section ${index + 1}`, level: 2, summary: "", body_preview: index === 0 ? ["Goal bullet kept from source"] : [] })),
    action_items: Array.from({ length: 6 }, (_, index) => ({ text: `Action ${index + 1}`, checked: false })),
    glossary: Array.from({ length: 5 }, (_, index) => ({ term: `Term ${index + 1}`, definition: `Definition ${index + 1}` })),
    warnings: Array.from({ length: 4 }, (_, index) => `Risk ${index + 1}`),
    heuristic_fields: {
      tldr_one_liner: "TLDR",
      key_rules: Array.from({ length: 6 }, (_, index) => `Decision ${index + 1}`),
      success_criteria: [],
      edge_cases: Array.from({ length: 4 }, (_, index) => `Risk ${index + 1}`),
      components: [],
      provenance: "heuristic",
      generator: "heuristic-v3",
      generated_at: "2026-05-10T00:00:00Z",
    },
  },
};

const hostileArtifact: DocsVisualReadResult = {
  ...readyArtifact,
  artifact: {
    ...readyArtifact.artifact,
    title: "Doc <script>alert('title')</script>",
    summary: "Summary <img src=x onerror=alert('summary')>",
    action_items: [{ text: "Do <svg onload=alert('action')>", checked: false }],
    glossary: [{ term: "<b>Term</b>", definition: "Definition <iframe src='file:///etc/passwd'></iframe>" }],
    diagram_blocks: [{ id: "hostile", kind: "mermaid", title: "Flow <script>alert('diagram-title')</script>", source: "graph TD\nA[<script>alert('diagram')</script>]" }],
    warnings: ["Warning <a href='https://example.com'>link</a>"],
    heuristic_fields: {
      tldr_one_liner: "TLDR <script>alert('tldr')</script>",
      key_rules: ["Rule <img src=x onerror=alert('rule')>"],
      success_criteria: [],
      edge_cases: ["Risk <script>alert('risk')</script>"],
      components: [],
      provenance: "heuristic",
      generator: "heuristic-v3",
      generated_at: "2026-05-10T00:00:00Z",
    },
  },
};

const readyHtmlArtifact: DocsHtmlReadResult = {
  path: "PROJECT_CONTEXT.md",
  contract: { schema_version: 1, generator_version: "raw-html-v1" },
  artifact: {
    source_path: "/tmp/project/PROJECT_CONTEXT.md",
    source_hash: "hash-a",
    generated_at: "2026-05-10T00:00:00Z",
    generator_version: "raw-html-v1",
    schema_version: 1,
    title: "Doc A",
    html: "<!doctype html><html><head><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'\"><style>font-family: Georgia; li::before { background: #4dff91; }</style></head><body><script>window.parent.hacked=true</script><main><h1>Raw HTML body</h1><p>Alpha</p><p>Beta</p><ul><li>Readable list</li><li>Second item</li></ul><table><tr><td>Mode</td><td>Purpose</td></tr></table><pre><code>Gamma</code></pre></main></body></html>",
    csp: "default-src 'none'",
    mode: "raw_html",
  },
};

const mocks = vi.hoisted(() => ({
  runVibResolve: null as ((value: VibResult) => void) | null,
  readDocsVisualMock: vi.fn<(...args: [string, string]) => Promise<DocsVisualReadResult | null>>(),
  readDocsHtmlMock: vi.fn<(...args: [string, string]) => Promise<DocsHtmlReadResult | null>>(),
  runVibMock: vi.fn<(...args: [string[], string?]) => Promise<VibResult>>(),
  pickFolderMock: vi.fn<(...args: [string?]) => Promise<string | null>>(),
  addExtraDocSourceMock: vi.fn<(...args: [string, string]) => Promise<{ ok: boolean; sources: string[]; entries: DocsIndexEntry[]; warnings: string[] }>>(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    listDocsIndex: vi.fn(async () => docsIndex),
    listExtraDocSources: vi.fn(async () => ({ ok: true, sources: [], entries: docsIndex, warnings: [] })),
    readFile: vi.fn(async (_root: string, path: string) => docPayloads[path]),
    readDocsVisual: mocks.readDocsVisualMock,
    readDocsHtml: mocks.readDocsHtmlMock,
    runVib: mocks.runVibMock,
    pickFolder: mocks.pickFolderMock,
    addExtraDocSource: mocks.addExtraDocSourceMock,
    removeExtraDocSource: vi.fn(),
  };
});

describe("DocsViewer generation epoch", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.runVibResolve = null;
    mocks.readDocsVisualMock.mockReset();
    mocks.readDocsHtmlMock.mockReset();
    mocks.runVibMock.mockReset();
    mocks.pickFolderMock.mockReset();
    mocks.addExtraDocSourceMock.mockReset();
    mocks.readDocsVisualMock.mockResolvedValue(null);
    mocks.readDocsHtmlMock.mockResolvedValue(null);
    mocks.runVibMock.mockImplementation(() => new Promise((resolve) => { mocks.runVibResolve = resolve; }));
    mocks.pickFolderMock.mockResolvedValue(null);
    mocks.addExtraDocSourceMock.mockResolvedValue({ ok: true, sources: ["docs/plans"], entries: docsIndex, warnings: [] });
  });

  test("test_generation_epoch_discards_stale_result", async () => {
    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("Context · PROJECT_CONTEXT.md")).toBeInTheDocument();
    fireEvent.click(await screen.findByText("Generate Canvas"));
    expect(mocks.runVibMock).toHaveBeenCalledWith(["docs-build", "--", "PROJECT_CONTEXT.md"], "/tmp/project");

    fireEvent.change(screen.getByPlaceholderText("제목, 경로, 카테고리 검색..."), { target: { value: "README" } });
    fireEvent.click(await screen.findByText("Doc B"));
    expect(await screen.findByText("Readme · README.md")).toBeInTheDocument();
    const readCallsBeforeStaleGenerationFinishes = mocks.readDocsVisualMock.mock.calls.length;

    mocks.readDocsVisualMock.mockResolvedValue(readyArtifact);
    mocks.runVibResolve?.({ ok: true, exit_code: 0, stdout: "", stderr: "" });
    await new Promise((resolve) => { setTimeout(resolve, 20); });

    expect(screen.getByText("Readme · README.md")).toBeInTheDocument();
    expect(screen.queryByText("CANVAS READY")).not.toBeInTheDocument();
    expect(mocks.readDocsVisualMock).toHaveBeenCalledTimes(readCallsBeforeStaleGenerationFinishes);
    expect(mocks.readDocsVisualMock).not.toHaveBeenLastCalledWith("/tmp/project", "PROJECT_CONTEXT.md");
  });

  test("ready_canvas_exposes_regenerate_control", async () => {
    mocks.readDocsVisualMock.mockResolvedValue(readyArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    expect(screen.getByText("Regenerate Canvas")).toBeInTheDocument();
  });

  test("canvas_mode_renders_html_iframe", async () => {
    mocks.readDocsVisualMock.mockResolvedValue(visualMindmapArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Canvas" }));

    const frame = await screen.findByTitle("Doc A HTML Canvas");
    expect(frame).toBeInTheDocument();
    expect(frame).toHaveAttribute("sandbox", "");
    expect(frame).toHaveStyle({ height: "2550px" });
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("HTML Canvas"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("data-diagram-visual=\"mindmap\""));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("overflow-wrap: anywhere"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("Outline"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("Outline · Source Order"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("Late Section"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("data-canvas-visual-mode=\"document-control-map\""));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("signal-board"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("data-canvas-source-order=\"sections\""));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("source-spine"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("source-preview"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("Goal bullet kept from source"));
    expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("white-space: nowrap"));
    expect(frame).not.toHaveAttribute("srcdoc", expect.stringContaining("writing-mode: vertical-rl"));
    const srcdoc = frame.getAttribute("srcdoc") ?? "";
    expect(srcdoc.indexOf('aria-label="Outline Source Order"')).toBeLessThan(srcdoc.indexOf('aria-label="Flow"'));
    expect(srcdoc.indexOf("Section 1")).toBeLessThan(srcdoc.indexOf("Late Section"));
    expect(srcdoc.indexOf('aria-label="Flow"')).toBeLessThan(srcdoc.indexOf('aria-label="Decisions"'));
    expect(srcdoc.indexOf('aria-label="Decisions"')).toBeLessThan(srcdoc.indexOf('aria-label="Actions"'));
    expect(srcdoc.indexOf('aria-label="Actions"')).toBeLessThan(srcdoc.indexOf('aria-label="Risks"'));
    expect(srcdoc.indexOf('aria-label="Risks"')).toBeLessThan(srcdoc.indexOf('aria-label="Glossary"'));
    expect(frame).not.toHaveAttribute("srcdoc", expect.stringContaining("<pre><code>mindmap"));
  });

  test("split_mode_uses_taller_canvas_for_narrow_column", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 980 });
    mocks.readDocsVisualMock.mockResolvedValue(visualMindmapArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Split" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Split" }));

    const frame = await screen.findByTitle("Doc A HTML Canvas");
    expect(frame).toHaveStyle({ height: "6450px" });
  });

  test("split_tab_remains_available_on_minimal_layout", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 760 });
    mocks.readDocsVisualMock.mockResolvedValue(visualMindmapArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Split" })).toBeInTheDocument();
  });

  test("folder_picker_accepts_windows_path_casing_inside_project", async () => {
    mocks.pickFolderMock.mockResolvedValue("c:\\repo\\docs\\plans");

    render(<DocsViewer projectDir={"C:\\Repo"} />);

    expect(await screen.findByText("Context · PROJECT_CONTEXT.md")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "+ 소스 추가" }));
    fireEvent.click(screen.getByRole("button", { name: "탐색" }));

    expect(await screen.findByDisplayValue("docs/plans")).toBeInTheDocument();
    expect(screen.queryByText("프로젝트 루트 안쪽 폴더만 추가할 수 있어요.")).not.toBeInTheDocument();
  });

  test("canvas_html_iframe_escapes_hostile_artifact_text", async () => {
    mocks.readDocsVisualMock.mockResolvedValue(hostileArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Canvas" }));

    const frame = await screen.findByTitle("Doc <script>alert('title')</script> HTML Canvas");
    const srcdoc = frame.getAttribute("srcdoc") ?? "";
    expect(srcdoc).toContain("&lt;script&gt;alert(&#39;tldr&#39;)&lt;/script&gt;");
    expect(srcdoc).toContain("&lt;img src=x onerror=alert(&#39;rule&#39;)&gt;");
    expect(srcdoc).toContain("&lt;iframe src=&#39;file:///etc/passwd&#39;&gt;&lt;/iframe&gt;");
    expect(srcdoc).not.toContain("<script>alert('tldr')</script>");
    expect(srcdoc).not.toContain("<img src=x onerror=alert('rule')>");
    expect(srcdoc).not.toContain("<iframe src='file:///etc/passwd'></iframe>");
  });

  test("raw_html_mode_renders_raw_artifact_in_sandboxed_iframe", async () => {
    mocks.readDocsVisualMock.mockResolvedValue(readyArtifact);
    mocks.readDocsHtmlMock.mockResolvedValue(readyHtmlArtifact);

    render(<DocsViewer projectDir="/tmp/project" />);

    expect(await screen.findByText("CANVAS READY")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Raw HTML" }));

    const frame = await screen.findByTitle("Doc A Raw HTML Canvas");
    const srcdoc = frame.getAttribute("srcdoc") ?? "";
    expect(frame).toHaveAttribute("sandbox", "");
    expect(frame).toHaveStyle({ height: "1426px" });
    expect(srcdoc).toContain("<script>window.parent.hacked=true</script>");
    expect(srcdoc).toContain("Content-Security-Policy");
    expect(srcdoc).toContain("font-family: Georgia");
    expect(srcdoc).toContain("<li>Readable list</li>");
    expect(srcdoc).toContain("<table><tr><td>Mode</td><td>Purpose</td></tr></table>");
  });
});
// === ANCHOR: DOCSVIEWER_EPOCH_TEST_END ===
