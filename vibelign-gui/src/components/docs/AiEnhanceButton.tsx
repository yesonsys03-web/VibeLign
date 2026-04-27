import { useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { enhanceDocWithAi } from "../../lib/vib";

const API_KEY_URL = "https://aistudio.google.com/app/apikey";

function renderErrorMessage(message: string) {
  const parts = message.split(API_KEY_URL);
  return parts.map((part, index) => (
    <span key={index}>
      {part}
      {index < parts.length - 1 ? (
        <button
          type="button"
          onClick={() => openUrl(API_KEY_URL).catch(() => {})}
          style={{
            background: "transparent",
            border: "none",
            color: "#265CFF",
            cursor: "pointer",
            font: "inherit",
            fontWeight: 800,
            padding: 0,
            textDecoration: "underline",
          }}
        >
          {API_KEY_URL}
        </button>
      ) : null}
    </span>
  ));
}

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <button
        className="card"
        onClick={() => void proceed()}
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
        <div style={{ fontSize: 11, color: "#A33A3A", whiteSpace: "pre-wrap" }}>
          {renderErrorMessage(error)}
        </div>
      ) : null}
      {isAiActive && typeof lastCostUsd === "number" ? (
        <div style={{ fontSize: 10, color: "#777" }}>
          last AI: in={lastTokensInput ?? 0} out={lastTokensOutput ?? 0} · ${lastCostUsd.toFixed(4)}
        </div>
      ) : null}
    </div>
  );
}
