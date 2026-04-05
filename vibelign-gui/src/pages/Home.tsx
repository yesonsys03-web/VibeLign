// === ANCHOR: HOME_START ===
import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { vibGuard, vibScan, vibTransfer, startWatch, stopWatch, watchStatus, checkpointCreate, runVib, pickFile, GuardResult, buildGuiAiEnv } from "../lib/vib";
import { COMMANDS, PATCH_COMMAND, CardState, FlagDef, GuideStep, buildCmdArgs } from "../lib/commands";
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


/** CLI stdout/stderr와 동일한 본문을 그대로 보여 주는 터미널 스타일 블록 (줄바꿈·공백 유지). */
function GuiCliOutputBlock({
  text,
  placeholder,
  variant = "default",
}: {
  text: string;
  placeholder: string;
  variant?: "default" | "error" | "warn";
}) {
  const [folded, setFolded] = useState(false);
  const trimmed = text.trim();

  useEffect(() => {
    setFolded(false);
  }, [text]);

  if (!trimmed) {
    if (!placeholder) return null;
    return (
      <div style={{ fontSize: 15, color: "#555", marginBottom: 6, lineHeight: 1.35 }}>
        {placeholder}
      </div>
    );
  }
  const color = variant === "error" ? "#FF4D4D" : variant === "warn" ? "#A05A00" : "#1A1A1A";
  return (
    <div style={{ margin: "0 0 8px 0" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setFolded((f) => !f)}
          style={{ fontSize: 9, fontWeight: 700, padding: "2px 10px", border: "2px solid #1A1A1A", cursor: "pointer" }}
        >
          {folded ? "펼치기" : "접기"}
        </button>
      </div>
      {!folded && (
        <pre
          style={{
            margin: 0,
            padding: "8px 10px",
            maxHeight: 280,
            overflowY: "auto",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 10,
            lineHeight: 1.45,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "#fff",
            border: "2px solid #1A1A1A",
            color,
            boxSizing: "border-box",
          }}
        >
          {text}
        </pre>
      )}
      {folded && (
        <div style={{ fontSize: 10, color: "#888", fontWeight: 600, padding: "4px 2px 0" }}>결과가 접혀 있어요.</div>
      )}
    </div>
  );
}

// ── 컴포넌트 ──────────────────────────────────────────────────────────────────
export default function Home({ projectDir, apiKey, providerKeys, hasAnyAiKey = false, aiKeyStatusLoaded = false, onNavigate, onOpenSettings, initialView = "home", watchOn: watchOnProp, setWatchOn: setWatchOnProp, mapMode: mapModeProp, setMapMode: setMapModeProp }: HomeProps) {
  const [view, setView]                   = useState<View>(initialView);
  const [selectedCmd, setSelectedCmd]     = useState<typeof COMMANDS[0] | null>(null);
  const [guardState, setGuardState]       = useState<CardState>("idle");
  const [guardResult, setGuardResult]     = useState<GuardResult | null>(null);
  const [guardModal, setGuardModal] = useState(false);
  const [scanState, setScanState]         = useState<CardState>("idle");
  const [watchOnLocal, setWatchOnLocal]   = useState(watchOnProp ?? false);
  const watchOn = watchOnProp ?? watchOnLocal;
  const setWatchOn = (v: boolean) => { setWatchOnLocal(v); setWatchOnProp?.(v); };
  const [watchLoading, setWatchLoading]   = useState(false);
  const [watchLogs, setWatchLogs]         = useState<string[]>([]);
  const watchLogRef                       = useRef<HTMLDivElement>(null);
  const [mapModeLocal, setMapModeLocal]   = useState<"manual"|"auto">(mapModeProp ?? "manual");
  const mapMode = mapModeProp ?? mapModeLocal;
  const setMapMode = (v: "manual"|"auto") => { setMapModeLocal(v); setMapModeProp?.(v); };
  const [transferState, setTransferState] = useState<CardState>("idle");
  const [cpMsg, setCpMsg]                 = useState("");
  const [cpState, setCpState]             = useState<CardState>("idle");
  const [error, setError]                 = useState<string | null>(null);
  const [cmdStates, setCmdStates]         = useState<Record<string, CardState>>({});
  const [cmdOutputs, setCmdOutputs]       = useState<Record<string, string>>({});
  const [cmdHasWarnings, setCmdHasWarnings] = useState<Record<string, boolean>>({});
  const [cmdFlagValues, setCmdFlagValues]     = useState<Record<string, Record<string, string | boolean>>>({});
  const [guardStrict, setGuardStrict]         = useState(false);
  const [transferHandoff, setTransferHandoff] = useState(false);
  const [transferCompact, setTransferCompact] = useState(false);
  const [outputModal, setOutputModal]         = useState<{ name: string; content: string } | null>(null);
  const cmdIdleTimers = useRef<Record<string, number>>({});

  useEffect(() => {
    return () => {
      Object.values(cmdIdleTimers.current).forEach((timerId) => {
        window.clearTimeout(timerId);
      });
    };
  }, []);

  async function handleGuard() {
    setGuardState("loading"); setGuardResult(null); setError(null);
    try {
      const r = await vibGuard(projectDir, { strict: guardStrict });
      setGuardResult(r);
      setGuardModal(true);
      setGuardState("done");
    } catch (e) { setError(String(e)); setGuardState("error"); }
  }

  async function handleScan() {
    setScanState("loading"); setError(null);
    try {
      const r = await vibScan(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setScanState("done");
    } catch (e) { setError(String(e)); setScanState("error"); }
  }

  useEffect(() => {
    watchStatus().then((running) => {
      if (running !== watchOn) setWatchOn(running);
    }).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const unlisten = listen<string>("watch_log", (e) => {
      setWatchLogs((prev) => {
        const next = [...prev, e.payload].slice(-200);
        return next;
      });
      setTimeout(() => {
        if (watchLogRef.current) watchLogRef.current.scrollTop = watchLogRef.current.scrollHeight;
      }, 0);
    });
    return () => { unlisten.then((f) => f()); };
  }, []);

  async function handleToggleWatch() {
    setWatchLoading(true); setError(null);
    try {
      if (watchOn) { await stopWatch(); setWatchOn(false); }
      else { setWatchLogs([]); await startWatch(projectDir); setWatchOn(true); }
    } catch (e) { setError(String(e)); }
    finally { setWatchLoading(false); }
  }

  async function handleCheckpoint() {
    if (!cpMsg.trim()) return;
    setCpState("loading"); setError(null);
    try {
      await checkpointCreate(projectDir, cpMsg.trim());
      setCpMsg(""); setCpState("done");
      setTimeout(() => setCpState("idle"), 2000);
    } catch (e) { setError(String(e)); setCpState("error"); }
  }

  async function handleTransfer() {
    setTransferState("loading"); setError(null);
    try {
      const r = await vibTransfer(projectDir, { handoff: transferHandoff, compact: transferCompact });
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setTransferState("done");
    } catch (e) { setError(String(e)); setTransferState("error"); }
  }

  async function handleRunCmd(name: string) {
    if (name === "undo") { onNavigate("checkpoints"); return; }
    const args = buildCmdArgs(name, cmdFlagValues);
    if (!args) {
      setCmdStates(s => ({ ...s, [name]: "error" }));
      setCmdOutputs(o => ({ ...o, [name]: "필수 항목을 입력해주세요" }));
      return;
    }
    if (args.includes("--ai") && aiKeyStatusLoaded && !hasAnyAiKey) {
      setCmdStates(s => ({ ...s, [name]: "error" }));
      setCmdOutputs(o => ({ ...o, [name]: "API 키를 먼저 설정해주세요" }));
      if (onOpenSettings) {
        onOpenSettings("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      } else {
        setError("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      }
      return;
    }
    setCmdStates(s => ({ ...s, [name]: "loading" }));
    setCmdOutputs(o => ({ ...o, [name]: "" }));
    const existingTimer = cmdIdleTimers.current[name];
    if (existingTimer !== undefined) {
      window.clearTimeout(existingTimer);
      delete cmdIdleTimers.current[name];
    }
    try {
      const env = args.includes("--ai") ? buildGuiAiEnv(providerKeys, apiKey) : undefined;
      const r = await runVib(args, projectDir, env);
      setCmdStates(s => ({ ...s, [name]: r.ok ? "done" : "error" }));
      const stdoutContent = r.stdout.trim();
      const stderrContent = r.stderr.trim();
      const combinedOutput = [stderrContent, stdoutContent].filter(Boolean).join("\n\n");
      const output = combinedOutput || (r.ok ? "완료" : `exit ${r.exit_code}`);
      setCmdOutputs(o => ({ ...o, [name]: output }));
      const hasWarning = Boolean(stderrContent);
      setCmdHasWarnings(w => ({ ...w, [name]: hasWarning }));
      if (!r.ok || hasWarning) {
        setOutputModal({ name, content: output });
      }
      if (r.ok && !hasWarning) {
        cmdIdleTimers.current[name] = window.setTimeout(() => {
          setCmdStates(s => ({ ...s, [name]: "idle" }));
          delete cmdIdleTimers.current[name];
        }, 3000);
      }
    } catch (e) {
      setCmdStates(s => ({ ...s, [name]: "error" }));
      setCmdOutputs(o => ({ ...o, [name]: String(e) }));
      setCmdHasWarnings(w => ({ ...w, [name]: false }));
    }
  }

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
              <button className="btn btn-sm" style={{ background: "#FF4D8B" }} onClick={() => { setGuardModal(false); handleGuard(); }}>다시 실행</button>
            </div>
          </div>
        </div>
      )}
      {/* ── 커맨드 결과 모달 ── */}
      {outputModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setOutputModal(null)}>
          <div style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 560, maxHeight: "80vh", display: "flex", flexDirection: "column" }}
            onClick={e => e.stopPropagation()}>
            <div style={{ background: "#1A1A1A", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 13, color: "#fff", letterSpacing: 2 }}>{outputModal.name.toUpperCase()} 결과</span>
              <button onClick={() => setOutputModal(null)} style={{ background: "transparent", border: "1px solid #555", color: "#aaa", cursor: "pointer", padding: "2px 8px", fontSize: 14, fontWeight: 700 }}>✕</button>
            </div>
            <div style={{ overflowY: "auto", padding: "16px 20px" }}>
              <pre style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.7, color: "#1A1A1A", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>{outputModal.content}</pre>
            </div>
            <div style={{ padding: "10px 20px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setOutputModal(null)}>닫기</button>
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

      {error && <div className="alert alert-error" style={{ margin: "0 20px 8px" }}>{error}</div>}

      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>

          {/* ── 코드맵 생성 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#F5621E18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#F5621E", color: "#fff", borderColor: "#F5621E", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>MAP</div>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>코드맵</span>
                <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
                  복잡한 코드가 서로 어떻게 연결되어 있는지 한눈에 보여주는 지도
                </span>
              </div>
              {watchOn && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>감시 중</span>}
              {mapMode === "manual" && scanState === "done" && !watchOn && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
                {(["manual", "auto"] as const).map((m) => (
                  <button key={m} onClick={() => setMapMode(m)} style={{
                    flex: 1, fontSize: 10, fontWeight: 700, padding: "3px 0",
                    border: "2px solid #1A1A1A",
                    background: mapMode === m ? "#1A1A1A" : "#fff",
                    color: mapMode === m ? "#fff" : "#1A1A1A", cursor: "pointer",
                  }}>{m === "manual" ? "수동" : "자동"}</button>
                ))}
              </div>
              {mapMode === "manual" ? (
                <button className="btn btn-sm" style={{ width: "100%", background: "#F5621E", color: "#fff", border: "2px solid #1A1A1A" }}
                  disabled={scanState === "loading"} onClick={handleScan}>
                  {scanState === "loading" ? <span className="spinner" /> : "SCAN ▶"}
                </button>
              ) : (
                <>
                  <button className="btn btn-sm" style={{ width: "100%", border: "2px solid #1A1A1A", background: watchOn ? "#FF4D4D" : "#F5621E", color: "#fff" }}
                    disabled={watchLoading} onClick={handleToggleWatch}>
                    {watchLoading ? <span className="spinner" /> : watchOn ? "STOP ■" : "WATCH ▶"}
                  </button>
                  {watchOn && (
                    <div ref={watchLogRef} style={{
                      marginTop: 6, height: 80, overflowY: "auto", background: "#0D0D0D",
                      border: "1px solid #333", padding: "4px 6px", fontFamily: "monospace",
                      fontSize: 9, color: "#4DFF91", lineHeight: 1.5,
                    }}>
                      {watchLogs.length === 0
                        ? <span style={{ color: "#666" }}>감시 중… 로그 대기</span>
                        : watchLogs.map((l, i) => <div key={i}>{l}</div>)
                      }
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* ── AI 폭주 방지 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#FF4D8B18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#FF4D8B", color: "#fff", borderColor: "#FF4D8B", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>♥</div>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>AI 방지</span>
                <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
                  AI가 코드를 이상하게 바꿨는지, 몸 검진하듯 살펴봐요
                </span>
              </div>
              {guardState === "done" && guardResult && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: guardColor(guardResult.status), color: "#1A1A1A", border: "1px solid #1A1A1A" }}>
                  {guardResult.status.toUpperCase()}
                </span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 16.5, color: "#555", marginBottom: 8 }}>
                {guardResult ? guardResult.summary.slice(0, 60) + "…" : "프로젝트 상태 점검"}
              </div>
              <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
                <button onClick={() => setGuardStrict(s => !s)} style={{
                  fontSize: 9, fontWeight: 700, padding: "2px 8px",
                  border: "2px solid #1A1A1A",
                  background: guardStrict ? "#1A1A1A" : "#fff",
                  color: guardStrict ? "#fff" : "#1A1A1A", cursor: "pointer",
                }}>--strict</button>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn btn-sm" style={{ flex: 1, background: "#FF4D8B", color: "#fff", border: "2px solid #1A1A1A" }}
                  disabled={guardState === "loading"} onClick={handleGuard}>
                  {guardState === "loading" ? <span className="spinner" /> : "GUARD ▶"}
                </button>
                {guardResult && (
                  <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
                    onClick={() => setGuardModal(true)}>결과 보기</button>
                )}
              </div>
              {guardState === "error" && error && (
                <div className="alert alert-error" style={{ marginTop: 6, fontSize: 10 }}>{error}</div>
              )}
            </div>
          </div>

          {/* ── 체크포인트 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>💾</div>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>체크포인트</span>
                <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
                  지금 코드 모습을 저장해 두면 나중에 그때로 되돌릴 수 있어요 (게임 세이브 같아요)
                </span>
              </div>
              {cpState === "done" && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>저장됨</span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <input
                className="input-field"
                value={cpMsg}
                onChange={(e) => setCpMsg(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCheckpoint()}
                placeholder="메시지 입력..."
                style={{ width: "100%", marginBottom: 6, fontSize: 11, padding: "4px 8px", boxSizing: "border-box" }}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
                  disabled={cpState === "loading" || !cpMsg.trim()} onClick={handleCheckpoint}>
                  {cpState === "loading" ? <span className="spinner" /> : "저장 ▶"}
                </button>
                <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
                  onClick={() => onNavigate("checkpoints")}>목록</button>
              </div>
            </div>
          </div>

          {/* ── AI 이동 자유 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#4D9FFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#4D9FFF", color: "#fff", borderColor: "#4D9FFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>⇄</div>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>AI 이동</span>
                <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
                  다른 AI 앱으로 넘어갈 때, 지금까지 한 일을 한 장 요약으로 만들어 줘요
                </span>
              </div>
              {transferState === "done" && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 16.5, color: "#555", marginBottom: 8 }}>PROJECT_CONTEXT 생성</div>
              <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
                <button onClick={() => setTransferHandoff(s => !s)} style={{
                  flex: 1, fontSize: 9, fontWeight: 700, padding: "2px 0",
                  border: "2px solid #1A1A1A",
                  background: transferHandoff ? "#1A1A1A" : "#fff",
                  color: transferHandoff ? "#fff" : "#1A1A1A", cursor: "pointer",
                }}>--handoff</button>
                <button onClick={() => setTransferCompact(s => !s)} style={{
                  flex: 1, fontSize: 9, fontWeight: 700, padding: "2px 0",
                  border: "2px solid #1A1A1A",
                  background: transferCompact ? "#1A1A1A" : "#fff",
                  color: transferCompact ? "#fff" : "#1A1A1A", cursor: "pointer",
                }}>--compact</button>
              </div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A" }}
                disabled={transferState === "loading"} onClick={handleTransfer}>
                {transferState === "loading" ? <span className="spinner" /> : "TRANSFER ▶"}
              </button>
            </div>
          </div>

          {/* ── 히스토리 + 패치 (한 행: 히스토리 왼쪽, 패치 오른쪽) ── */}
          <div
            style={{
              gridColumn: "1 / -1",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
            }}
          >
            <div className="feature-card" style={{ cursor: "default" }}>
              <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
                <div className="feature-card-icon"
                  style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 14, fontWeight: 900 }}>🕓</div>
                <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>히스토리</span>
                  <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
                    저장이 언제 찍혔는지 시간 순으로 보여 줘요
                  </span>
                </div>
                {(((cmdStates["history"] ?? "idle") === "done") || ((cmdStates["history"] ?? "idle") === "idle" && cmdOutputs["history"])) && !(cmdHasWarnings["history"] ?? false) && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
                )}
                {(cmdHasWarnings["history"] ?? false) && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>
                )}
                {(cmdStates["history"] ?? "idle") === "error" && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
                )}
              </div>
              <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
                <GuiCliOutputBlock
                  text={cmdOutputs["history"] ?? ""}
                  placeholder="체크포인트 변경 이력 보기"
                  variant={
                    (cmdStates["history"] ?? "idle") === "error"
                      ? "error"
                      : (cmdHasWarnings["history"] ?? false)
                        ? "warn"
                        : "default"
                  }
                />
                <div style={{ display: "flex", gap: 4 }}>
                  <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
                    disabled={(cmdStates["history"] ?? "idle") === "loading"} onClick={() => handleRunCmd("history")}>
                    {(cmdStates["history"] ?? "idle") === "loading" ? <span className="spinner" /> : "HISTORY ▶"}
                  </button>
                  {cmdOutputs["history"] && (
                    <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                      onClick={() => setOutputModal({ name: "history", content: cmdOutputs["history"] })}>결과</button>
                  )}
                </div>
              </div>
            </div>
            {(() => {
              const cmd = PATCH_COMMAND;
              const st = cmdStates[cmd.name] ?? "idle";
              const out = cmdOutputs[cmd.name] ?? "";
              const hasWarning = cmdHasWarnings[cmd.name] ?? false;
              return (
                <div className="feature-card" style={{ cursor: "default" }}>
                  <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
                    <div className="feature-card-icon" style={{
                      background: cmd.color, color: "#fff", borderColor: cmd.color,
                      width: 22, height: 22, fontSize: 11, fontWeight: 900,
                    }}>{cmd.icon}</div>
                    <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                      <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{cmd.title}</span>
                      <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{cmd.short}</span>
                    </div>
                    {(st === "done" || (st === "idle" && out)) && !hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
                    {hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>}
                    {st === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
                  </div>
                  <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
                    {!((cmd as any).flags as FlagDef[] | undefined)?.some((f: FlagDef) => f.type === "text" || f.type === "select") && (
                      <GuiCliOutputBlock
                        text={out}
                        placeholder={cmd.short}
                        variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
                      />
                    )}
                    {((cmd as any).flags as FlagDef[] | undefined)?.map((fd: FlagDef, fi: number) => {
                      const fvals = cmdFlagValues[cmd.name] ?? {};
                      const val: string | boolean = fvals[fd.key] ?? (fd.type === "bool" ? false : (fd.type === "select" && fd.options.length > 0 ? fd.options[0].v : ""));
                      if (fd.type === "bool") return (
                        <button key={fi} onClick={() => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: !val } }))} style={{
                          fontSize: 9, fontWeight: 700, padding: "2px 6px", marginRight: 4, marginBottom: 4,
                          border: "2px solid #1A1A1A",
                          background: val ? "#1A1A1A" : "#fff",
                          color: val ? "#fff" : "#1A1A1A", cursor: "pointer",
                        }}>{fd.label}</button>
                      );
                      if (fd.type === "text") return (
                        <div key={fi} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                          <input value={String(val)} onChange={e => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: e.target.value } }))} placeholder={(fd as any).placeholder} style={{
                            flex: 1, fontSize: 10, padding: "3px 6px",
                            border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                            fontFamily: "IBM Plex Mono, monospace", background: "#fff", minWidth: 0,
                          }} />
                          {fd.key === "_file" && (
                            <button onClick={async () => {
                              const picked = await pickFile(projectDir);
                              if (picked) {
                                const rel = picked.startsWith(projectDir + "/") ? picked.slice(projectDir.length + 1) : picked;
                                setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: rel } }));
                              }
                            }} style={{ padding: "2px 6px", border: "2px solid #1A1A1A", background: "#fff", cursor: "pointer", fontSize: 13, flexShrink: 0 }}>📁</button>
                          )}
                        </div>
                      );
                      if (fd.type === "select") return (
                        <select key={fi} value={String(val)} onChange={e => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: e.target.value } }))} style={{
                          width: "100%", fontSize: 10, padding: "3px 6px", marginBottom: 4,
                          border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                          fontFamily: "IBM Plex Mono, monospace", cursor: "pointer", background: "#fff",
                        }}>
                          {fd.options.map((o: { v: string; l: string }) => <option key={o.v} value={o.v}>{o.l}</option>)}
                        </select>
                      );
                      return null;
                    })}
                    {out && ((cmd as any).flags as FlagDef[] | undefined)?.some((f: FlagDef) => f.type === "text" || f.type === "select") && (
                      <GuiCliOutputBlock
                        text={out}
                        placeholder=""
                        variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
                      />
                    )}
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="btn btn-sm"
                        style={{ flex: 1, background: cmd.color, color: cmd.color === "#FFD166" || cmd.color === "#FFE44D" ? "#1A1A1A" : "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
                        disabled={st === "loading"}
                        onClick={() => handleRunCmd(cmd.name)}
                      >
                        {st === "loading" ? <span className="spinner" /> : `${cmd.name.toUpperCase()} ▶`}
                      </button>
                      {out && (
                        <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                          onClick={() => setOutputModal({ name: cmd.name, content: out })}>결과</button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>

        </div>

        {/* ── 커맨드 섹션 ── */}
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#888", letterSpacing: "0.08em", marginBottom: 6, paddingLeft: 2 }}>
            커맨드
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {((() => {
              const EXCLUDE = ["scan","watch","guard","checkpoint","transfer","history","patch","start","doctor","config","rules","install","manual","policy"];
              const toneRank = (color: string) => {
                if (color === "#FFE44D" || color === "#FFD166" || color === "#F5621E") return 0; // warm
                if (color === "#FF4D4D" || color === "#FF4D8B") return 1; // red/pink
                if (color === "#4D9FFF") return 2; // blue
                if (color === "#7B4DFF") return 3; // purple
                if (color === "#4DFF91") return 4; // green
                return 5;
              };
              return COMMANDS
                .filter(c => !EXCLUDE.includes(c.name))
                .sort((a, b) => toneRank(a.color) - toneRank(b.color) || a.title.localeCompare(b.title, "ko"));
            })()).map(cmd => {
              const st = cmdStates[cmd.name] ?? "idle";
              const out = cmdOutputs[cmd.name] ?? "";
              const hasWarning = cmdHasWarnings[cmd.name] ?? false;
              return (
                <div key={cmd.name} className="feature-card" style={{ cursor: "default" }}>
                  <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
                    <div className="feature-card-icon" style={{
                      background: cmd.color, color: "#fff", borderColor: cmd.color,
                      width: 22, height: 22, fontSize: 11, fontWeight: 900,
                    }}>{cmd.icon}</div>
                    <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                      <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{cmd.title}</span>
                      <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{cmd.short}</span>
                    </div>
                    {(st === "done" || (st === "idle" && out)) && !hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
                    {hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>}
                    {st === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
                  </div>
                  <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
                    {!((cmd as any).flags as FlagDef[] | undefined)?.some((f: FlagDef) => f.type === "text" || f.type === "select") && (
                      <GuiCliOutputBlock
                        text={out}
                        placeholder={cmd.short}
                        variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
                      />
                    )}
                    {((cmd as any).flags as FlagDef[] | undefined)?.map((fd: FlagDef, fi: number) => {
                      const fvals = cmdFlagValues[cmd.name] ?? {};
                      const val: string | boolean = fvals[fd.key] ?? (fd.type === "bool" ? false : (fd.type === "select" && fd.options.length > 0 ? fd.options[0].v : ""));
                      if (fd.type === "bool") return (
                        <button key={fi} onClick={() => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: !val } }))} style={{
                          fontSize: 9, fontWeight: 700, padding: "2px 6px", marginRight: 4, marginBottom: 4,
                          border: "2px solid #1A1A1A",
                          background: val ? "#1A1A1A" : "#fff",
                          color: val ? "#fff" : "#1A1A1A", cursor: "pointer",
                        }}>{fd.label}</button>
                      );
                      if (fd.type === "text") return (
                        <div key={fi} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                          <input value={String(val)} onChange={e => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: e.target.value } }))} placeholder={(fd as any).placeholder} style={{
                            flex: 1, fontSize: 10, padding: "3px 6px",
                            border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                            fontFamily: "IBM Plex Mono, monospace", background: "#fff", minWidth: 0,
                          }} />
                          {fd.key === "_file" && (
                            <button onClick={async () => {
                              const picked = await pickFile(projectDir);
                              if (picked) {
                                const rel = picked.startsWith(projectDir + "/") ? picked.slice(projectDir.length + 1) : picked;
                                setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: rel } }));
                              }
                            }} style={{ padding: "2px 6px", border: "2px solid #1A1A1A", background: "#fff", cursor: "pointer", fontSize: 13, flexShrink: 0 }}>📁</button>
                          )}
                        </div>
                      );
                      if (fd.type === "select") return (
                        <select key={fi} value={String(val)} onChange={e => setCmdFlagValues(m => ({ ...m, [cmd.name]: { ...(m[cmd.name] ?? {}), [fd.key]: e.target.value } }))} style={{
                          width: "100%", fontSize: 10, padding: "3px 6px", marginBottom: 4,
                          border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                          fontFamily: "IBM Plex Mono, monospace", cursor: "pointer", background: "#fff",
                        }}>
                          {fd.options.map((o: { v: string; l: string }) => <option key={o.v} value={o.v}>{o.l}</option>)}
                        </select>
                      );
                      return null;
                    })}
                    {out && ((cmd as any).flags as FlagDef[] | undefined)?.some((f: FlagDef) => f.type === "text" || f.type === "select") && (
                      <GuiCliOutputBlock
                        text={out}
                        placeholder=""
                        variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
                      />
                    )}
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="btn btn-sm"
                        style={{ flex: 1, background: cmd.color, color: cmd.color === "#FFD166" || cmd.color === "#FFE44D" ? "#1A1A1A" : "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
                        disabled={st === "loading"}
                        onClick={() => cmd.name === "manual" ? setView("manual_list") : handleRunCmd(cmd.name)}
                      >
                        {st === "loading" ? <span className="spinner" /> : `${cmd.name.toUpperCase()} ▶`}
                      </button>
                      {out && (
                        <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                          onClick={() => setOutputModal({ name: cmd.name, content: out })}>결과</button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
