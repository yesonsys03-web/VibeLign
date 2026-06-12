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

describe("formatWorkOutputLine (codex)", () => {
  it("renders_thread_start_and_agent_message", () => {
    expect(formatWorkOutputLine(JSON.stringify({ type: "thread.started", thread_id: "t1" }))).toEqual([
      { kind: "info", text: "세션 시작 — Codex" },
    ]);
    const msg = JSON.stringify({
      type: "item.completed",
      item: { id: "item_0", type: "agent_message", text: "OK 코덱스 검증" },
    });
    expect(formatWorkOutputLine(msg)).toEqual([{ kind: "text", text: "OK 코덱스 검증" }]);
  });

  it("renders_command_execution_and_file_change_as_tools", () => {
    const cmd = JSON.stringify({
      type: "item.started",
      item: { type: "command_execution", command: "npm test" },
    });
    expect(formatWorkOutputLine(cmd)).toEqual([{ kind: "tool", text: "🔧 명령 실행 — npm test" }]);
    const change = JSON.stringify({
      type: "item.completed",
      item: { type: "file_change", changes: [{ path: "src/a.ts" }] },
    });
    expect(formatWorkOutputLine(change)).toEqual([{ kind: "tool", text: "🔧 파일 수정 — src/a.ts" }]);
  });

  it("renders_turn_completion_and_failure", () => {
    expect(formatWorkOutputLine(JSON.stringify({ type: "turn.completed", usage: {} }))).toEqual([
      { kind: "result", text: "✅ 작업 완료" },
    ]);
    expect(
      formatWorkOutputLine(JSON.stringify({ type: "turn.failed", error: { message: "한도 초과" } })),
    ).toEqual([{ kind: "error", text: "❌ 한도 초과" }]);
  });

  it("hides_turn_started_and_reasoning_items", () => {
    expect(formatWorkOutputLine(JSON.stringify({ type: "turn.started" }))).toEqual([]);
    expect(
      formatWorkOutputLine(JSON.stringify({ type: "item.completed", item: { type: "reasoning" } })),
    ).toEqual([]);
  });
});
// === ANCHOR: WORK_STREAM_JSON_TEST_END ===
