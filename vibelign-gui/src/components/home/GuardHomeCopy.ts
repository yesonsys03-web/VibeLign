// === ANCHOR: GUARDHOMECOPY_START ===
import type { GuardResult } from "../../lib/vib";

export type HomeCopy = {
  readonly title: string;
  readonly detail: string;
  readonly accent: string;
};

export type HomeActionCopy = HomeCopy & {
  readonly needsAction: boolean;
};

// === ANCHOR: GUARDHOMECOPY_GUARDSAFETYCOPY_START ===
export function guardSafetyCopy(guardResult: GuardResult | null, watchOn: boolean): HomeCopy {
  // 3단 verdict 기준(2026-06-12) — 공포 어휘는 stop(실제 위반) 전용. 위생 누적은 '준비'로 말한다.
  if (guardResult?.verdict === "stop") {
    return {
      title: "확인이 필요한 문제가 있어요",
      detail: "안전 검사에서 직접 확인할 항목을 찾았어요.",
      accent: "#FF4D4D",
    };
  }
  if (guardResult?.verdict === "prepare") {
    return {
      title: "이번 변경은 범위 안이에요 — 준비 항목이 있어요",
      detail: "다음 AI 작업 전에 준비하면 좋은 항목을 찾았어요.",
      accent: "#FFD166",
    };
  }
  if (guardResult?.verdict === "pass" || watchOn) {
    return {
      title: "안전장치가 켜져 있어요",
      detail: "파일 변경과 안전 검사를 확인할 준비가 되어 있어요.",
      accent: "#4DFF91",
    };
  }
  return {
    title: "상태를 아직 확인하지 못했어요",
    detail: "상태 확인을 실행하면 프로젝트 안전 상태가 더 정확해져요.",
    accent: "#B8B4B0",
  };
}
// === ANCHOR: GUARDHOMECOPY_GUARDSAFETYCOPY_END ===

// === ANCHOR: GUARDHOMECOPY_GUARDNEXTACTIONCOPY_START ===
export function guardNextActionCopy(guardResult: GuardResult | null, watchOn: boolean): HomeActionCopy {
  if (guardResult?.verdict === "stop") {
    return {
      title: "안전 검사 결과를 확인하세요",
      detail: "문제가 있는 파일과 다음 행동을 쉬운 목록으로 확인할 수 있어요.",
      accent: "#FF4D4D",
      needsAction: true,
    };
  }
  if (guardResult?.verdict === "prepare") {
    return {
      title: "다음 작업 전 준비 항목을 확인하세요",
      detail: "앵커 설정 같은 준비를 마치면 다음 AI 작업이 더 안전해져요.",
      accent: "#FFD166",
      needsAction: true,
    };
  }
  if (guardResult?.verdict === "pass") {
    return {
      title: "바로 AI 코딩해도 괜찮아요",
      detail: "지금은 먼저 처리할 문제가 보이지 않아요.",
      accent: "#4DFF91",
      needsAction: false,
    };
  }
  if (!watchOn) {
    return {
      title: "프로젝트 상태를 한 번 확인하세요",
      detail: "아래 버튼으로 프로젝트 상태를 바로 확인할 수 있어요.",
      accent: "#FFD166",
      needsAction: false,
    };
  }
  return {
    title: "바로 AI 코딩해도 괜찮아요",
    detail: "지금은 먼저 처리할 문제가 보이지 않아요.",
    accent: "#4DFF91",
    needsAction: false,
  };
}
// === ANCHOR: GUARDHOMECOPY_GUARDNEXTACTIONCOPY_END ===
// === ANCHOR: GUARDHOMECOPY_END ===
