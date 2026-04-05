// === ANCHOR: HOME_START ===
import { useState } from "react";
import { GuardResult } from "../lib/vib";
import { COMMANDS, GuideStep } from "../lib/commands";
import UndoCard from "../components/cards/backup/UndoCard";
import HistoryCard from "../components/cards/backup/HistoryCard";
import CheckpointCard from "../components/cards/backup/CheckpointCard";
import CodemapCard from "../components/cards/analysis/CodemapCard";
import GuardCard from "../components/cards/analysis/GuardCard";
import AnchorCard from "../components/cards/analysis/AnchorCard";
import PatchCard from "../components/cards/ai/PatchCard";
import ExplainCard from "../components/cards/ai/ExplainCard";
import AskCard from "../components/cards/ai/AskCard";
import TransferCard from "../components/cards/transfer/TransferCard";
import ExportCard from "../components/cards/transfer/ExportCard";
import ProtectCard from "../components/cards/security/ProtectCard";
import SecretsCard from "../components/cards/security/SecretsCard";
import pkg from "../../package.json";

type View = "home" | "manual_list" | "manual_detail";

interface HomeProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onNavigate: (page: "checkpoints") => void;
  onOpenSettings?: (reason?: string) => void;
  initialView?: View;
  watchOn?: boolean;
  setWatchOn?: (v: boolean) => void;
  mapMode?: "manual" | "auto";
  setMapMode?: (v: "manual" | "auto") => void;
}


// ── 컴포넌트 ──────────────────────────────────────────────────────────────────
export default function Home({ projectDir, apiKey, providerKeys, hasAnyAiKey = false, aiKeyStatusLoaded = false, onNavigate, onOpenSettings, initialView = "home", watchOn: watchOnProp, setWatchOn: setWatchOnProp, mapMode: mapModeProp, setMapMode: setMapModeProp }: HomeProps) {
  const [view, setView]                   = useState<View>(initialView);
  const [selectedCmd, setSelectedCmd]     = useState<typeof COMMANDS[0] | null>(null);
  const [guardResult, setGuardResult]     = useState<GuardResult | null>(null);
  const [guardModal, setGuardModal] = useState(false);
  const [watchOnLocal, setWatchOnLocal]   = useState(watchOnProp ?? false);
  const watchOn = watchOnProp ?? watchOnLocal;
  const setWatchOn = (v: boolean) => { setWatchOnLocal(v); setWatchOnProp?.(v); };
  const [mapModeLocal, setMapModeLocal]   = useState<"manual"|"auto">(mapModeProp ?? "manual");
  const mapMode = mapModeProp ?? mapModeLocal;
  const setMapMode = (v: "manual"|"auto") => { setMapModeLocal(v); setMapModeProp?.(v); };



  function guardColor(status: string) {
    if (status === "pass") return "#4DFF91";
    if (status === "warn") return "#FFD166";
    return "#FF4D4D";
  }

  // ── 메뉴얼 커맨드 상세 뷰 ────────────────────────────────────────────────────
  if (view === "manual_detail" && selectedCmd) {
    const cmd = selectedCmd;
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div className="page-header" style={{ padding: "12px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setView("manual_list")} style={{ fontSize: 11 }}>← 목록</button>
            <div style={{ width: 32, height: 32, background: cmd.color, border: "2px solid #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>
              {cmd.icon}
            </div>
            <div>
              <div style={{ fontWeight: 900, fontSize: 14 }}>{cmd.title}</div>
              <div style={{ fontSize: 10, color: "#666" }}>vib {cmd.name}</div>
            </div>
          </div>
        </div>

        <div className="page-content">
          {/* 한 줄 설명 배지 */}
          <div style={{ background: cmd.color + "22", border: `2px solid ${cmd.color}`, padding: "10px 14px", marginBottom: 12, fontWeight: 700, fontSize: 12 }}>
            {cmd.short}
          </div>

          {/* 본문 설명 */}
          <div className="card" style={{ marginBottom: 12, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>어떤 기능이에요?</div>
            <div style={{ fontSize: 13, lineHeight: 1.8, color: "#1A1A1A" }}>{cmd.desc}</div>
          </div>

          {/* 사용법 */}
          <div className="terminal" style={{ marginBottom: 12 }}>
            <div className="terminal-header">
              <div className="terminal-dot red" />
              <div className="terminal-dot yellow" />
              <div className="terminal-dot green" />
            </div>
            <div style={{ marginTop: 4 }}>
              <span className="terminal-prompt">$ </span>
              <span style={{ color: "#FFD166", fontWeight: 700 }}>{cmd.usage}</span>
            </div>
          </div>

          {/* 가이드 or 팁 */}
          {"guide" in cmd && Array.isArray((cmd as any).guide) ? (
            <div>
              {((cmd as any).guide as GuideStep[]).map((gs, gi) => (
                <div key={gi} className="card" style={{ marginBottom: 8, padding: "12px 14px" }}>
                  {/* 스텝 헤더 */}
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: gs.subtitle ? 2 : 8 }}>
                    <span style={{
                      fontSize: 9, fontWeight: 900, padding: "2px 6px",
                      background: gs.optional ? "#444" : cmd.color,
                      color: gs.optional ? "#aaa" : "#1A1A1A",
                      border: "1.5px solid #1A1A1A", flexShrink: 0,
                    }}>{gs.step}</span>
                    <span style={{ fontWeight: 800, fontSize: 12 }}>{gs.title}</span>
                  </div>
                  {gs.subtitle && (
                    <div style={{ fontSize: 10, color: "#888", marginBottom: 8, marginLeft: 2 }}>{gs.subtitle}</div>
                  )}
                  {/* 라인들 */}
                  {gs.lines.map((ln, li) => {
                    if (ln.t === "code") return (
                      <div key={li} style={{
                        fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 700,
                        background: "#1A1A1A", color: "#4DFF91", padding: "5px 10px",
                        marginBottom: 4, overflowX: "auto", whiteSpace: "nowrap",
                      }}>{ln.v}</div>
                    );
                    if (ln.t === "label") return (
                      <div key={li} style={{ fontSize: 10, fontWeight: 800, color: "#888", marginTop: 6, marginBottom: 2 }}>{ln.v}</div>
                    );
                    if (ln.t === "error") return (
                      <div key={li} style={{
                        fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 700,
                        color: "#FF4D4D", marginTop: 8, marginBottom: 2,
                      }}>{ln.v}</div>
                    );
                    return (
                      <div key={li} style={{ fontSize: 11, color: "#444", lineHeight: 1.6, marginBottom: 2 }}>{ln.v}</div>
                    );
                  })}
                  {/* 경고 */}
                  {gs.warn && (
                    <div style={{
                      marginTop: 8, fontSize: 10, fontWeight: 700, color: "#FFD166",
                      background: "#FFD16618", border: "1.5px solid #FFD16666",
                      padding: "5px 10px",
                    }}>⚠ {gs.warn}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="card" style={{ padding: "14px 16px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>💡 이렇게 써요</div>
              {cmd.tips.map((tip, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 12, lineHeight: 1.6 }}>
                  <span style={{ color: cmd.color, fontWeight: 900, flexShrink: 0 }}>▸</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── 메뉴얼 커맨드 목록 뷰 ────────────────────────────────────────────────────
  if (view === "manual_list") {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div className="page-header" style={{ padding: "12px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setView("home")} style={{ fontSize: 11 }}>← 홈</button>
            <span className="page-title">MANUAL</span>
          </div>
          <div style={{ fontSize: 11, color: "#666", fontWeight: 600 }}>커맨드 {COMMANDS.length}개</div>
        </div>

        <div className="page-content">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            {COMMANDS.map((cmd) => (
              <div
                key={cmd.name}
                className="feature-card"
                style={{ cursor: "pointer" }}
                onClick={() => { setSelectedCmd(cmd); setView("manual_detail"); }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-2px)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "")}
              >
                <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
                  <div className="feature-card-icon"
                    style={{ background: cmd.color, color: "#fff", borderColor: cmd.color, width: 26, height: 26, fontSize: 13, fontWeight: 900 }}>
                    {cmd.icon}
                  </div>
                  <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                    <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{cmd.title}</span>
                    <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{cmd.short}</span>
                  </div>
                </div>
                <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
                  <div style={{ fontSize: 15, color: "#555", lineHeight: 1.5 }}>{cmd.short}</div>
                  <div style={{ marginTop: 4, fontSize: 13.5, fontFamily: "IBM Plex Mono, monospace", color: cmd.color, fontWeight: 700 }}>
                    vib {cmd.name}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── 홈 메인 뷰 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* ── Guard 결과 모달 ── */}
      {guardModal && guardResult && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setGuardModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 560, maxHeight: "80vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 모달 헤더 */}
            <div style={{ background: "#1A1A1A", padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 14, color: "#fff", letterSpacing: 2 }}>GUARD 결과</span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", background: guardColor(guardResult.status), color: "#1A1A1A", border: "1px solid #555" }}>
                  {guardResult.status.toUpperCase()}
                </span>
              </div>
              <button onClick={() => setGuardModal(false)} style={{ background: "transparent", border: "1px solid #555", color: "#aaa", cursor: "pointer", padding: "2px 8px", fontSize: 14, fontWeight: 700 }}>✕</button>
            </div>

            {/* 모달 본문 */}
            <div style={{ overflowY: "auto", padding: "20px" }}>
              {/* 요약 */}
              <div style={{ fontSize: 14, color: "#1A1A1A", lineHeight: 1.7, marginBottom: 20, padding: "14px 16px", background: "#fff", border: "2px solid #1A1A1A" }}>
                {guardResult.summary}
              </div>

              {/* 권장 액션 */}
              {guardResult.recommendations.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 11, letterSpacing: 1, marginBottom: 10, textTransform: "uppercase" }}>권장 액션</div>
                  {guardResult.recommendations.map((r, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, marginBottom: 8, padding: "10px 14px", background: "#fff", border: "2px solid #1A1A1A", fontSize: 13, lineHeight: 1.5 }}>
                      <span style={{ color: "#FF4D8B", fontWeight: 900, flexShrink: 0 }}>▸</span>
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* 전체 이슈 */}
              {guardResult.issues.length > 0 && (
                <div>
                  <div style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 11, letterSpacing: 1, marginBottom: 10, textTransform: "uppercase" }}>
                    전체 이슈 ({guardResult.issues.length}개)
                  </div>
                  {guardResult.issues.map((issue, i) => (
                    <div key={i} style={{ marginBottom: 8, padding: "10px 14px", background: "#fff", border: "2px solid #E8E4D8" }}>
                      <div style={{ fontSize: 12, color: "#333", marginBottom: 6, lineHeight: 1.5 }}>{issue.found}</div>
                      <div style={{ fontSize: 12, color: "#F5621E", fontWeight: 700, fontFamily: "IBM Plex Mono, monospace" }}>→ {issue.next_step}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 모달 푸터 */}
            <div style={{ padding: "12px 20px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setGuardModal(false)}>닫기</button>
              <button className="btn btn-sm" style={{ background: "#FF4D8B" }} onClick={() => setGuardModal(false)}>닫고 다시 실행</button>
            </div>
          </div>
        </div>
      )}
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">HOME</span>
        <div
          className="terminal"
          style={{
            padding: "6px 10px",
            fontSize: 10,
            fontWeight: 700,
            lineHeight: 1.4,
            flexShrink: 0,
          }}
          title="VibeLign GUI 버전"
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
            <div className="terminal-header" style={{ marginBottom: 0 }}>
              <div className="terminal-dot red" />
              <div className="terminal-dot yellow" />
              <div className="terminal-dot green" />
            </div>
            <span style={{ color: "#b8b4b0" }}>바이브라인</span>
            <span style={{ color: "#F5621E" }}>v{pkg.version}</span>
          </div>
        </div>
      </div>


      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>

          {/* ── 코드맵 생성 ── */}
          <CodemapCard
            projectDir={projectDir}
            watchOn={watchOn}
            setWatchOn={setWatchOn}
            mapMode={mapMode}
            setMapMode={setMapMode}
          />

          {/* ── AI 폭주 방지 ── */}
          <GuardCard
            projectDir={projectDir}
            onGuardResult={(r) => { setGuardResult(r); setGuardModal(true); }}
          />

          {/* ── 체크포인트 ── */}
          <CheckpointCard projectDir={projectDir} onNavigate={onNavigate} />

          {/* ── AI 이동 자유 ── */}
          <TransferCard projectDir={projectDir} />

          {/* ── 히스토리 + 패치 (한 행: 히스토리 왼쪽, 패치 오른쪽) ── */}
          <div
            style={{
              gridColumn: "1 / -1",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
            }}
          >
            <HistoryCard projectDir={projectDir} />
            <PatchCard
              projectDir={projectDir}
              apiKey={apiKey}
              providerKeys={providerKeys}
              hasAnyAiKey={hasAnyAiKey}
              aiKeyStatusLoaded={aiKeyStatusLoaded}
              onOpenSettings={onOpenSettings}
            />
          </div>

        </div>

        {/* ── 커맨드 섹션 ── */}
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#888", letterSpacing: "0.08em", marginBottom: 6, paddingLeft: 2 }}>
            커맨드
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            <UndoCard projectDir={projectDir} onNavigate={onNavigate} />
            <AnchorCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
            <ExplainCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
            <AskCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
            <ExportCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
            <ProtectCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
            <SecretsCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
          </div>
        </div>

      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
