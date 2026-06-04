import type { GuardResult } from "../../lib/vib";

export type HomeCopy = {
  readonly title: string;
  readonly detail: string;
  readonly accent: string;
};

export type HomeActionCopy = HomeCopy & {
  readonly needsAction: boolean;
};

export function guardSafetyCopy(guardResult: GuardResult | null, watchOn: boolean): HomeCopy {
  if (guardResult?.status === "fail") {
    return {
      title: "확인이 필요한 문제가 있어요",
      detail: "안전 검사에서 직접 확인할 항목을 찾았어요.",
      accent: "#FF4D4D",
    };
  }
  if (guardResult?.status === "warn") {
    return {
      title: "자동 안전장치 일부를 확인하세요",
      detail: "안전 검사에서 점검이 필요한 항목을 찾았어요.",
      accent: "#FFD166",
    };
  }
  if (guardResult?.status === "pass" || watchOn) {
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

export function guardNextActionCopy(guardResult: GuardResult | null, watchOn: boolean): HomeActionCopy {
  if (guardResult?.status === "fail" || guardResult?.status === "warn") {
    return {
      title: "안전 검사 결과를 확인하세요",
      detail: "문제가 있는 파일과 다음 행동을 쉬운 목록으로 확인할 수 있어요.",
      accent: guardResult.status === "fail" ? "#FF4D4D" : "#FFD166",
      needsAction: true,
    };
  }
  if (guardResult?.status === "pass") {
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
