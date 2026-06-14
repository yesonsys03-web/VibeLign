// === ANCHOR: WORKROOM_CTA_START ===
// 작업방 "실행해보기" CTA 노출 조건 — 완료 상태창 버튼과 하단 sticky 바의 단일 진실원.
// guard 가 안전(pass/prepare)일 때만 실행을 권한다. stop/미실행은 숨겨 안전 우선.
export function runCtaVisible(phase: string, verdict: string | null | undefined): boolean {
  return phase === "finished" && (verdict === "pass" || verdict === "prepare");
}
// === ANCHOR: WORKROOM_CTA_END ===
