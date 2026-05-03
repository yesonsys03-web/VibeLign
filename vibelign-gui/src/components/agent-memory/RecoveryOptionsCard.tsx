// === ANCHOR: RECOVERY_OPTIONS_CARD_START ===
import { useEffect, useState } from "react";
import { CardState } from "../../lib/commands";
import { RecoveryPreviewResult, recoveryPreview } from "../../lib/vib";

interface RecoveryOptionsCardProps {
  projectDir: string;
}

export default function RecoveryOptionsCard({ projectDir }: RecoveryOptionsCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [preview, setPreview] = useState<RecoveryPreviewResult | null>(null);

  async function refresh() {
    setState("loading");
    try {
      setPreview(await recoveryPreview(projectDir));
      setState("done");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void refresh();
  }, [projectDir]);

  const options = preview?.options.slice(0, 3) ?? [];
  const driftCandidates = preview?.driftCandidates.slice(0, 2) ?? [];

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#FFD16622", padding: "10px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#FFD166", color: "#1A1A1A", borderColor: "#FFD166", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>↺</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>복구 옵션</div>
          <div style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>파일을 바꾸기 전, 읽기 전용 복구 계획만 보여줘요</div>
        </div>
        <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#fff", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>READ ONLY</span>
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ fontSize: 11, color: "#333", lineHeight: 1.45, marginBottom: 8 }}>
          {preview?.summary ?? "복구 계획을 불러오는 중..."}
        </div>
        {options.length > 0 && (
          <div style={{ display: "grid", gap: 5, marginBottom: 8 }}>
            {options.map((item, index) => (
              <div key={index} style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#fff", border: "1.5px solid #1A1A1A" }}>{item}</div>
            ))}
          </div>
        )}
        {preview?.safeCheckpointCandidate && (
          <div style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#4DFF9118", border: "1.5px solid #1A1A1A", marginBottom: 8 }}>
            안전 체크포인트: {preview.safeCheckpointCandidate}
          </div>
        )}
        {driftCandidates.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 9, fontWeight: 900, color: "#777", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: 4 }}>Drift candidates</div>
            {driftCandidates.map((item, index) => (
              <div key={index} style={{ fontSize: 10, lineHeight: 1.35, color: "#555" }}>• {item}</div>
            ))}
          </div>
        )}
        <button className="btn btn-sm" style={{ width: "100%", background: "#FFD166", color: "#1A1A1A", border: "2px solid #1A1A1A" }} disabled={state === "loading"} onClick={refresh}>
          {state === "loading" ? <span className="spinner" /> : "PREVIEW 다시 보기"}
        </button>
        {state === "error" && <div style={{ marginTop: 6, fontSize: 10, color: "#FF4D4D", fontWeight: 700 }}>복구 미리보기를 불러오지 못했어요.</div>}
      </div>
    </div>
  );
}
// === ANCHOR: RECOVERY_OPTIONS_CARD_END ===
