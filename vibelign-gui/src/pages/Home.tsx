// === ANCHOR: HOME_START ===
import { useState } from "react";
import { vibGuard, vibScan, vibTransfer, startWatch, stopWatch } from "../lib/vib";

type CardState = "idle" | "loading" | "done" | "error";

interface HomeProps {
  projectDir: string;
  onNavigate: (page: "checkpoints") => void;
}

export default function Home({ projectDir, onNavigate }: HomeProps) {
  const [guardState, setGuardState]       = useState<CardState>("idle");
  const [guardResult, setGuardResult]     = useState<{ status: string; summary: string } | null>(null);
  const [scanState, setScanState]         = useState<CardState>("idle");
  const [watchOn, setWatchOn]             = useState(false);
  const [watchLoading, setWatchLoading]   = useState(false);
  const [mapMode, setMapMode]             = useState<"manual" | "auto">("manual");
  const [transferState, setTransferState] = useState<CardState>("idle");
  const [error, setError]                 = useState<string | null>(null);

  async function handleGuard() {
    setGuardState("loading");
    setGuardResult(null);
    setError(null);
    try {
      const r = await vibGuard(projectDir);
      setGuardResult({ status: r.status, summary: r.summary });
      setGuardState("done");
    } catch (e) {
      setError(String(e));
      setGuardState("error");
    }
  }

  async function handleScan() {
    setScanState("loading");
    setError(null);
    try {
      const r = await vibScan(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setScanState("done");
    } catch (e) {
      setError(String(e));
      setScanState("error");
    }
  }

  async function handleToggleWatch() {
    setWatchLoading(true);
    setError(null);
    try {
      if (watchOn) {
        await stopWatch();
        setWatchOn(false);
      } else {
        await startWatch(projectDir);
        setWatchOn(true);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setWatchLoading(false);
    }
  }

  async function handleTransfer() {
    setTransferState("loading");
    setError(null);
    try {
      const r = await vibTransfer(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setTransferState("done");
    } catch (e) {
      setError(String(e));
      setTransferState("error");
    }
  }

  function guardColor(status: string) {
    if (status === "pass") return "#4DFF91";
    if (status === "warn") return "#FFD166";
    return "#FF4D4D";
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">HOME</span>
      </div>

      {error && <div className="alert alert-error" style={{ margin: "0 20px 8px" }}>{error}</div>}

      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>

          {/* ── 코드맵 생성 ────────────────────────────────────── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#F5621E18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#F5621E", color: "#fff", borderColor: "#F5621E", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>
                MAP
              </div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>코드맵 생성</div>
              {watchOn && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>
                  감시 중
                </span>
              )}
              {mapMode === "manual" && scanState === "done" && !watchOn && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>
                  갱신 완료
                </span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              {/* 수동/자동 탭 */}
              <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
                {(["manual", "auto"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMapMode(m)}
                    style={{
                      flex: 1, fontSize: 10, fontWeight: 700, padding: "3px 0",
                      border: "2px solid #1A1A1A",
                      background: mapMode === m ? "#1A1A1A" : "#fff",
                      color: mapMode === m ? "#fff" : "#1A1A1A",
                      cursor: "pointer",
                    }}
                  >
                    {m === "manual" ? "수동" : "자동"}
                  </button>
                ))}
              </div>
              {mapMode === "manual" ? (
                <>
                  <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>앵커 스캔 + 코드맵 1회 갱신</div>
                  <button
                    className="btn btn-sm"
                    style={{ width: "100%", background: "#F5621E", color: "#fff", border: "2px solid #1A1A1A" }}
                    disabled={scanState === "loading"}
                    onClick={handleScan}
                  >
                    {scanState === "loading" ? <span className="spinner" /> : "SCAN ▶"}
                  </button>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
                    {watchOn ? "파일 변경 시 코드맵 자동 갱신 중" : "실시간 감시 시작 (vib watch)"}
                  </div>
                  <button
                    className="btn btn-sm"
                    style={{
                      width: "100%", border: "2px solid #1A1A1A",
                      background: watchOn ? "#FF4D4D" : "#F5621E",
                      color: "#fff",
                    }}
                    disabled={watchLoading}
                    onClick={handleToggleWatch}
                  >
                    {watchLoading ? <span className="spinner" /> : watchOn ? "STOP ■" : "WATCH ▶"}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* ── AI 폭주 방지 ────────────────────────────────────── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#FF4D8B18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#FF4D8B", color: "#fff", borderColor: "#FF4D8B", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>
                ♥
              </div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>AI 폭주 방지</div>
              {guardState === "done" && guardResult && (
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: "2px 6px",
                  background: guardColor(guardResult.status),
                  color: "#1A1A1A", border: "1px solid #1A1A1A",
                }}>
                  {guardResult.status.toUpperCase()}
                </span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
                {guardResult ? guardResult.summary : "현재 프로젝트 상태 점검"}
              </div>
              <button
                className="btn btn-sm"
                style={{ width: "100%", background: "#FF4D8B", color: "#fff", border: "2px solid #1A1A1A" }}
                disabled={guardState === "loading"}
                onClick={handleGuard}
              >
                {guardState === "loading" ? <span className="spinner" /> : "GUARD ▶"}
              </button>
            </div>
          </div>

          {/* ── 원클릭 복구 ─────────────────────────────────────── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>
                ↺
              </div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>원클릭 복구</div>
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>체크포인트 목록으로 이동</div>
              <button
                className="btn btn-sm"
                style={{ width: "100%", background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
                onClick={() => onNavigate("checkpoints")}
              >
                열기 ▶
              </button>
            </div>
          </div>

          {/* ── AI 이동 자유 ─────────────────────────────────────── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#4D9FFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#4D9FFF", color: "#fff", borderColor: "#4D9FFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>
                ⇄
              </div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>AI 이동 자유</div>
              {transferState === "done" && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>
                  생성 완료
                </span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>PROJECT_CONTEXT.md 생성</div>
              <button
                className="btn btn-sm"
                style={{ width: "100%", background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A" }}
                disabled={transferState === "loading"}
                onClick={handleTransfer}
              >
                {transferState === "loading" ? <span className="spinner" /> : "TRANSFER ▶"}
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
