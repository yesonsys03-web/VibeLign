// === ANCHOR: PLANNINGINSTRUCTION_START ===
import { planningPersonaRoleLabel, type PlanningPersonaId } from "../../pages/planning/PlanningPersonas";

interface PlanningWorkInstructionInput {
  readonly prompt: string;
  readonly outputPath: string;
  readonly persona?: PlanningWorkPersona;
}

export type PlanningWorkPersona = PlanningPersonaId;

const PERSONA_CLI_DETAILS: Record<PlanningWorkPersona, { readonly cliName: string; readonly role: string }> = {
  chloe: {
    cliName: "Claude Code CLI",
    role: "구현 구조와 컴포넌트 분리를 먼저 설계합니다.",
  },
  gio: {
    cliName: "Codex CLI",
    role: "변경 위험, 테스트 기준, 정책 위반 가능성을 검토합니다.",
  },
  mina: {
    cliName: "Antigravity CLI",
    role: "대안 흐름, 놓친 사용자 시나리오, 탐색 관점을 보강합니다.",
  },
  deepseek: {
    cliName: "OpenCode CLI",
    role: "다른 관점을 쉽게 풀어 설명하고, 막힌 지점과 남은 질문을 정리합니다.",
  },
};

// === ANCHOR: PLANNINGINSTRUCTION_BUILDPLANNINGWORKINSTRUCTION_START ===
export function buildPlanningWorkInstruction({ prompt, outputPath, persona }: PlanningWorkInstructionInput): string {
  const trimmedPrompt = prompt.trim() || "저장된 기획안을 기준으로 구현 범위를 정리하세요.";
  const personaDetails = persona ? PERSONA_CLI_DETAILS[persona] : null;
  return [
    "저장된 기획안을 기준으로 AI 작업을 시작하세요.",
    ...(persona && personaDetails
      ? [
          "",
          `대상 역할: ${planningPersonaRoleLabel(persona)}`,
          `사용 CLI: ${personaDetails.cliName}`,
          `역할 기준: ${personaDetails.role}`,
        ]
      : []),
    "",
    `저장된 기획안: ${outputPath}`,
    `요청 요약: ${trimmedPrompt}`,
    "",
    "작업 기준:",
    "- 먼저 저장된 Markdown 기획안을 읽고 구현 범위, 제외할 것, 아직 결정이 필요한 질문을 확인하세요.",
    "- 기존 코드 구조를 읽고 컴포넌트/모듈 단위로 작게 나눠 작업하세요.",
    "- 공식 CLI를 사용할 때는 사용자가 이미 로그인한 CLI 프로세스만 실행하고 stdout/stderr만 캡처하세요.",
    "- 토큰, 쿠키, 세션 파일을 읽지 마세요.",
    "- 변경 전 baseline 테스트와 새 동작 RED 테스트를 먼저 작성하세요.",
  ].join("\n");
}
// === ANCHOR: PLANNINGINSTRUCTION_BUILDPLANNINGWORKINSTRUCTION_END ===
// === ANCHOR: PLANNINGINSTRUCTION_END ===
