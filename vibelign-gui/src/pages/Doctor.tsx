// === ANCHOR: DOCTOR_START ===
import { useState, useEffect, useCallback } from "react";
import { doctorJson, doctorPlanJson, doctorApply } from "../lib/vib";

interface Issue {
  severity?: string;
  found: string;
  why_it_matters?: string;
  next_step?: string;
  path?: string;
}

interface DoctorReport {
  project_score: number;
  status: string;
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
}

export default function Doctor({ projectDir, apiKey }: DoctorProps) {
  const [view, setView] = useState<View>("report");
  const [report, setReport] = useState<DoctorReport | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyMsg, setApplyMsg] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await doctorJson(projectDir) as DoctorReport;
      setReport(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

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

  function scoreClass(score: number) {
    if (score >= 80) return "score-high";
    if (score >= 50) return "score-medium";
    return "score-low";
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
    try {
      const result = await doctorApply(projectDir, apiKey ?? undefined) as { ok: boolean; done?: number; manual?: number };
      if (result.ok) {
        setApplyMsg(`완료: ${result.done ?? 0}개 자동 적용, ${result.manual ?? 0}개 수동 필요`);
        loadReport();
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
                background: report.status === "Healthy" ? "#4DFF91" :
                            report.status === "Risky"   ? "#FFD166" : "#FF4D4D",
                border: "1px solid #1A1A1A",
                color: report.status === "High Risk" ? "#fff" : "#1A1A1A",
              }}>
                {report.status}
              </span>
            </>
          )}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn btn-ghost btn-sm" onClick={loadReport} disabled={loading}>새로고침</button>
          <button className="btn btn-sm" style={{ background: "#7B4DFF" }}
            onClick={() => { setView("plan"); if (!plan) loadPlan(); }}>
            PLAN
          </button>
          <button className="btn btn-sm" onClick={handleApply} disabled={applying}>
            {applying ? <span className="spinner" /> : "APPLY ▶"}
          </button>
        </div>
      </div>

      {error   && <div className="alert alert-error"   style={{ margin: "0 20px 8px" }}>{error}</div>}
      {applyMsg && <div className="alert alert-success" style={{ margin: "0 20px 8px" }}>{applyMsg}</div>}

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
              <div><span className="terminal-prompt">$ </span>vib doctor --json</div>
              <div><span className="terminal-check">✓ </span>앵커 커버리지: {Math.round(report.anchor_coverage * 100)}%</div>
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
                    {(issue.severity ?? "INFO").toUpperCase()}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 12 }}>{issue.found}</div>
                    {issue.path && <code style={{ fontSize: 10, color: "#888" }}>{issue.path}</code>}
                    {issue.next_step && (
                      <div style={{ fontSize: 11, marginTop: 3, color: "#666" }}>{issue.next_step}</div>
                    )}
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
