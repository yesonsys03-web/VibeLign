import type { OnboardingSnapshot } from "../../lib/vib";

interface OnboardingAdvancedPanelProps {
  readonly vibFound: string | null;
  readonly vibChecking: boolean;
  readonly gitInstalled: boolean | null;
  readonly xcodeCltInstalled: boolean | null;
  readonly onboardingSnapshot: OnboardingSnapshot | null;
  readonly recentDirs: readonly string[];
  readonly onResume?: (dir: string) => void;
  readonly onRemoveRecent?: (dir: string) => void;
}

export function OnboardingAdvancedPanel({
  vibFound,
  vibChecking,
  gitInstalled,
  xcodeCltInstalled,
  onboardingSnapshot,
  recentDirs,
  onResume,
  onRemoveRecent,
}: OnboardingAdvancedPanelProps) {
  return (
    <section style={{ marginTop: 18, border: "2px solid #1A1A1A", background: "#fff", padding: 14 }}>
      <h2 style={{ fontSize: 13, margin: "0 0 10px", fontWeight: 900 }}>시스템 상태</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <span className="badge" style={{ fontSize: 10 }}>
          VIB CLI: {vibChecking ? "확인 중" : vibFound ? "발견됨" : "미설치"}
        </span>
        <span className="badge" style={{ fontSize: 10 }}>
          Git: {gitInstalled === null ? "확인 중" : gitInstalled ? "준비됨" : "필요"}
        </span>
        <span className="badge" style={{ fontSize: 10 }}>
          Xcode CLT: {xcodeCltInstalled === null ? "확인 중" : xcodeCltInstalled ? "준비됨" : "확인 필요"}
        </span>
        {onboardingSnapshot && (
          <span className="badge" style={{ fontSize: 10 }}>
            Claude Code: {onboardingSnapshot.state === "success" ? "준비됨" : "확인 필요"}
          </span>
        )}
      </div>

      {recentDirs.length > 0 && onResume && (
        <div>
          <h3 style={{ fontSize: 12, margin: "0 0 8px", fontWeight: 900 }}>최근 프로젝트</h3>
          <div style={{ display: "grid", gap: 6 }}>
            {recentDirs.map((dir) => (
              <div key={dir} style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #DDD", padding: "6px 8px" }}>
                <button type="button" onClick={() => onResume(dir)} style={{ border: "none", background: "transparent", fontWeight: 800, cursor: "pointer", textAlign: "left", flex: 1 }}>
                  {dir}
                </button>
                {onRemoveRecent && (
                  <button
                    type="button"
                    aria-label={`${dir} 최근 프로젝트 목록에서 제거`}
                    onClick={() => onRemoveRecent(dir)}
                    style={{ border: "1px solid #999", background: "#fff", cursor: "pointer" }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
