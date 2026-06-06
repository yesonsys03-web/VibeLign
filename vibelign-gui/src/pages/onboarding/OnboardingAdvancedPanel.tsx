// === ANCHOR: ONBOARDINGADVANCEDPANEL_START ===
import { useState } from "react";
import type { OnboardingSnapshot } from "../../lib/vib";

const RECENT_PAGE_SIZE = 5;

interface OnboardingAdvancedPanelProps {
  readonly vibFound: string | null;
  readonly vibChecking: boolean;
  readonly gitInstalled: boolean | null;
  readonly xcodeCltInstalled: boolean | null;
  readonly claudeInstalled: boolean | null;
  readonly onboardingSnapshot: OnboardingSnapshot | null;
  readonly recentDirs: readonly string[];
  readonly onResume?: (dir: string) => void;
  readonly onRemoveRecent?: (dir: string) => void;
}

// === ANCHOR: ONBOARDINGADVANCEDPANEL_ONBOARDINGADVANCEDPANEL_START ===
export function OnboardingAdvancedPanel({
  vibFound,
  vibChecking,
  gitInstalled,
  xcodeCltInstalled,
  claudeInstalled,
  onboardingSnapshot,
  recentDirs,
  onResume,
  onRemoveRecent,
}: OnboardingAdvancedPanelProps) {
  const [recentPage, setRecentPage] = useState(0);
  // 실제 진단값 기반 Claude Code 상태: PATH 탐지 / 온보딩 검증(success) / 진단 플래그 중
  // 하나라도 설치를 가리키면 "준비됨". 아직 탐지 전이면 "확인 중", 확실히 없으면 "미설치".
  const claudeReady =
    claudeInstalled === true ||
    onboardingSnapshot?.state === "success" ||
    onboardingSnapshot?.diagnostics.claudeOnPath === true ||
    onboardingSnapshot?.diagnostics.claudeVersionOk === true;
  const claudeCodeLabel = claudeReady ? "준비됨" : claudeInstalled === null ? "확인 중" : "미설치";
  const totalPages = Math.max(1, Math.ceil(recentDirs.length / RECENT_PAGE_SIZE));
  const currentPage = Math.min(recentPage, totalPages - 1);
  const pageStart = currentPage * RECENT_PAGE_SIZE;
  const visibleDirs = recentDirs.slice(pageStart, pageStart + RECENT_PAGE_SIZE);

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
        <span className="badge" style={{ fontSize: 10 }}>
          Claude Code: {claudeCodeLabel}
        </span>
      </div>

      {recentDirs.length > 0 && onResume && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "0 0 8px", gap: 8 }}>
            <h3 style={{ fontSize: 12, margin: 0, fontWeight: 900 }}>최근 프로젝트</h3>
            {totalPages > 1 && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, fontWeight: 800 }}>
                <button
                  type="button"
                  aria-label="이전 페이지"
                  onClick={() => setRecentPage(Math.max(0, currentPage - 1))}
                  disabled={currentPage === 0}
                  style={{ border: "1px solid #999", background: "#fff", cursor: currentPage === 0 ? "default" : "pointer", opacity: currentPage === 0 ? 0.4 : 1, padding: "2px 8px" }}
                >
                  ‹ 이전
                </button>
                <span aria-label={`${currentPage + 1} / ${totalPages} 페이지`}>
                  {currentPage + 1}/{totalPages}
                </span>
                <button
                  type="button"
                  aria-label="다음 페이지"
                  onClick={() => setRecentPage(Math.min(totalPages - 1, currentPage + 1))}
                  disabled={currentPage >= totalPages - 1}
                  style={{ border: "1px solid #999", background: "#fff", cursor: currentPage >= totalPages - 1 ? "default" : "pointer", opacity: currentPage >= totalPages - 1 ? 0.4 : 1, padding: "2px 8px" }}
                >
                  다음 ›
                </button>
              </div>
            )}
          </div>
          <div style={{ display: "grid", gap: 6 }}>
            {visibleDirs.map((dir) => (
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
// === ANCHOR: ONBOARDINGADVANCEDPANEL_ONBOARDINGADVANCEDPANEL_END ===
// === ANCHOR: ONBOARDINGADVANCEDPANEL_END ===
