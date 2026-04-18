// === ANCHOR: DOCTOR_START ===
import { useState, useEffect, useCallback } from "react";
import { doctorJson, doctorPlanJson, doctorApply, anchorAutoIntentJson, getAiEnhancement, buildGuiAiEnv } from "../lib/vib";

interface Issue {
  severity: "high" | "medium" | "low";
  category?: string;
  found: string;
  why_it_matters?: string;
  next_step?: string;
  path?: string | null;
  recommended_command?: string | null;
  can_auto_fix?: boolean;
  auto_fix_label?: string | null;
}

interface DoctorReport {
  project_score: number;
  status: "Safe" | "Good" | "Caution" | "Risky" | "High Risk";
  anchor_coverage: number;
  issues: Issue[];
  recommended_actions: string[];
}

interface Action {
  action_type: string;
  description: string;
  target_path?: string;
  command?: string;
}

interface Plan {
  actions: Action[];
  source_score: number;
  warnings: string[];
}

type View = "report" | "plan";

interface DoctorProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
}

export default function Doctor({ projectDir, apiKey, providerKeys }: DoctorProps) {
  const [view, setView] = useState<View>("report");
  const [report, setReport] = useState<DoctorReport | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [strict, setStrict] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyMsg, setApplyMsg] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<string | null>(null);
  const [useWithAi, setUseWithAi] = useState(false);
  const [aiProgress, setAiProgress] = useState<{ done: number; total: number; cached: number; toCall: number } | null>(null);
  const [aiErrors, setAiErrors] = useState<string[]>([]);
  const [aiStderrLog, setAiStderrLog] = useState<string | null>(null);
  const [showStderrLog, setShowStderrLog] = useState(false);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await doctorJson(projectDir, strict) as DoctorReport;
      setReport(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectDir, strict]);

  const loadPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await doctorPlanJson(projectDir) as Plan;
      setPlan(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  useEffect(() => { loadReport(); }, [loadReport]);

  useEffect(() => {
    if (!projectDir) return;
    getAiEnhancement(projectDir)
      .then(setUseWithAi)
      .catch(() => {});
  }, [projectDir]);

  function scoreClass(score: number) {
    if (score >= 80) return "score-high";
    if (score >= 50) return "score-medium";
    return "score-low";
  }

  function statusBadgeStyle(status: DoctorReport["status"]) {
    if (status === "Safe" || status === "Good") {
      return { background: "#4DFF91", color: "#1A1A1A" };
    }
    if (status === "Caution" || status === "Risky") {
      return { background: "#FFD166", color: "#1A1A1A" };
    }
    return { background: "#FF4D4D", color: "#fff" };
  }

  function sevClass(sev?: string) {
    const s = (sev ?? "").toLowerCase();
    if (s === "high")                  return "sev-high";
    if (s === "medium" || s === "med") return "sev-med";
    if (s === "low")                   return "sev-low";
    return "sev-info";
  }

  async function handleApply() {
    setApplying(true);
    setApplyMsg(null);
    setAiStatus(null);
    setError(null);
    try {
      const aiEnv = buildGuiAiEnv(providerKeys, apiKey);
      const result = await doctorApply(projectDir, aiEnv) as {
        ok: boolean; done?: number; manual?: number; needs_ai_aliases?: boolean;
      };
      if (result.ok) {
        setApplyMsg(`완료: ${result.done ?? 0}개 자동 적용, ${result.manual ?? 0}개 수동 필요`);
        await Promise.all([loadReport(), loadPlan()]);
        if (result.needs_ai_aliases) {
          if (useWithAi) {
            const started = Date.now();
            setAiStatus("AI aliases 생성 준비 중...");
            setAiProgress(null);
            setAiErrors([]);
            setAiStderrLog(null);
            setShowStderrLog(false);
            anchorAutoIntentJson(projectDir, {
              aiEnv,
              withAi: true,
              onProgress: (ev) => {
                if (ev.step === "ai-cache") {
                  const total = ev.total ?? 0;
                  const cached = ev.cached ?? 0;
                  const toCall = ev.to_call ?? 0;
                  setAiProgress({ done: 0, total: ev.batches ?? 0, cached, toCall });
                  if (toCall === 0) {
                    setAiStatus(`캐시 히트 ${cached}/${total} — API 호출 없음`);
                  } else {
                    setAiStatus(`AI 보강 중... (신규 ${toCall}개, 캐시 ${cached}개)`);
                  }
                } else if (ev.step === "ai-batch") {
                  setAiProgress((prev) => ({
                    done: ev.done ?? 0,
                    total: ev.total ?? prev?.total ?? 0,
                    cached: prev?.cached ?? 0,
                    toCall: prev?.toCall ?? 0,
                  }));
                } else if (ev.step === "ai-error") {
                  const stage = ev.stage ?? "?";
                  const reason = ev.message ?? "unknown";
                  const cnt = ev.count ?? 0;
                  setAiErrors((prev) => [...prev, `[${stage}] batch=${ev.batch ?? "?"} 사유=${reason} 앵커=${cnt}개`]);
                }
              },
            })
              .then(({ data, stderrLog }) => {
                setAiStderrLog(stderrLog || null);
                const elapsed = ((Date.now() - started) / 1000).toFixed(1);
                const cached = data.ai_cached_hit ?? 0;
                const failed = data.ai_failed ?? 0;
                const retried = data.ai_retried ?? 0;
                const parts: string[] = [`AI 보강 완료 (${elapsed}s)`];
                if (data.ai_count) parts.push(`신규 ${data.ai_count}개`);
                if (cached) parts.push(`캐시 ${cached}개`);
                if (retried) parts.push(`재시도 ${retried}개`);
                if (failed) parts.push(`실패 ${failed}개(네거티브캐시)`);
                if (!data.ai_count && !cached) parts.push("변경 없음");
                setAiStatus(parts.join(" · "));
              })
              .catch((e) => setAiStatus(`AI aliases 생성 실패: ${e}`))
              .finally(() => setTimeout(() => { setAiStatus(null); setAiProgress(null); }, 8000));
          } else {
            setAiStatus("AI aliases 보강은 APPLY 옆 체크박스를 켠 뒤 다시 실행하세요 (또는 Settings 에서 전역 ON)");
            setTimeout(() => setAiStatus(null), 8000);
          }
        }
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setApplying(false);
    }
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* ─── 헤더 ───────────────────────────────────────── */}
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="page-title">DOCTOR</span>
          {loading && <span className="spinner" />}
          {report && !loading && (
            <>
              <span className={`score-badge ${scoreClass(report.project_score)}`}>
                {report.project_score}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                padding: "2px 8px",
                border: "1px solid #1A1A1A",
                ...statusBadgeStyle(report.status),
              }}>
                {report.status}
              </span>
            </>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <button
            className="btn btn-ghost btn-sm"
            style={{
              fontSize: 10, padding: "2px 8px",
              background: strict ? "#1A1A1A" : "transparent",
              color: strict ? "#FF4D8B" : "#888",
              border: strict ? "2px solid #FF4D8B" : "2px solid #ccc",
              fontWeight: 700,
            }}
            onClick={() => setStrict((v) => !v)}
          >
            {strict ? "정밀" : "일반"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={loadReport} disabled={loading}>새로고침</button>
          <button className="btn btn-sm" style={{ background: "#7B4DFF" }}
            onClick={() => { setView("plan"); if (!plan) loadPlan(); }}>
            PLAN
          </button>
          <label
            title="체크 시 이번 apply 에서만 AI aliases 보강까지 실행합니다 (기본값은 Settings 의 ai_enhancement)."
            style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: 10, fontWeight: 700, color: useWithAi ? "#4DFF91" : "#888",
              cursor: "pointer", userSelect: "none",
              border: "2px solid #1A1A1A",
              background: useWithAi ? "#1E2216" : "transparent",
              padding: "2px 6px",
            }}
          >
            <input
              type="checkbox"
              checked={useWithAi}
              onChange={(e) => setUseWithAi(e.target.checked)}
              style={{ margin: 0, cursor: "pointer" }}
            />
            AI 보강
          </label>
          <button className="btn btn-sm" onClick={handleApply} disabled={applying}>
            {applying ? <span className="spinner" /> : "APPLY ▶"}
          </button>
        </div>
      </div>

      {error   && <div className="alert alert-error"   style={{ margin: "0 20px 8px" }}>{error}</div>}
      {applyMsg && <div className="alert alert-success" style={{ margin: "0 20px 8px" }}>{applyMsg}</div>}
      {aiStatus && (
        <div className="alert" style={{
          margin: "0 20px 8px",
          background: aiStatus.includes("완료") ? "#e8f5e9" : aiStatus.includes("실패") ? "#fce4ec" : "#e3f2fd",
          color: "#333",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {!aiStatus.includes("완료") && !aiStatus.includes("실패") && <span className="spinner" />}
            <span>{aiStatus}</span>
          </div>
          {aiProgress && aiProgress.total > 0 && !aiStatus.includes("완료") && !aiStatus.includes("실패") && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                flex: 1, height: 6, background: "#cfd8dc", borderRadius: 3, overflow: "hidden",
              }}>
                <div style={{
                  width: `${Math.min(100, (aiProgress.done / aiProgress.total) * 100)}%`,
                  height: "100%", background: "#4DFF91", transition: "width 0.2s ease",
                }} />
              </div>
              <span style={{ fontSize: 11, color: "#555", minWidth: 60, textAlign: "right" }}>
                {aiProgress.done}/{aiProgress.total} 배치
              </span>
            </div>
          )}
        </div>
      )}
      {aiErrors.length > 0 && (
        <div className="alert" style={{
          margin: "0 20px 8px", background: "#fff8e1", color: "#5D4037",
          display: "flex", flexDirection: "column", gap: 2,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 700, fontSize: 12 }}>⚠ 배치 경고 {aiErrors.length}건</span>
            <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, padding: "2px 8px" }} onClick={() => setAiErrors([])}>닫기</button>
          </div>
          {aiErrors.slice(-6).map((e, i) => (
            <div key={i} style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 10 }}>{e}</div>
          ))}
        </div>
      )}
      {aiStderrLog && (
        <div className="alert" style={{ margin: "0 20px 8px", background: "#fafafa", color: "#333" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 10, padding: "2px 8px", border: "1px solid #888" }}
              onClick={() => setShowStderrLog((v) => !v)}
            >
              {showStderrLog ? "stderr 로그 숨기기" : `stderr 로그 보기 (${aiStderrLog.split("\n").length} 줄)`}
            </button>
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 10, padding: "2px 8px" }}
              onClick={() => { setAiStderrLog(null); setShowStderrLog(false); }}
            >
              닫기
            </button>
          </div>
          {showStderrLog && (
            <pre style={{
              marginTop: 6, padding: 8, background: "#1A1A1A", color: "#ddd",
              fontSize: 10, lineHeight: 1.4, maxHeight: 320, overflow: "auto",
              fontFamily: "IBM Plex Mono, monospace", whiteSpace: "pre-wrap", wordBreak: "break-word",
            }}>{aiStderrLog}</pre>
          )}
        </div>
      )}

      {/* ─── 탭 ─────────────────────────────────────────── */}
      <div className="nav-tabs">
        <button className={`nav-tab ${view === "report" ? "active" : ""}`} onClick={() => setView("report")}>리포트</button>
        <button className={`nav-tab ${view === "plan"   ? "active" : ""}`} onClick={() => { setView("plan"); if (!plan) loadPlan(); }}>플랜</button>
      </div>

      {/* ─── 콘텐츠 ─────────────────────────────────────── */}
      <div className="page-content">
        {/* 리포트 */}
        {view === "report" && report && (
          <>
            {/* 터미널 스타일 요약 */}
            <div className="terminal" style={{ marginBottom: 16 }}>
              <div className="terminal-header">
                <div className="terminal-dot red" />
                <div className="terminal-dot yellow" />
                <div className="terminal-dot green" />
              </div>
              <div><span className="terminal-prompt">$ </span>vib doctor --json{strict ? " --strict" : ""}</div>
              <div><span className="terminal-check">✓ </span>앵커 커버리지: {report.anchor_coverage}%</div>
              <div><span className="terminal-check">✓ </span>이슈: {report.issues.length}개</div>
              <div><span className="terminal-check">✓ </span>프로젝트 점수: {report.project_score} / 100</div>
            </div>

            {/* 이슈 목록 */}
            {report.issues.length === 0 ? (
              <div className="card" style={{ textAlign: "center", padding: 28 }}>
                <div style={{ fontSize: 22, marginBottom: 6 }}>✓</div>
                <div style={{ fontWeight: 700, fontSize: 13 }}>이슈 없음 — 상태 좋음!</div>
              </div>
            ) : (
              report.issues.map((issue, i) => (
                <div className="issue-item" key={i}>
                  <span className={`issue-severity ${sevClass(issue.severity)}`}>
                    {(issue.severity ?? "low").toUpperCase()}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                      <div style={{ fontWeight: 700, fontSize: 12 }}>{issue.found}</div>
                      {issue.category && <code style={{ fontSize: 10 }}>{issue.category}</code>}
                    </div>
                    {issue.path && <code style={{ fontSize: 10, color: "#888" }}>{issue.path}</code>}
                    {issue.why_it_matters && (
                      <div style={{ fontSize: 11, marginTop: 3, color: "#666" }}>{issue.why_it_matters}</div>
                    )}
                    {issue.next_step && (
                      <div style={{ fontSize: 11, marginTop: 3, color: "#666" }}>다음 단계: {issue.next_step}</div>
                    )}
                    {issue.recommended_command && (
                      <code style={{ display: "block", fontSize: 10, color: "#888", marginTop: 4 }}>
                        {issue.recommended_command}
                      </code>
                    )}
                    <div style={{ fontSize: 10, marginTop: 4, color: issue.can_auto_fix ? "#0a7" : "#888" }}>
                      {issue.can_auto_fix
                        ? `자동 수정 가능${issue.auto_fix_label ? ` · ${issue.auto_fix_label}` : ""}`
                        : "자동 수정 불가"}
                    </div>
                  </div>
                </div>
              ))
            )}
          </>
        )}

        {/* 플랜 */}
        {view === "plan" && (
          <>
            {loading && <div style={{ padding: 20, textAlign: "center" }}><span className="spinner" /></div>}
            {plan && (
              <>
                <div style={{ marginBottom: 12, fontSize: 12, color: "#666", fontWeight: 600 }}>
                  실행 예정 {plan.actions.length}개 항목
                </div>
                {plan.actions.length === 0 ? (
                  <div className="card" style={{ textAlign: "center", padding: 28, fontWeight: 700 }}>
                    할 일이 없어요!
                  </div>
                ) : (
                  plan.actions.map((action, i) => (
                    <div className="issue-item" key={i}>
                      <span className="issue-severity sev-info" style={{ minWidth: 80, textAlign: "center" }}>
                        {action.action_type.replace("_", " ")}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 12 }}>{action.description}</div>
                        {action.command && (
                          <code style={{ fontSize: 10, color: "#888" }}>{action.command}</code>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {plan.warnings.map((w, i) => (
                  <div className="alert alert-warn" key={i}>{w}</div>
                ))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
// === ANCHOR: DOCTOR_END ===
