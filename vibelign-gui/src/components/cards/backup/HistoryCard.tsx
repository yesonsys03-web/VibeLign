// === ANCHOR: HISTORY_CARD_START ===
import { useRef, useState } from "react";
import { runVib } from "../../../lib/vib";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";
import { CardState } from "../../../lib/commands";

interface HistoryCardProps {
  projectDir: string;
}

export default function HistoryCard({ projectDir }: HistoryCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [out, setOut] = useState("");
  const [hasWarning, setHasWarning] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const idleTimer = useRef<number | undefined>(undefined);

  async function handleRun() {
    setSt("loading");
    setOut("");
    if (idleTimer.current !== undefined) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = undefined;
    }
    try {
      const r = await runVib(["history"], projectDir);
      const stdoutContent = r.stdout.trim();
      const stderrContent = r.stderr.trim();
      const combined = [stderrContent, stdoutContent].filter(Boolean).join("\n\n");
      const output = combined || (r.ok ? "완료" : `exit ${r.exit_code}`);
      const warn = Boolean(stderrContent);
      setSt(r.ok ? "done" : "error");
      setOut(output);
      setHasWarning(warn);
      if (!r.ok || warn) setShowModal(true);
      if (r.ok && !warn) {
        idleTimer.current = window.setTimeout(() => {
          setSt("idle");
          idleTimer.current = undefined;
        }, 3000);
      }
    } catch (e) {
      setSt("error");
      setOut(String(e));
      setHasWarning(false);
    }
  }

  return (
    <>
      {showModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 480, maxHeight: "70vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>HISTORY 결과</span>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <pre style={{ margin: 0, padding: 16, overflowY: "auto", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", color: st === "error" ? "#FF4D4D" : "#1A1A1A" }}>
              {out}
            </pre>
          </div>
        </div>
      )}
      <div className="feature-card" style={{ cursor: "default" }}>
        <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
          <div className="feature-card-icon"
            style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 14, fontWeight: 900 }}>🕓</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
              <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>저장 기록</span>
            <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
              저장이 언제 찍혔는지 시간 순으로 보여 줘요
            </span>
          </div>
          {(st === "done" || (st === "idle" && out)) && !hasWarning && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
          )}
          {hasWarning && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>
          )}
          {st === "error" && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
          )}
        </div>
        <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
          <GuiCliOutputBlock
            text={out}
            placeholder="저장 기록 보기"
            variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
          />
          <div style={{ display: "flex", gap: 4 }}>
            <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
              disabled={st === "loading"} onClick={handleRun}>
              {st === "loading" ? <span className="spinner" /> : "HISTORY ▶"}
            </button>
            {out && (
              <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                onClick={() => setShowModal(true)}>결과</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
// === ANCHOR: HISTORY_CARD_END ===
