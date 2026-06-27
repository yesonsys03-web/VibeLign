import { describe, expect, test } from "vitest";

import { applyReportSessionDraftToEmitPayload } from "../reportSessionDraft";
import type { ReportSessionDraft } from "../reportSessionDraft";
import type { EmitPayload, RModel } from "../../../lib/vib/reportModel";

function emptyModel(): RModel {
  return { title: "T", report_type: "work", date: "2026-06-23", source_plan_path: "plan.md", sections: [] };
}

function basePayload(): EmitPayload {
  return {
    ok: true,
    report_type: "work",
    slug: "s",
    key: "k",
    base: emptyModel(),
    polished: emptyModel(),
    guards: [],
    vague_warnings: [],
    quality: {} as EmitPayload["quality"],
    assistance: {} as EmitPayload["assistance"],
  };
}

const MARKDOWN = [
  "- **초보 사용자 (코알못)**: 규칙을 모릅니다.",
  "  - *완화 방안*: 기본값을 초보 모드로 둡니다.",
  "- **숙련된 사용자**: 직접 선택 모드로 전환합니다.",
  "## 향후 조치 계획",
  "미나의 탐색 결과를 바탕으로 진행합니다.",
].join("\n");

describe("applyReportSessionDraftToEmitPayload", () => {
  test("renders the draft markdown as structured blocks, not one raw paragraph", () => {
    const draft: ReportSessionDraft = { entries: [{ id: "a", text: MARKDOWN, source: "suggestion" }] };
    const out = applyReportSessionDraftToEmitPayload(basePayload(), draft);

    const section = out.base.sections.at(-1);
    expect(section?.heading).toBe("사용자 확인 보완 초안");
    const blocks = section?.blocks ?? [];

    // Must NOT be a single paragraph holding the whole markdown blob.
    expect(blocks.length).toBeGreaterThan(1);

    // Bullet lines become a bullets block; inline markers are KEPT verbatim so the HTML
    // renderer can convert **bold**/*em* to <strong>/<em> (html_renderer._render_inline).
    const bullets = blocks.find((b) => b.kind === "bullets");
    expect(bullets).toBeDefined();
    const joined = (bullets?.items ?? []).join("\n");
    expect(joined).toContain("**초보 사용자 (코알못)**: 규칙을 모릅니다.");
    expect(bullets?.items.some((i) => i.includes("↳ *완화 방안*: 기본값을 초보 모드로"))).toBe(true);

    // Headings keep their text but drop the leading '#'.
    const headingBlock = blocks.find((b) => b.kind === "paragraph" && b.text === "향후 조치 계획");
    expect(headingBlock).toBeDefined();

    // No block leaks raw markdown syntax.
    for (const b of blocks) {
      expect(b.text).not.toContain("##");
      expect(b.text.startsWith("- ")).toBe(false);
    }

    // base and polished both receive the section.
    expect(out.polished.sections.at(-1)?.heading).toBe("사용자 확인 보완 초안");
  });

  test("handles Windows CRLF line endings without leaking carriage returns", () => {
    const crlf = MARKDOWN.replace(/\n/g, "\r\n");
    const draft: ReportSessionDraft = { entries: [{ id: "a", text: crlf, source: "suggestion" }] };
    const out = applyReportSessionDraftToEmitPayload(basePayload(), draft);
    const blocks = out.base.sections.at(-1)?.blocks ?? [];

    // Same structured result as the LF case — no stray \r in any block text or item.
    expect(blocks.length).toBeGreaterThan(1);
    for (const b of blocks) {
      expect(b.text).not.toContain("\r");
      for (const item of b.items) expect(item).not.toContain("\r");
    }
    const bullets = blocks.find((b) => b.kind === "bullets");
    expect(bullets?.items.some((i) => i === "**초보 사용자 (코알못)**: 규칙을 모릅니다.")).toBe(true);
    expect(blocks.some((b) => b.kind === "paragraph" && b.text === "향후 조치 계획")).toBe(true);
  });

  test("returns the payload unchanged when the draft is empty", () => {
    const out = applyReportSessionDraftToEmitPayload(basePayload(), { entries: [] });
    expect(out.base.sections).toHaveLength(0);
  });
});
