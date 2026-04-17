import { useState } from "react";
import { enhanceDocWithAi } from "../../lib/vib";

const CONSENT_KEY = "vibelign.docs.ai.consent";

export interface AiEnhanceButtonProps {
  root: string;
  relativePath: string;
  onDone: () => void;
  sourceHash: string;
  isAiActive: boolean;
  lastTokensInput?: number;
  lastTokensOutput?: number;
  lastCostUsd?: number;
}

export default function AiEnhanceButton({
  root,
  relativePath,
  onDone,
  isAiActive,
  lastTokensInput,
  lastTokensOutput,
  lastCostUsd,
}: AiEnhanceButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(false);

  const proceed = async () => {
    setBusy(true);
    setError(null);
    try {
      let models: Record<string, string> | undefined;
      try {
        const raw = localStorage.getItem("vibelign_llm_models");
        if (raw) models = JSON.parse(raw) as Record<string, string>;
      } catch {
        models = undefined;
      }
      await enhanceDocWithAi(root, relativePath, models);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleClick = () => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (consent === "accepted") {
      void proceed();
      return;
    }
    setShowConsent(true);
  };

  const handleAccept = (remember: boolean) => {
    if (remember) localStorage.setItem(CONSENT_KEY, "accepted");
    setShowConsent(false);
    void proceed();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <button
        className="card"
        onClick={handleClick}
        disabled={busy}
        style={{
          padding: "8px 14px",
          background: isAiActive ? "#FFF0F0" : "#E8F5FF",
          fontWeight: 800,
          fontSize: 12,
          cursor: busy ? "wait" : "pointer",
        }}
      >
        {busy ? "AI 요약 생성 중..." : isAiActive ? "AI 요약 새로 생성" : "AI 로 요약하기"}
      </button>
      {error ? (
        <div style={{ fontSize: 11, color: "#A33A3A" }}>{error}</div>
      ) : null}
      {isAiActive && typeof lastCostUsd === "number" ? (
        <div style={{ fontSize: 10, color: "#777" }}>
          last AI: in={lastTokensInput ?? 0} out={lastTokensOutput ?? 0} · ${lastCostUsd.toFixed(4)}
        </div>
      ) : null}
      {showConsent ? (
        <div
          role="dialog"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <div
            className="card"
            style={{ padding: 24, maxWidth: 420, background: "#FBF8EE" }}
          >
            <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 12 }}>
              AI 요약을 사용하시겠어요?
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 16 }}>
              이 문서 내용이 Anthropic API (외부) 로 전송됩니다. 민감한 문서는
              진행 전에 한 번 더 확인해주세요.
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowConsent(false)} style={{ padding: "6px 12px" }}>
                취소
              </button>
              <button onClick={() => handleAccept(false)} style={{ padding: "6px 12px" }}>
                이번만 진행
              </button>
              <button
                onClick={() => handleAccept(true)}
                style={{ padding: "6px 12px", background: "#4D9FFF", color: "#fff" }}
              >
                항상 허용
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
