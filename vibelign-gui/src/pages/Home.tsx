// === ANCHOR: HOME_START ===
import { useState } from "react";
import { vibGuard, vibScan, vibTransfer } from "../lib/vib";

type CardState = "idle" | "loading" | "done" | "error";

interface HomeProps {
  projectDir: string;
  onNavigate: (page: "checkpoints") => void;
}

export default function Home({ projectDir, onNavigate }: HomeProps) {
  const [guardState, setGuardState]     = useState<CardState>("idle");
  const [guardResult, setGuardResult]   = useState<{ status: string; summary: string } | null>(null);
  const [scanState, setScanState]       = useState<CardState>("idle");
  const [transferState, setTransferState] = useState<CardState>("idle");
  const [error, setError]               = useState<string | null>(null);

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
    if (status === "pass")   return "#4DFF91";
    if (status === "warn")   return "#FFD166";
    return "#FF4D4D";
  }

  const CARDS = [
    {
      icon: "MAP", color: "#F5621E",
      title: "코드맵 생성",
      desc: "앵커 스캔 + 코드맵 갱신",
      state: scanState,
      doneMsg: "코드맵 갱신 완료",
      action: handleScan,
      btnLabel: "SCAN ▶",
    },
    {
      icon: "♥", color: "#FF4D8B",
      title: "AI 폭주 방지",
      desc: guardResult
        ? guardResult.summary
        : "현재 프로젝트 상태 점검",
      state: guardState,
      doneMsg: guardResult ? `상태: ${guardResult.status.toUpperCase()}` : "완료",
      doneColor: guardResult ? guardColor(guardResult.status) : "#4DFF91",
      action: handleGuard,
      btnLabel: "GUARD ▶",
    },
    {
      icon: "↺", color: "#7B4DFF",
      title: "원클릭 복구",
      desc: "체크포인트 목록으로 이동",
      state: "idle" as CardState,
      doneMsg: "",
      action: () => onNavigate("checkpoints"),
      btnLabel: "열기 ▶",
    },
    {
      icon: "⇄", color: "#4D9FFF",
      title: "AI 이동 자유",
      desc: "PROJECT_CONTEXT.md 생성",
      state: transferState,
      doneMsg: "맥락 파일 생성 완료",
      action: handleTransfer,
      btnLabel: "TRANSFER ▶",
    },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">HOME</span>
      </div>

      {error && <div className="alert alert-error" style={{ margin: "0 20px 8px" }}>{error}</div>}

      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {CARDS.map((card) => (
            <div className="feature-card" key={card.icon} style={{ cursor: "default" }}>
              <div className="feature-card-header" style={{ background: card.color + "18", padding: "10px 14px" }}>
                <div className="feature-card-icon"
                  style={{ background: card.color, color: "#fff", borderColor: card.color, width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>
                  {card.icon}
                </div>
                <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>{card.title}</div>
                {card.state === "done" && (
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: "2px 6px",
                    background: (card as { doneColor?: string }).doneColor ?? "#4DFF91",
                    color: "#1A1A1A", border: "1px solid #1A1A1A",
                  }}>
                    {card.doneMsg}
                  </span>
                )}
              </div>
              <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
                <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>{card.desc}</div>
                <button
                  className="btn btn-sm"
                  style={{ width: "100%", background: card.color, color: "#fff", border: "2px solid #1A1A1A" }}
                  disabled={card.state === "loading"}
                  onClick={card.action}
                >
                  {card.state === "loading" ? <span className="spinner" /> : card.btnLabel}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
