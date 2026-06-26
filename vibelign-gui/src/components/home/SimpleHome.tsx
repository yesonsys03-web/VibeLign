// === ANCHOR: SIMPLEHOME_START ===
import type { ReactNode } from "react";
import type { GuardResult } from "../../lib/vib";
import type { ScopeReportResult } from "../../lib/home/scopeReport";
import { guardNextActionCopy, guardSafetyCopy } from "./GuardHomeCopy";
import { SafetyAutomationNotice } from "./SafetyAutomationNotice";

interface SimpleHomeProps {
  readonly guardResult: GuardResult | null;
  readonly watchOn: boolean;
  readonly watchError: string | null;
  readonly hasCheckpoint: boolean;
  readonly guardCheckPending: boolean;
  readonly guardCheckError: string | null;
  readonly scopeReport?: ScopeReportResult | null;
  readonly onRetryWatch: () => void;
  readonly onRunGuard: () => void;
  readonly onShowAdvanced: () => void;
  readonly onNavigateBackups: () => void;
  readonly onOpenGuardDetails: () => void;
}

// === ANCHOR: SIMPLEHOME_SIMPLEHOME_START ===
export function SimpleHome({
  guardResult,
  watchOn,
  watchError,
  hasCheckpoint,
  guardCheckPending,
  guardCheckError,
  scopeReport = null,
  onRetryWatch,
  onRunGuard,
  onShowAdvanced,
  onNavigateBackups,
  onOpenGuardDetails,
}: SimpleHomeProps) {
  const safety = guardSafetyCopy(guardResult, watchOn);
  const nextAction = guardNextActionCopy(guardResult, watchOn);
  const canRunGuard = !nextAction.needsAction && !watchOn;
  // 3단 verdict(ee86b90) 기준 — 위반(stop)·준비(prepare) 모두 상세 진입을 연다.
  // status(fail/warn)는 구 기계 게이트라 위생 재분류(92358a9) 후 prepare 를 못 잡는다.
  const hasGuardProblemDetails = guardResult?.verdict === "stop" || guardResult?.verdict === "prepare";
  return (
    <section style={{ display: "grid", gap: 10 }}>
      <SafetyAutomationNotice rawError={watchError} onRetry={onRetryWatch} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
        <HomeStatusBlock title="프로젝트 안전 상태" accent={safety.accent}>
          <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1.35 }}>{safety.title}</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", lineHeight: 1.55 }}>{safety.detail}</div>
          {scopeReport ? (
            <div style={{ marginTop: 8, fontSize: 12, lineHeight: 1.55, color: scopeReport.outOfScope.length > 0 ? "#A63A00" : "#555" }}>
              <div>
                약속 범위 안 변경 {scopeReport.inScope}건
                {scopeReport.outOfScope.length > 0 ? ` · 범위 밖 ${scopeReport.outOfScope.length}건` : ""}
              </div>
              {scopeReport.outOfScope.length > 0 ? (
                <details style={{ marginTop: 4 }}>
                  <summary style={{ cursor: "pointer" }}>범위 밖 변경이 있어요 — 의도한 작업인지 확인해보세요</summary>
                  {scopeReport.outOfScope.map((path) => (
                    <div key={path} style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>{path}</div>
                  ))}
                </details>
              ) : null}
            </div>
          ) : null}
          {hasGuardProblemDetails ? (
            <button className="btn btn-ghost btn-sm" type="button" onClick={onOpenGuardDetails} style={{ marginTop: 12, fontSize: 12 }}>
              문제 확인하기
            </button>
          ) : null}
        </HomeStatusBlock>

        <HomeStatusBlock title="지금 할 일" accent={nextAction.accent}>
          <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1.35 }}>{nextAction.title}</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", lineHeight: 1.55 }}>{nextAction.detail}</div>
          {guardCheckError ? (
            <div style={{ marginTop: 8, fontSize: 12, color: "#A63A00", fontWeight: 800, lineHeight: 1.45 }}>{guardCheckError}</div>
          ) : null}
          {nextAction.needsAction ? (
            <button className="btn btn-black btn-sm" type="button" onClick={onOpenGuardDetails} style={{ marginTop: 12, fontSize: 12 }}>
              확인하기
            </button>
          ) : null}
          {canRunGuard ? (
            <button className="btn btn-black btn-sm" type="button" disabled={guardCheckPending} onClick={onRunGuard} style={{ marginTop: 12, fontSize: 12 }}>
              {guardCheckPending ? "확인 중..." : "상태 확인하기"}
            </button>
          ) : null}
        </HomeStatusBlock>

        <HomeStatusBlock title="되돌리기" accent="#7B4DFF">
          <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1.35 }}>
            {hasCheckpoint ? "최근 저장 지점이 있어요" : "아직 저장 지점이 없어요"}
          </div>
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", lineHeight: 1.55 }}>
            {hasCheckpoint ? "필요하면 이전 상태 후보를 확인할 수 있어요." : "작업 전 저장 지점을 만들면 되돌리기가 쉬워져요."}
          </div>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onNavigateBackups} style={{ marginTop: 12, fontSize: 12 }}>
            {hasCheckpoint ? "이전 상태로 돌아가기" : "저장 기록 확인하기"}
          </button>
        </HomeStatusBlock>
      </div>

      <button
        className="btn btn-ghost"
        type="button"
        onClick={onShowAdvanced}
        style={{ justifySelf: "start", fontSize: 12, border: "2px solid #1A1A1A" }}
      >
        고급 기능 보기
      </button>
    </section>
  );
}
// === ANCHOR: SIMPLEHOME_SIMPLEHOME_END ===

interface HomeStatusBlockProps {
  readonly title: string;
  readonly accent: string;
  readonly children: ReactNode;
}

// === ANCHOR: SIMPLEHOME_HOMESTATUSBLOCK_START ===
function HomeStatusBlock({ title, accent, children }: HomeStatusBlockProps) {
  return (
    <section style={{ background: "#FFFCF2", border: "2px solid #1A1A1A", padding: 14, minHeight: 132, display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span style={{ width: 10, height: 10, background: accent, border: "2px solid #1A1A1A", flexShrink: 0 }} />
        <h2 style={{ margin: 0, fontSize: 13, fontWeight: 900 }}>{title}</h2>
      </div>
      {children}
    </section>
  );
}
// === ANCHOR: SIMPLEHOME_HOMESTATUSBLOCK_END ===
// === ANCHOR: SIMPLEHOME_END ===
