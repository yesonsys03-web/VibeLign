// === ANCHOR: RUN_VIEW_START ===
// 실행해보기 패널의 순수 표시 로직 — 백엔드 상태/타입을 한글 카피·톤으로 변환.
// RunPanel 에서 분리해 단위 테스트한다(컴포넌트 렌더 없이).
import type { RunProjectKind, RunStatusKind } from "../vib/run";

/** 감지된 프로젝트 타입의 사용자 라벨. */
export function kindLabel(kind: RunProjectKind): string {
  switch (kind) {
    case "web":
      return "웹앱";
    case "electron":
      return "데스크톱 앱(Electron)";
    case "unknown":
      return "프로그램";
  }
}

export type RunTone = "idle" | "info" | "running" | "success" | "error";

export interface RunStatusView {
  text: string;
  tone: RunTone;
}

/** 실행 상태 → 카피 + 톤. installing/running 은 진행, done/failed/stopped 은 종료. */
export function statusView(status: RunStatusKind): RunStatusView {
  switch (status) {
    case "installing":
      return { text: "준비 중… 필요한 패키지를 설치하고 있어요", tone: "info" };
    case "running":
      return { text: "실행 중 — 직접 써보면서 작동을 확인해 보세요", tone: "running" };
    case "done":
      return { text: "실행이 끝났어요", tone: "success" };
    case "failed":
      return { text: "실행에 실패했어요 — 출력 끝부분을 확인하세요", tone: "error" };
    case "stopped":
      return { text: "실행을 중지했어요", tone: "idle" };
  }
}

/** 진행 단계(설치/실행) 출력 라벨. */
export function phaseLabel(phase: "install" | "run"): string {
  return phase === "install" ? "설치" : "실행";
}

/** 종료 상태인가 — 중지/재실행 버튼 분기에 쓴다. */
export function isTerminal(status: RunStatusKind): boolean {
  return status === "done" || status === "failed" || status === "stopped";
}

/** 실패만 작업방 "에러 고쳐줘" 대상(M3b) — stopped/done 은 사용자 의도/정상. */
export function isFixable(status: RunStatusKind): boolean {
  return status === "failed";
}

/** 작업방 핸드오프용 출력 tail. stdout+stderr 를 함께 — vite/next 는 시작 에러를
 * stdout 에 찍어서 stderr 만 거르면 빈 페이로드가 된다(advisor). stderr 는 표시 표식. */
export function collectErrorTail(
  lines: ReadonlyArray<{ stream: "stdout" | "stderr"; text: string }>,
  max = 40,
): string {
  return lines
    .slice(-max)
    .map((l) => (l.stream === "stderr" ? `! ${l.text}` : l.text))
    .join("\n");
}
// === ANCHOR: RUN_VIEW_END ===
