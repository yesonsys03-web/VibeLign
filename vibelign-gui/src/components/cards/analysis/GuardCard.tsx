// === ANCHOR: GUARD_CARD_START ===
import { useState } from "react";
import { vibGuard, GuardResult } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface GuardCardProps {
  projectDir: string;
  onGuardResult: (result: GuardResult) => void;
}

export default function GuardCard({ projectDir, onGuardResult }: GuardCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [guardStrict, setGuardStrict] = useState(false);
  const [lastResult, setLastResult] = useState<GuardResult | null>(null);

  async function handleGuard() {
    setSt("loading");
    try {
      const r = await vibGuard(projectDir, { strict: guardStrict });
      setLastResult(r);
      onGuardResult(r);
      setSt("done");
    } catch (e) {
      setSt("error");
    }
  }

  return (
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
        {st === "done" && lastResult && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
        {st === "error" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ fontSize: 16.5, color: "#555", marginBottom: 8 }}>
          {lastResult ? lastResult.summary.slice(0, 60) + "…" : "프로젝트 상태 점검"}
        </div>
        <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
          <button onClick={() => setGuardStrict((s) => !s)} style={{
            fontSize: 9, fontWeight: 700, padding: "2px 8px",
            border: "2px solid #1A1A1A",
            background: guardStrict ? "#1A1A1A" : "#fff",
            color: guardStrict ? "#fff" : "#1A1A1A", cursor: "pointer",
          }}>--strict</button>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn btn-sm" style={{ flex: 1, background: "#FF4D8B", color: "#fff", border: "2px solid #1A1A1A" }}
            disabled={st === "loading"} onClick={handleGuard}>
            {st === "loading" ? <span className="spinner" /> : "GUARD ▶"}
          </button>
          {lastResult && (
            <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
              onClick={() => onGuardResult(lastResult)}>결과 보기</button>
          )}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: GUARD_CARD_END ===
