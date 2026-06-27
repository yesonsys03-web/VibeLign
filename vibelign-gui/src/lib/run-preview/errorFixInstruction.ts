// === ANCHOR: ERROR_FIX_INSTRUCTION_START ===
// 실행 실패 → 작업방 핸드오프 지시문 (plans/2026-06-12-실행해보기-run-preview-design.md §6).
// "실패하면 작업방으로 넘겨 AI가 고치는 루프를 닫는다"의 키스톤. 순수 함수(테스트 용이).
//
// 프레이밍 주의(advisor):
// - 이건 테스트 실패가 아니라 "앱이 dev 모드로 켜질 때 난 오류"다(포트 충돌·문법·누락 의존성).
// - planPath 가 있을 때만 기획안을 참조(plan-less 도 동작).
// - 에이전트에게 다시 실행/미리보기를 시키지 않는다 — 재실행은 사용자 몫(재진입 함정 회피).

export interface RunErrorFixInput {
  /** 실행 출력 끝부분(stdout+stderr 혼합 tail). */
  readonly errorText: string;
  /** 기획안 경로 — 있으면 범위 참조, 없으면(plan-less) 생략. */
  readonly planPath: string | null;
}

// === ANCHOR: ERROR_FIX_INSTRUCTION_BUILD_START ===
export function buildRunErrorFixInstruction({ errorText, planPath }: RunErrorFixInput): string {
  const trimmed = errorText.trim();
  return [
    "방금 이 앱을 dev 모드로 실행했는데 켜지지 않고 실패했어요. 아래 실행 출력을 보고 원인을 찾아 고쳐주세요.",
    "이건 테스트 실패가 아니라 앱이 시작될 때 난 오류예요 — 포트 충돌, 문법 오류, 누락된 의존성 같은 게 흔한 원인이에요.",
    "",
    "[실행 출력(끝부분)]",
    trimmed || "(캡처된 출력이 없어요 — 코드와 설정에서 시작 실패 원인을 추정해 주세요.)",
    "",
    ...(planPath
      ? [`참고: 이 작업의 기획안은 ${planPath} 에 있어요 — 기획안 범위를 벗어나지 않게 고쳐주세요.`, ""]
      : []),
    "작업 기준:",
    "- 원인을 먼저 한두 줄로 설명한 뒤, 최소한의 변경으로 고치세요.",
    "- 실행 방법을 못 찾은 상태라면 프로젝트 루트에 index.html 파일을 만들거나, package.json에 dev 또는 start 스크립트를 제공하세요.",
    "- 앵커 경계를 지키고, 약속한 범위 밖 파일은 건드리기 전에 확인하세요.",
    "- 고친 뒤 다시 실행이나 미리보기는 사용자가 직접 합니다 — dev 서버를 직접 띄우지 마세요.",
  ].join("\n");
}
// === ANCHOR: ERROR_FIX_INSTRUCTION_BUILD_END ===
// === ANCHOR: ERROR_FIX_INSTRUCTION_END ===
