// === ANCHOR: RECOVERY_OPTIONS_CARD_START ===
import { useEffect, useState } from "react";
import { CardState } from "../../lib/commands";
import { buildGuiAiEnv, RecoveryPreviewResult, RecoveryRecommendationResponse, recoveryPreview, recoveryRecommend } from "../../lib/vib";

interface RecoveryOptionsCardProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
}

export default function RecoveryOptionsCard({ projectDir, apiKey, providerKeys }: RecoveryOptionsCardProps) {
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
      setRecommendation(await recoveryRecommend(projectDir, phrase, buildGuiAiEnv(providerKeys, apiKey)));
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
            {recommendation.fallback_reason && (
              <div style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#FF4D4D14", border: "1.5px solid #FF4D4D", color: "#7A1D1D", fontWeight: 700 }}>
                AI 추천을 붙이지 못해서 규칙 기반으로 보여줘요: {plainAiFallbackReason(recommendation.fallback_reason)}
              </div>
            )}
            {recommendation.ranked_candidates.slice(0, 3).map((candidate) => (
              <div key={candidate.candidate_id} style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#fff", border: "1.5px solid #1A1A1A" }}>
                <div style={{ fontWeight: 900 }}>#{candidate.rank} {recoveryCandidateTitle(candidate.label, candidate.source, candidate.commit_message)}</div>
                <div style={{ color: "#333", marginTop: 4 }}>{recoveryCandidateSafetySummary(candidate)}</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                  <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#4DFF9122" }}>{recoveryCandidateEvidenceLabel(candidate.evidence_score.score)}</span>
                  <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#FFD16622" }}>{candidate.llm_confidence ? `AI 의견: ${candidate.llm_confidence.level}` : "규칙 기반 추천"}</span>
                  {candidate.evidence_score.score < 0.5 && <span style={{ padding: "1px 5px", border: "1px solid #1A1A1A", background: "#FF4D4D22" }}>복원 전 미리보기 필수</span>}
                </div>
                <div style={{ color: "#555", marginTop: 4 }}>{recoveryCandidateEvidenceDetails(candidate)}</div>
              </div>
            ))}
          </div>
        )}
        {recommendState === "error" && <div style={{ marginBottom: 8, fontSize: 10, color: "#FF4D4D", fontWeight: 700 }}>복구 후보 추천을 불러오지 못했어요.</div>}
        {preview?.safeCheckpointCandidate && (
          <div style={{ fontSize: 10, lineHeight: 1.35, padding: "5px 7px", background: "#4DFF9118", border: "1.5px solid #1A1A1A", marginBottom: 8 }}>
            <div style={{ fontWeight: 900 }}>가장 안전한 복원 지점</div>
            <div>{recoveryPointSentence(preview.safeCheckpointCandidate)}</div>
            <div style={{ color: "#666", marginTop: 3 }}>기술 ID: {preview.safeCheckpointCandidate.checkpointId}</div>
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

function recoveryPointSentence(candidate: NonNullable<RecoveryPreviewResult["safeCheckpointCandidate"]>): string {
  const time = plainRecoveryTime(candidate.createdAt);
  const title = friendlyRecoveryTitle(candidate.message, candidate.trigger, candidate.gitCommitMessage);
  if (candidate.trigger === "post_commit" && candidate.gitCommitMessage?.trim()) {
    return time ? `${time}에 저장된 “${title}” 커밋 직후 상태로 되돌릴 수 있어요.` : `“${title}” 커밋 직후 상태로 되돌릴 수 있어요.`;
  }
  return time ? `${time}에 저장된 “${title}” 복원 지점으로 되돌릴 수 있어요.` : `“${title}” 복원 지점으로 되돌릴 수 있어요.`;
}

function recoveryCandidateTitle(label: string, source: string, commitMessage?: string | null): string {
  return friendlyRecoveryTitle(label, source === "post_commit_checkpoint" ? "post_commit" : null, commitMessage ?? null);
}

function recoveryCandidateSafetySummary(candidate: RecoveryRecommendationResponse["ranked_candidates"][number]): string {
  const time = plainRecoveryTime(candidate.created_at);
  const source = recoveryCandidateSourceLabel(candidate.source);
  const confidence = candidate.evidence_score.score >= 0.6 ? "비교적 안전한 후보예요" : "가능한 후보지만 확인이 더 필요해요";
  const timePart = time ? `${time}에 저장된 ` : "";
  return `${timePart}${source}라서 ${confidence}.`;
}

function recoveryCandidateEvidenceLabel(score: number): string {
  if (score >= 0.8) return "안전 근거 많음";
  if (score >= 0.6) return "안전 근거 보통";
  return "안전 근거 적음";
}

function recoveryCandidateEvidenceDetails(candidate: RecoveryRecommendationResponse["ranked_candidates"][number]): string {
  const score = candidate.evidence_score;
  const reasons = [
    score.commit_boundary ? "커밋 직후 저장" : "커밋 경계 아님",
    score.verification_fresh ? "검증 기록 있음" : "최근 검증 기록 없음",
    score.diff_small ? "변경 범위 작음" : "변경 범위 확인 필요",
    score.protected_paths_clean ? "보호 파일 문제 없음" : "보호 파일 확인 필요",
    score.time_match_user_request ? "요청한 시간대와 맞음" : "시간 단서 없음",
  ];
  return `근거: ${reasons.join(" · ")}`;
}

function recoveryCandidateSourceLabel(source: string): string {
  if (source === "post_commit_checkpoint") return "커밋 직후 자동 저장";
  if (source === "manual_checkpoint") return "직접 만든 복원 지점";
  if (source === "git_commit") return "Git 커밋 기록";
  return "복원 후보";
}

function plainAiFallbackReason(reason: string): string {
  if (reason.includes("API_KEY_INVALID") || reason.includes("API Key not found")) {
    return "Gemini API 키가 유효하지 않거나 Google AI Studio에서 삭제된 키예요. Settings에서 Gemini 키를 다시 저장해 주세요.";
  }
  if (reason.includes("HTTP 429")) return "AI 사용량 제한에 걸렸어요. 잠시 뒤 다시 시도해 주세요.";
  if (reason.includes("timeout")) return "AI 응답 시간이 초과됐어요. 잠시 뒤 다시 시도해 주세요.";
  return reason;
}

function friendlyRecoveryTitle(message: string, trigger?: string | null, gitCommitMessage?: string | null): string {
  if (trigger === "post_commit" && gitCommitMessage?.trim()) {
    return gitCommitMessage.trim().split(/\r?\n/, 1)[0] || "코드 저장";
  }
  return message.trim() || "저장된 시점";
}

function plainRecoveryTime(value: string): string {
  const normalized = value.trim();
  if (!normalized) return "";
  return normalized.replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, "");
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
