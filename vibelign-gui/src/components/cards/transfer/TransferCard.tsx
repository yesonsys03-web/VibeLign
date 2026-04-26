// === ANCHOR: TRANSFER_CARD_START ===
import { useState } from "react";
import { vibTransfer } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

const GUI_HANDOFF_NEXT_ACTION = "Active intent와 Verification snapshot을 확인하고, Warnings / risks를 정리한 뒤 관련 테스트를 재실행하세요.";

interface TransferCardProps {
  projectDir: string;
}

export default function TransferCard({ projectDir }: TransferCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [handoff, setHandoff] = useState(false);
  const [compact, setCompact] = useState(false);

  async function handleTransfer() {
    setSt("loading");
    try {
      const r = await vibTransfer(projectDir, {
        handoff,
        compact,
        firstNextAction: handoff ? GUI_HANDOFF_NEXT_ACTION : undefined,
      });
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setSt("done");
    } catch {
      setSt("error");
    }
  }

  return (
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
        {st === "done" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
        {st === "error" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ fontSize: 16.5, color: "#555", marginBottom: 8 }}>PROJECT_CONTEXT 생성</div>
        {handoff && (
          <div style={{ fontSize: 10, color: "#555", lineHeight: 1.35, marginBottom: 6 }}>
            현재 세션 작업과 다음 할 일을 자동으로 정리해서 새 AI가 바로 이어받게 해요.
          </div>
        )}
        <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
          <button onClick={() => setHandoff((s) => !s)} style={{
            flex: 1, fontSize: 9, fontWeight: 700, padding: "2px 0",
            border: "2px solid #1A1A1A",
            background: handoff ? "#1A1A1A" : "#fff",
            color: handoff ? "#fff" : "#1A1A1A", cursor: "pointer",
          }}>--handoff</button>
          <button onClick={() => setCompact((s) => !s)} style={{
            flex: 1, fontSize: 9, fontWeight: 700, padding: "2px 0",
            border: "2px solid #1A1A1A",
            background: compact ? "#1A1A1A" : "#fff",
            color: compact ? "#fff" : "#1A1A1A", cursor: "pointer",
          }}>--compact</button>
        </div>
        <button className="btn btn-sm" style={{ width: "100%", background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A" }}
          disabled={st === "loading"} onClick={handleTransfer}>
          {st === "loading" ? <span className="spinner" /> : "TRANSFER ▶"}
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: TRANSFER_CARD_END ===
