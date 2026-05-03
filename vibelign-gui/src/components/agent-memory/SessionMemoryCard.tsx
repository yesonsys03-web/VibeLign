// === ANCHOR: SESSION_MEMORY_CARD_START ===
import { useEffect, useState } from "react";
import { CardState } from "../../lib/commands";
import { MemorySummaryResult, memorySummary } from "../../lib/vib";

interface SessionMemoryCardProps {
  projectDir: string;
}

export default function SessionMemoryCard({ projectDir }: SessionMemoryCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [summary, setSummary] = useState<MemorySummaryResult | null>(null);

  async function refresh() {
    setState("loading");
    try {
      setSummary(await memorySummary(projectDir));
      setState("done");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void refresh();
  }, [projectDir]);

  const decisions = summary?.decisions.slice(-2) ?? [];

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#4DFF9118", padding: "10px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#4DFF91", color: "#1A1A1A", borderColor: "#4DFF91", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>🧠</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>세션 메모리</div>
          <div style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>현재 의도와 다음 행동을 AI 전환 전에 확인해요</div>
        </div>
        {state === "error" && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <MemoryLine label="Active" value={summary?.activeIntent ?? "불러오는 중..."} />
        <MemoryLine label="Next" value={summary?.nextAction ?? "불러오는 중..."} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, fontSize: 10 }}>
          <span style={{ fontWeight: 900, color: "#777", letterSpacing: 0.8, textTransform: "uppercase" }}>Verification</span>
          <span style={{ fontWeight: 900, padding: "2px 6px", border: "1.5px solid #1A1A1A", background: freshnessColor(summary?.verificationFreshness) }}>
            {summary?.verificationFreshness ?? "loading"}
          </span>
        </div>
        {(summary?.verification ?? []).slice(-1).map((item, index) => (
          <div key={index} style={{ fontSize: 10, color: "#555", lineHeight: 1.35, marginBottom: 6 }}>최근 검증: {item}</div>
        ))}
        {decisions.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 10, color: "#555", lineHeight: 1.45 }}>
            {decisions.map((item, index) => <div key={index}>• {item}</div>)}
          </div>
        )}
        <button className="btn btn-sm" style={{ width: "100%", marginTop: 8, background: "#4DFF91", color: "#1A1A1A", border: "2px solid #1A1A1A" }} disabled={state === "loading"} onClick={refresh}>
          {state === "loading" ? <span className="spinner" /> : "메모리 새로고침"}
        </button>
      </div>
    </div>
  );
}

function MemoryLine({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 9, fontWeight: 900, color: "#777", letterSpacing: 0.8, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 11, color: "#1A1A1A", lineHeight: 1.45, border: "1.5px solid #1A1A1A", background: "#fff", padding: "5px 7px" }}>{value}</div>
    </div>
  );
}

function freshnessColor(value: MemorySummaryResult["verificationFreshness"] | undefined): string {
  if (value === "fresh") return "#4DFF91";
  if (value === "stale") return "#FFD166";
  return "#EEE";
}
// === ANCHOR: SESSION_MEMORY_CARD_END ===
