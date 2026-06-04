import type { ReactNode } from "react";
import type { GuardResult } from "../../lib/vib";
import { guardNextActionCopy, guardSafetyCopy } from "./GuardHomeCopy";
import { SafetyAutomationNotice } from "./SafetyAutomationNotice";

interface SimpleHomeProps {
  readonly guardResult: GuardResult | null;
  readonly watchOn: boolean;
  readonly watchError: string | null;
  readonly hasCheckpoint: boolean;
  readonly onRetryWatch: () => void;
  readonly onShowAdvanced: () => void;
  readonly onNavigateBackups: () => void;
  readonly onOpenGuardDetails: () => void;
}

export function SimpleHome({
  guardResult,
  watchOn,
  watchError,
  hasCheckpoint,
  onRetryWatch,
  onShowAdvanced,
  onNavigateBackups,
  onOpenGuardDetails,
}: SimpleHomeProps) {
  const safety = guardSafetyCopy(guardResult, watchOn);
  const nextAction = guardNextActionCopy(guardResult, watchOn);
  return (
    <section style={{ display: "grid", gap: 10 }}>
      <SafetyAutomationNotice rawError={watchError} onRetry={onRetryWatch} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
        <HomeStatusBlock title="프로젝트 안전 상태" accent={safety.accent}>
          <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1.35 }}>{safety.title}</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", lineHeight: 1.55 }}>{safety.detail}</div>
          {guardResult ? (
            <button className="btn btn-ghost btn-sm" type="button" onClick={onOpenGuardDetails} style={{ marginTop: 12, fontSize: 11 }}>
              문제 확인하기
            </button>
          ) : null}
        </HomeStatusBlock>

        <HomeStatusBlock title="지금 할 일" accent={nextAction.accent}>
          <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1.35 }}>{nextAction.title}</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", lineHeight: 1.55 }}>{nextAction.detail}</div>
          {nextAction.needsAction ? (
            <button className="btn btn-black btn-sm" type="button" onClick={onOpenGuardDetails} style={{ marginTop: 12, fontSize: 11 }}>
              확인하기
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
          <button className="btn btn-ghost btn-sm" type="button" onClick={onNavigateBackups} style={{ marginTop: 12, fontSize: 11 }}>
            이전 상태로 돌아가기
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

interface HomeStatusBlockProps {
  readonly title: string;
  readonly accent: string;
  readonly children: ReactNode;
}

function HomeStatusBlock({ title, accent, children }: HomeStatusBlockProps) {
  return (
    <section style={{ background: "#FFFCF2", border: "2px solid #1A1A1A", padding: 16, minHeight: 170 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{ width: 10, height: 10, background: accent, border: "2px solid #1A1A1A", flexShrink: 0 }} />
        <h2 style={{ margin: 0, fontSize: 13, fontWeight: 900 }}>{title}</h2>
      </div>
      {children}
    </section>
  );
}
