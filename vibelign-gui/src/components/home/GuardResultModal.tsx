import type { GuardResult } from "../../lib/vib";

interface GuardResultModalProps {
  readonly guardResult: GuardResult;
  readonly onClose: () => void;
}

function guardStatusColor(status: GuardResult["status"]) {
  if (status === "pass") return "#4DFF91";
  if (status === "warn") return "#FFD166";
  return "#FF4D4D";
}

export function GuardResultModal({ guardResult, onClose }: GuardResultModalProps) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
      onClick={onClose}
    >
      <div
        style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 560, maxHeight: "80vh", display: "flex", flexDirection: "column" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div style={{ background: "#1A1A1A", padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 14, color: "#fff", letterSpacing: 2 }}>GUARD 결과</span>
            <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", background: guardStatusColor(guardResult.status), color: "#1A1A1A", border: "1px solid #555" }}>
              {guardResult.status.toUpperCase()}
            </span>
          </div>
          <button aria-label="모달 닫기" onClick={onClose} style={{ background: "transparent", border: "1px solid #555", color: "#aaa", cursor: "pointer", padding: "2px 8px", fontSize: 14, fontWeight: 700 }} type="button">
            ✕
          </button>
        </div>

        <div style={{ overflowY: "auto", padding: "20px" }}>
          <div style={{ fontSize: 14, color: "#1A1A1A", lineHeight: 1.7, marginBottom: 20, padding: "14px 16px", background: "#fff", border: "2px solid #1A1A1A" }}>
            {guardResult.summary}
          </div>

          {guardResult.recommendations.length > 0 ? (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 11, letterSpacing: 1, marginBottom: 10, textTransform: "uppercase" }}>권장 액션</div>
              {guardResult.recommendations.map((recommendation) => (
                <div key={recommendation} style={{ display: "flex", gap: 10, marginBottom: 8, padding: "10px 14px", background: "#fff", border: "2px solid #1A1A1A", fontSize: 13, lineHeight: 1.5 }}>
                  <span style={{ color: "#FF4D8B", fontWeight: 900, flexShrink: 0 }}>▸</span>
                  <span>{recommendation}</span>
                </div>
              ))}
            </div>
          ) : null}

          {guardResult.issues.length > 0 ? (
            <div>
              <div style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 11, letterSpacing: 1, marginBottom: 10, textTransform: "uppercase" }}>
                전체 이슈 ({guardResult.issues.length}개)
              </div>
              {guardResult.issues.map((issue) => (
                <div key={`${issue.found}:${issue.next_step}`} style={{ marginBottom: 8, padding: "10px 14px", background: "#fff", border: "2px solid #E8E4D8" }}>
                  <div style={{ fontSize: 12, color: "#333", marginBottom: 6, lineHeight: 1.5 }}>{issue.found}</div>
                  <div style={{ fontSize: 12, color: "#F5621E", fontWeight: 700, fontFamily: "IBM Plex Mono, monospace" }}>→ {issue.next_step}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div style={{ padding: "12px 20px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={onClose} type="button">닫기</button>
          <button className="btn btn-sm" style={{ background: "#FF4D8B" }} onClick={onClose} type="button">닫고 다시 실행</button>
        </div>
      </div>
    </div>
  );
}
