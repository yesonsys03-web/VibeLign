import { useEffect, useState } from "react";

import { listPlanningChatSessions } from "../../lib/vib";
import type { PlanningSessionSummary } from "../../lib/vib/types";

interface PlanningSessionPickerProps {
  readonly projectDir: string;
  readonly onSelect: (sessionId: string) => void;
  readonly onClose: () => void;
}

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}

export function PlanningSessionPicker({ projectDir, onSelect, onClose }: PlanningSessionPickerProps) {
  const [sessions, setSessions] = useState<PlanningSessionSummary[] | null>(null);

  useEffect(() => {
    let active = true;
    void listPlanningChatSessions(projectDir).then((rows) => {
      if (active) {
        setSessions(rows);
      }
    });
    return () => {
      active = false;
    };
  }, [projectDir]);

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
      onClick={onClose}
    >
      <div
        style={{ background: "#FEFBF0", border: "2px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 520, maxHeight: "80vh", display: "flex", flexDirection: "column" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div style={{ background: "#1A1A1A", padding: "12px 18px" }}>
          <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 13, color: "#fff", letterSpacing: 1 }}>이전 기획 불러오기</span>
        </div>
        <div style={{ padding: 16, overflow: "auto", display: "grid", gap: 8 }}>
          {sessions === null && <div style={{ fontSize: 12, opacity: 0.7 }}>불러오는 중…</div>}
          {sessions !== null && sessions.length === 0 && (
            <div style={{ fontSize: 12, opacity: 0.7 }}>아직 저장된 기획이 없어요.</div>
          )}
          {sessions?.map((session) => (
            <button
              key={session.sessionId}
              type="button"
              onClick={() => onSelect(session.sessionId)}
              style={{ textAlign: "left", border: "2px solid #1A1A1A", background: "#fff", padding: "10px 12px", cursor: "pointer", display: "grid", gap: 4 }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <strong style={{ fontSize: 12 }}>{session.title || "(제목 없음)"}</strong>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    padding: "2px 8px",
                    border: "1.5px solid #1A1A1A",
                    whiteSpace: "nowrap",
                    background: session.saved ? "#1E9E5A" : "#E6E3D8",
                    color: session.saved ? "#fff" : "#6B6657",
                  }}
                >
                  {session.saved ? "✓ 저장됨" : "작성중"}
                </span>
              </div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {session.outputPath ? `${fileName(session.outputPath)} · ` : ""}
                대화 {session.messageCount} · 카드 {session.cardCount}
              </div>
            </button>
          ))}
        </div>
        <div style={{ padding: "12px 18px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  );
}
