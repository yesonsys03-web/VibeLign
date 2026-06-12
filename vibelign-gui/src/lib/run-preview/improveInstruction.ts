// === ANCHOR: IMPROVE_INSTRUCTION_START ===
// 개선 요청 → 작업방 핸드오프 지시문 (plans/2026-06-12-작동검증-개선루프-design.md §4).
// "써보니 부족함" 다듬기. buildRunErrorFixInstruction(에러)와 짝, 순수 함수.
export interface ImproveInstructionInput {
  readonly requestText: string;
  readonly planPath: string | null;
}

// === ANCHOR: IMPROVE_INSTRUCTION_BUILD_START ===
export function buildImproveInstruction({ requestText, planPath }: ImproveInstructionInput): string {
  const trimmed = requestText.trim();
  return [
    "이미 만든 것을 직접 써보니 아래 점을 개선하고 싶어요. 기존 동작을 유지하면서 요청한 부분만 다듬어 주세요.",
    "",
    "[개선 요청]",
    trimmed || "(구체적인 요청이 없어요 — 코드를 보고 사용성·완성도가 떨어지는 부분을 한 가지만 골라 개선해 주세요.)",
    "",
    ...(planPath
      ? [`참고: 이 작업의 기획안은 ${planPath} 에 있어요 — 기획안 범위를 벗어나지 않게 개선해 주세요.`, ""]
      : []),
    "작업 기준:",
    "- 무엇을 바꿀지 먼저 한두 줄로 설명한 뒤, 최소한의 변경으로 개선하세요.",
    "- 앵커 경계를 지키고, 약속한 범위 밖 파일은 건드리기 전에 확인하세요.",
    "- 개선 뒤 다시 실행이나 미리보기는 사용자가 직접 합니다 — dev 서버를 직접 띄우지 마세요.",
  ].join("\n");
}
// === ANCHOR: IMPROVE_INSTRUCTION_BUILD_END ===
// === ANCHOR: IMPROVE_INSTRUCTION_END ===
