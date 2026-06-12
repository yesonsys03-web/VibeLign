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
      const cost =
        typeof obj.total_cost_usd === "number" ? ` (비용 ~$${obj.total_cost_usd.toFixed(2)})` : "";
      return [{ kind: "result", text: `✅ 작업 완료${cost}${resultText ? `\n${resultText}` : ""}` }];
    }
    default:
      return [];
  }
}
// === ANCHOR: WORK_STREAM_JSON_END ===
