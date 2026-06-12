// === ANCHOR: WORK_STREAM_JSON_TEST_START ===
import { describe, expect, it } from "vitest";

import { formatWorkOutputLine } from "./streamJson";

describe("formatWorkOutputLine", () => {
  it("passes_non_json_through_as_raw", () => {
    expect(formatWorkOutputLine("plain stderr text")).toEqual([
      { kind: "raw", text: "plain stderr text" },
    ]);
  });

  it("renders_init_with_model", () => {
    const line = JSON.stringify({ type: "system", subtype: "init", model: "claude-sonnet-4-6" });
    expect(formatWorkOutputLine(line)).toEqual([
      { kind: "info", text: "세션 시작 — 모델: claude-sonnet-4-6" },
    ]);
  });

  it("extracts_assistant_text_and_tool_use_with_file_target", () => {
    const line = JSON.stringify({
      type: "assistant",
      message: {
        content: [
          { type: "text", text: " 파일을 수정할게요 " },
          { type: "tool_use", name: "Edit", input: { file_path: "src/a.ts" } },
        ],
      },
    });
    expect(formatWorkOutputLine(line)).toEqual([
      { kind: "text", text: "파일을 수정할게요" },
      { kind: "tool", text: "🔧 Edit — src/a.ts" },
    ]);
  });

  it("hides_tool_results_but_surfaces_errors", () => {
    const ok = JSON.stringify({
      type: "user",
      message: { content: [{ type: "tool_result", is_error: false }] },
    });
    const failed = JSON.stringify({
      type: "user",
      message: { content: [{ type: "tool_result", is_error: true }] },
    });
    expect(formatWorkOutputLine(ok)).toEqual([]);
    expect(formatWorkOutputLine(failed)).toHaveLength(1);
    expect(formatWorkOutputLine(failed)[0].kind).toBe("error");
  });

  it("renders_success_result_with_cost", () => {
    const line = JSON.stringify({
      type: "result",
      subtype: "success",
      result: "끝",
      total_cost_usd: 0.1234,
    });
    const [item] = formatWorkOutputLine(line);
    expect(item.kind).toBe("result");
    expect(item.text).toContain("✅ 작업 완료");
    expect(item.text).toContain("$0.12");
    expect(item.text).toContain("끝");
  });

  it("renders_error_result_as_error", () => {
    const line = JSON.stringify({ type: "result", subtype: "error_max_turns", result: "한도 초과" });
    expect(formatWorkOutputLine(line)).toEqual([{ kind: "error", text: "❌ 한도 초과" }]);
  });

  it("ignores_unknown_event_types", () => {
    expect(formatWorkOutputLine(JSON.stringify({ type: "stream_event" }))).toEqual([]);
  });
});
// === ANCHOR: WORK_STREAM_JSON_TEST_END ===
