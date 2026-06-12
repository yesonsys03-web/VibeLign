// === ANCHOR: WORK_STREAM_JSON_START ===
/** claude -p --output-format stream-json 라인 → 사용자 표시 라인 변환 (순수 함수).
 *  러너(work_room.rs)는 라인을 해석 없이 그대로 흘리고, 해석은 전부 이 모듈이 맡는다 —
 *  CLI 출력 형식이 바뀌어도 Rust 쪽은 영향이 없다. JSON 이 아닌 라인(stderr 등)은
 *  raw 로 그대로 보여준다. */

export type WorkLineKind = "info" | "text" | "tool" | "result" | "error" | "raw";

export interface WorkDisplayLine {
  kind: WorkLineKind;
  text: string;
}

interface ContentItem {
  type?: string;
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  is_error?: boolean;
}

/** codex exec --json 의 item 구조 (2026-06-12 실캡처 기준). */
interface CodexItem {
  type?: string;
  text?: string;
  command?: string;
  changes?: { path?: string }[];
  message?: string;
}

/** 도구 호출 한 줄 요약 — 초보가 "지금 뭘 하는지" 알 수 있는 최소 단서(파일·명령). */
function toolSummary(name: string, input: Record<string, unknown> | undefined): string {
  const target =
    input && typeof input.file_path === "string"
      ? input.file_path
      : input && typeof input.command === "string"
        ? input.command
        : input && typeof input.pattern === "string"
          ? input.pattern
          : "";
  return target ? `🔧 ${name} — ${target}` : `🔧 ${name}`;
}

export function formatWorkOutputLine(line: string): WorkDisplayLine[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(line);
  } catch {
    return [{ kind: "raw", text: line }];
  }
  if (typeof parsed !== "object" || parsed === null) {
    return [{ kind: "raw", text: line }];
  }
  const obj = parsed as Record<string, unknown> & { message?: { content?: ContentItem[] } };
  switch (obj.type) {
    case "system":
      if (obj.subtype === "init") {
        const model = typeof obj.model === "string" ? obj.model : "";
        return [{ kind: "info", text: model ? `세션 시작 — 모델: ${model}` : "세션 시작" }];
      }
      return [];
    case "assistant": {
      const content = obj.message?.content;
      if (!Array.isArray(content)) return [];
      const out: WorkDisplayLine[] = [];
      for (const item of content) {
        if (item?.type === "text" && typeof item.text === "string" && item.text.trim()) {
          out.push({ kind: "text", text: item.text.trim() });
        } else if (item?.type === "tool_use" && typeof item.name === "string") {
          out.push({ kind: "tool", text: toolSummary(item.name, item.input) });
        }
      }
      return out;
    }
    case "user": {
      // 도구 결과 본문은 소음이라 숨기고, 실패 신호만 남긴다.
      const content = obj.message?.content;
      if (!Array.isArray(content)) return [];
      return content
        .filter((item) => item?.type === "tool_result" && item.is_error === true)
        .map(() => ({ kind: "error" as const, text: "⚠ 도구 실행 실패 — 에이전트가 이어서 대처합니다" }));
    }
    case "result": {
      const isError = typeof obj.subtype === "string" && obj.subtype !== "success";
      const resultText = typeof obj.result === "string" ? obj.result.trim() : "";
      if (isError) {
        return [{ kind: "error", text: resultText ? `❌ ${resultText}` : "❌ 작업이 실패했어요" }];
      }
      // 비용($) 미표시: 작업방 주 사용자는 정액 구독자라 total_cost_usd 는 실제 청구가
      // 아니다 — 숫자가 오히려 "방금 돈 나갔나?" 불안을 준다(2026-06-12 사용자 피드백).
      return [{ kind: "result", text: `✅ 작업 완료${resultText ? `\n${resultText}` : ""}` }];
    }
    // ── Codex(`codex exec --json`) JSONL — claude 와 type 네임스페이스가 달라 충돌 없음 ──
    case "thread.started":
      return [{ kind: "info", text: "세션 시작 — Codex" }];
    case "item.started": {
      const item = obj.item as CodexItem | undefined;
      if (item?.type === "command_execution" && typeof item.command === "string") {
        return [{ kind: "tool", text: `🔧 명령 실행 — ${item.command}` }];
      }
      return [];
    }
    case "item.completed": {
      const item = obj.item as CodexItem | undefined;
      if (!item) return [];
      if (item.type === "agent_message" && typeof item.text === "string" && item.text.trim()) {
        return [{ kind: "text", text: item.text.trim() }];
      }
      if (item.type === "file_change") {
        const first = Array.isArray(item.changes) && typeof item.changes[0]?.path === "string" ? ` — ${item.changes[0].path}` : "";
        return [{ kind: "tool", text: `🔧 파일 수정${first}` }];
      }
      if (item.type === "error" && typeof item.message === "string") {
        return [{ kind: "error", text: `❌ ${item.message}` }];
      }
      return [];
    }
    case "turn.completed":
      return [{ kind: "result", text: "✅ 작업 완료" }];
    case "turn.failed": {
      const err = (obj.error as { message?: string } | undefined)?.message;
      return [{ kind: "error", text: err ? `❌ ${err}` : "❌ 작업이 실패했어요" }];
    }
    default:
      return [];
  }
}
// === ANCHOR: WORK_STREAM_JSON_END ===
