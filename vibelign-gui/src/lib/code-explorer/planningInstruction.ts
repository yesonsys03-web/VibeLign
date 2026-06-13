// === ANCHOR: PLANNINGINSTRUCTION_START ===
import { planningPersonaRoleLabel, type PlanningPersonaId } from "../../pages/planning/PlanningPersonas";
import type { PlanningContract } from "../vib/types";

interface PlanningWorkInstructionInput {
  readonly prompt: string;
  readonly outputPath: string;
  readonly persona?: PlanningWorkPersona;
  readonly contract?: PlanningContract | null;
  readonly design?: {
    readonly mockupPath: string;
    readonly tokens: {
      readonly bg: string;
      readonly surface: string;
      readonly text: string;
      readonly primary: string;
      readonly accent: string;
      readonly border: string;
      readonly fontFamily: string;
      readonly radius: string;
      readonly shadow: string;
    };
    readonly motion?: {
      readonly tokens: { readonly duration: string; readonly easing: string };
      readonly recipe: string;
    };
  };
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
export function buildPlanningWorkInstruction({ prompt, outputPath, persona, contract, design }: PlanningWorkInstructionInput): string {
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
    ...(contract
      ? [
          "이번 작업의 계약(기획안에서 추출):",
          `- 목표: ${contract.goal}`,
          ...(contract.scope.length > 0
            ? [`- 손댈 범위(이 밖은 건드리기 전에 사용자에게 확인): ${contract.scope.map((s) => s.path).join(", ")}`]
            : []),
          ...contract.exclusions.map((item) => `- 건드리지 말 것: ${item}`),
          ...contract.doneCriteria.map((item) => `- 완료 기준: ${item}`),
          "",
        ]
      : []),
    ...(design
      ? [
          "[디자인 목업 — 코딩 시작 스캐폴드]",
          `- 목업 파일: ${design.mockupPath} (이 HTML/CSS를 시작점으로 이어서 확장하세요. 레이아웃·구조 보존)`,
          "- 색·폰트·모서리·그림자는 아래 토큰을 CSS 변수(var(--bg) 등)로만 사용:",
          `  --bg:${design.tokens.bg}; --surface:${design.tokens.surface}; --text:${design.tokens.text};`,
          `  --primary:${design.tokens.primary}; --accent:${design.tokens.accent}; --border:${design.tokens.border};`,
          `  --font:${design.tokens.fontFamily}; --radius:${design.tokens.radius}; --shadow:${design.tokens.shadow};`,
          ...(design.motion ? [
            "",
            "[모션 가이드]",
            `- 움직임 성격: ${design.motion.recipe}`,
            `  --dur:${design.motion.tokens.duration}; --ease:${design.motion.tokens.easing};`,
            "- prefers-reduced-motion 을 존중하고 상태 전환 시 공간 일관성을 유지. 실코드에선 CSS/JS 모션 모두 사용 가능.",
          ] : []),
          "",
        ]
      : []),
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
