// === ANCHOR: RECOVERY_OPTIONS_CARD_START ===
import { useEffect, useState } from "react";
import { CardState } from "../../lib/commands";
import { RecoveryPreviewResult, RecoveryRecommendationResponse, recoveryPreview, recoveryRecommend } from "../../lib/vib";

interface RecoveryOptionsCardProps {
  projectDir: string;
}

export default function RecoveryOptionsCard({ projectDir }: RecoveryOptionsCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [preview, setPreview] = useState<RecoveryPreviewResult | null>(null);
  const [phrase, setPhrase] = useState("");
  const [recommendation, setRecommendation] = useState<RecoveryRecommendationResponse | null>(null);
  const [recommendState, setRecommendState] = useState<CardState>("idle");

  async function refresh() {
    setState("loading");
    try {
      setPreview(await recoveryPreview(projectDir));
      setState("done");
    } catch {
      setState("error");
    }
  }

  async function suggest() {
    setRecommendState("loading");
    try {
      setRecommendation(await recoveryRecommend(projectDir, phrase));
      setRecommendState("done");
    } catch {
      setRecommendState("error");
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
        <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#fff", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>미리보기 전용</span>
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
        <div style={{ display: "grid", gap: 5, marginBottom: 8 }}>
          <input
            value={phrase}
            onChange={(event) => setPhrase(event.target.value)}
            placeholder="예: GUI broke 30m ago"
            style={{ fontSize: 10, padding: "5px 7px", border: "1.5px solid #1A1A1A" }}
          />
          <button className="btn btn-sm" style={{ width: "100%" }} disabled={recommendState === "loading"} onClick={suggest}>
            {recommendState === "loading" ? <span className="spinner" /> : "복구 후보 추천 보기"}
          </button>
        </div>
        {recommendation && recommendation.ranked_candidates.length > 0 && (
          <div style={{ display: "grid", gap: 5, marginBottom: 8 }}>
            {recommendation.ranked_candidates.slice(0, 3).map((candidate) => (
              <div key={candidate.candidate_id} style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#fff", border: "1.5px solid #1A1A1A" }}>
                <div style={{ fontWeight: 900 }}>#{candidate.rank} {candidate.label}</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                  <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#4DFF9122" }}>System: {(candidate.evidence_score.score * 100).toFixed(0)}%</span>
                  <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#FFD16622" }}>{candidate.llm_confidence ? `AI opinion: ${candidate.llm_confidence.level}` : "AI off"}</span>
                  {candidate.llm_confidence?.level === "high" && candidate.evidence_score.score < 0.5 && <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#FF4D4D22" }}>Evidence weak — review carefully</span>}
                </div>
                <div style={{ color: "#555", marginTop: 4 }}>{candidate.reason}</div>
              </div>
            ))}
          </div>
        )}
        {recommendState === "error" && <div style={{ marginBottom: 8, fontSize: 10, color: "#FF4D4D", fontWeight: 700 }}>복구 후보 추천을 불러오지 못했어요.</div>}
        {preview?.safeCheckpointCandidate && (
          <div style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#4DFF9118", border: "1.5px solid #1A1A1A", marginBottom: 8 }}>
            안전 체크포인트: {preview.safeCheckpointCandidate}
          </div>
        )}
        {driftCandidates.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 9, fontWeight: 900, color: "#777", letterSpacing: 0.8, marginBottom: 4 }}>검토가 필요한 파일</div>
            {driftCandidates.map((item, index) => (
              <div key={index} style={{ fontSize: 10, lineHeight: 1.35, color: "#555" }}>• {plainRecoveryFile(item)}</div>
            ))}
          </div>
        )}
        <button className="btn btn-sm" style={{ width: "100%", background: "#FFD166", color: "#1A1A1A", border: "2px solid #1A1A1A" }} disabled={state === "loading"} onClick={refresh}>
          {state === "loading" ? <span className="spinner" /> : "미리보기 다시 보기"}
        </button>
        {state === "error" && <div style={{ marginTop: 6, fontSize: 10, color: "#FF4D4D", fontWeight: 700 }}>복구 미리보기를 불러오지 못했어요.</div>}
      </div>
    </div>
  );
}

function plainRecoveryFile(value: string): string {
  const [path] = value.split(" — ");
  return `${path}: ${recoveryFileRole(path)}`;
}

function recoveryFileRole(path: string): string {
  const normalized = path.replace(/\\/g, "/").toLowerCase();
  const name = normalized.split("/").pop() ?? normalized;
  if (normalized.startsWith("docs/") || normalized.includes("/docs/") || /\.(md|mdx|rst)$/.test(name)) {
    return "작업 계획이나 기능 설명 문서예요.";
  }
  if (normalized.startsWith("tests/") || normalized.includes("/tests/") || name.startsWith("test_")) {
    return "기능이 맞는지 확인하는 테스트예요.";
  }
  if (normalized.includes("recovery") || normalized.includes("recover")) {
    return "되돌리기와 복구 안내 기능이에요.";
  }
  if (normalized.includes("memory")) {
    return "세션 메모리와 작업 기록 기능이에요.";
  }
  if (normalized.startsWith("vibelign-gui/") || /\.(tsx|jsx|css)$/.test(name)) {
    return "사용자 화면에 보이는 기능이에요.";
  }
  if (normalized.startsWith("vibelign/commands/") || normalized.startsWith("vibelign/cli/")) {
    return "vib 명령을 처리하는 기능이에요.";
  }
  if (name === "pyproject.toml" || name === "vib.spec") {
    return "설치와 빌드 설정이에요.";
  }
  if (normalized.startsWith("vibelign/core/") || normalized.startsWith("src/")) {
    return "제품의 핵심 동작 로직이에요.";
  }
  return "프로젝트 보조 파일이에요.";
}
// === ANCHOR: RECOVERY_OPTIONS_CARD_END ===
