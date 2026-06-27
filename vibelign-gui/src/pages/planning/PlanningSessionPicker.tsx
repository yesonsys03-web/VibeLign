// === ANCHOR: PLANNINGSESSIONPICKER_START ===
import { useEffect, useState } from "react";

import { deletePlanningChatSession, listPlanningChatSessions } from "../../lib/vib";
import type { PlanningSessionSummary } from "../../lib/vib/types";

interface PlanningSessionPickerProps {
  readonly projectDir: string;
  readonly onSelect: (sessionId: string) => void;
  readonly onClose: () => void;
  /** 세션이 삭제되면 호출(예: 현재 열린 기획이 그 세션이면 호출부가 정리). */
  readonly onDeleted?: (sessionId: string) => void;
}

// === ANCHOR: PLANNINGSESSIONPICKER_FILENAME_START ===
function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}
// === ANCHOR: PLANNINGSESSIONPICKER_FILENAME_END ===

// === ANCHOR: PLANNINGSESSIONPICKER_PLANNINGSESSIONPICKER_START ===
export function PlanningSessionPicker({ projectDir, onSelect, onClose, onDeleted }: PlanningSessionPickerProps) {
  const [sessions, setSessions] = useState<PlanningSessionSummary[] | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  // === ANCHOR: PLANNINGSESSIONPICKER_HANDLEDELETE_START ===
  async function handleDelete(sessionId: string) {
    setConfirmingId(null);
    setError(null);
    setDeletingId(sessionId);
    try {
      await deletePlanningChatSession(projectDir, sessionId);
      setSessions((rows) => rows?.filter((row) => row.sessionId !== sessionId) ?? null);
      onDeleted?.(sessionId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : typeof err === "string" ? err : "삭제하지 못했어요.");
    } finally {
      setDeletingId(null);
    }
  }
  // === ANCHOR: PLANNINGSESSIONPICKER_HANDLEDELETE_END ===

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
          {error && <div style={{ fontSize: 12, color: "#B91C1C", fontWeight: 700 }}>삭제 오류: {error}</div>}
          {sessions?.map((session) => (
            <div key={session.sessionId} style={{ display: "flex", alignItems: "stretch", gap: 6 }}>
              <button
                type="button"
                onClick={() => onSelect(session.sessionId)}
                disabled={deletingId === session.sessionId}
                style={{ flex: 1, textAlign: "left", border: "2px solid #1A1A1A", background: "#fff", padding: "10px 12px", cursor: "pointer", display: "grid", gap: 4, opacity: deletingId === session.sessionId ? 0.5 : 1 }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <strong style={{ fontSize: 12 }}>{session.title || "(제목 없음)"}</strong>
                  <span
                    style={{
                      fontSize: 12,
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
                <div style={{ fontSize: 12, opacity: 0.75 }}>
                  {session.outputPath ? `${fileName(session.outputPath)} · ` : ""}
                  대화 {session.messageCount} · 카드 {session.cardCount}
                </div>
              </button>
              {confirmingId === session.sessionId ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, justifyContent: "center" }}>
                  <button type="button" onClick={() => void handleDelete(session.sessionId)} title="이 기획을 영구 삭제" style={{ border: "2px solid #B91C1C", background: "#B91C1C", color: "#fff", fontSize: 12, fontWeight: 800, padding: "2px 8px", cursor: "pointer", whiteSpace: "nowrap" }}>삭제</button>
                  <button type="button" onClick={() => setConfirmingId(null)} style={{ border: "2px solid #1A1A1A", background: "#fff", fontSize: 12, padding: "2px 8px", cursor: "pointer" }}>취소</button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirmingId(session.sessionId)} disabled={deletingId === session.sessionId} title="이 기획 삭제" style={{ border: "2px solid #1A1A1A", background: "#fff", fontSize: 14, padding: "0 10px", cursor: "pointer" }}>🗑</button>
              )}
            </div>
          ))}
        </div>
        <div style={{ padding: "12px 18px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
// === ANCHOR: PLANNINGSESSIONPICKER_PLANNINGSESSIONPICKER_END ===
  );
}
// === ANCHOR: PLANNINGSESSIONPICKER_END ===
