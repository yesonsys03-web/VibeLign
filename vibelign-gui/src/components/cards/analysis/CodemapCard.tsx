// === ANCHOR: CODEMAP_CARD_START ===
import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { vibScan, startWatch, stopWatch, watchStatus } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface CodemapCardProps {
  projectDir: string;
  watchOn: boolean;
  setWatchOn: (v: boolean) => void;
  mapMode: "manual" | "auto";
  setMapMode: (v: "manual" | "auto") => void;
}

export default function CodemapCard({ projectDir, watchOn, setWatchOn, mapMode, setMapMode }: CodemapCardProps) {
  const [scanState, setScanState] = useState<CardState>("idle");
  const [watchLoading, setWatchLoading] = useState(false);
  const [watchLogs, setWatchLogs] = useState<string[]>([]);
  const watchLogRef = useRef<HTMLDivElement>(null);

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

  async function handleScan() {
    setScanState("loading");
    try {
      const r = await vibScan(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setScanState("done");
    } catch {
      setScanState("error");
    }
  }

  async function handleToggleWatch() {
    setWatchLoading(true);
    try {
      if (watchOn) { await stopWatch(); setWatchOn(false); }
      else { setWatchLogs([]); await startWatch(projectDir); setWatchOn(true); }
    } catch {
      // 오류 무시
    } finally {
      setWatchLoading(false);
    }
  }

  return (
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
  );
}
// === ANCHOR: CODEMAP_CARD_END ===
