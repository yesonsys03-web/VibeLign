// === ANCHOR: SETTINGS_START ===
import { useState, useEffect } from "react";
import { saveApiKey, deleteApiKey, getVibPath, getEnvKeyStatus } from "../lib/vib";

const PROVIDER_MODELS: Record<string, string[]> = {
  ANTHROPIC: ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
  OPENAI: ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
  GEMINI: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp-02-05"],
  GLM: ["glm-4-plus", "glm-4-flash", "glm-4-air"],
  MOONSHOT: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
};

interface SettingsProps {
  apiKey: string | null;
  onApiKeyChange: (key: string | null) => void;
  projectDir?: string | null;
  notice?: string | null;
}

export default function Settings({ apiKey, onApiKeyChange, projectDir, notice }: SettingsProps) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [vibPath, setVibPath] = useState<string | null>(null);
  const [envKeys, setEnvKeys] = useState<Record<string, boolean>>({});
  const [models, setModels] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem("vibelign_llm_models");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const handleModelChange = (provider: string, model: string) => {
    const newModels = { ...models, [provider]: model };
    setModels(newModels);
    localStorage.setItem("vibelign_llm_models", JSON.stringify(newModels));
  };

  useEffect(() => {
    getVibPath().then(setVibPath).catch(() => setVibPath(null));
    getEnvKeyStatus().then(setEnvKeys).catch(() => {});
  }, []);

  async function handleSave() {
    const key = input.trim();
    if (!key) return;
    setSaving(true);
    setMsg(null);
    try {
      await saveApiKey(key);
      onApiKeyChange(key);
      setInput("");
      setMsg({ type: "ok", text: "API 키 저장 완료." });
    } catch (e) {
      setMsg({ type: "err", text: String(e) });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    setMsg(null);
    try {
      await deleteApiKey();
      onApiKeyChange(null);
      setMsg({ type: "ok", text: "API 키 삭제 완료." });
    } catch (e) {
      setMsg({ type: "err", text: String(e) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">SETTINGS</span>
      </div>

      <div className="page-content" style={{ padding: "20px" }}>
        {notice && (
          <div
            className="alert"
            style={{
              marginBottom: 16,
              background: "#FFF4CC",
              border: "2px solid #1A1A1A",
              color: "#1A1A1A",
              fontWeight: 700,
            }}
          >
            {notice}
          </div>
        )}
        {/* CONFIG STATUS 카드 */}
        <div className="card" style={{ marginBottom: 20, background: "#1E2216", borderColor: "#333" }}>
          <div style={{ fontWeight: 700, fontSize: 11, marginBottom: 10, textTransform: "uppercase", letterSpacing: 1, color: "#7DFF6B", fontFamily: "IBM Plex Mono, monospace" }}>
            CONFIG STATUS
          </div>
          {/* 환경변수 API 키 및 모델 선택 */}
          {["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GLM_API_KEY", "MOONSHOT_API_KEY"].map((key) => {
            const ok = !!envKeys[key];
            const providerName = key.replace("_API_KEY", "");
            const availableModels = PROVIDER_MODELS[providerName] || [];
            const selectedModel = models[providerName] || "";
            return (
              <div key={key} style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 5, fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>
                <span style={{ color: ok ? "#4DFF91" : "#FF4D4D", fontWeight: 700, flexShrink: 0 }}>{ok ? "●" : "○"}</span>
                <span style={{ color: ok ? "#E8FFE0" : "#555", width: 140, flexShrink: 0 }}>{key}</span>
                <span style={{ color: ok ? "#4DFF91" : "#444", width: 40, flexShrink: 0 }}>{ok ? "설정됨" : "없음"}</span>
                {availableModels.length > 0 && (
                  <select
                    value={selectedModel}
                    onChange={(e) => handleModelChange(providerName, e.target.value)}
                    style={{
                      background: "#1A1A1A",
                      color: "#7DFF6B",
                      border: "1px solid #333",
                      borderRadius: 4,
                      padding: "2px 6px",
                      fontFamily: "inherit",
                      fontSize: 10,
                      outline: "none",
                      cursor: "pointer",
                      marginLeft: "auto"
                    }}
                  >
                    <option value="">기본 모델</option>
                    {availableModels.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                )}
              </div>
            );
          })}
          <div style={{ borderTop: "1px solid #333", margin: "10px 0" }} />
          {/* vib 경로 & 프로젝트 */}
          {[
            { label: "vib", ok: !!vibPath, value: vibPath ?? "감지 안됨" },
            { label: "project", ok: !!projectDir, value: projectDir ?? "없음" },
          ].map(({ label, ok, value }) => (
            <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 5, fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>
              <span style={{ color: ok ? "#4DFF91" : "#FF4D4D", fontWeight: 700, flexShrink: 0 }}>{ok ? "●" : "○"}</span>
              <span style={{ color: "#555", width: 180, flexShrink: 0 }}>{label}</span>
              <span style={{ color: ok ? "#E8FFE0" : "#444", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
            </div>
          ))}
        </div>

        {/* API 키 섹션 */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            Anthropic API Key
          </div>

          {/* 현재 상태 */}
          <div style={{ marginBottom: 12, fontSize: 12 }}>
            상태:{" "}
            {apiKey ? (
              <span style={{ color: "#4DFF91", fontWeight: 700 }}>
                저장됨 ({apiKey.slice(0, 8)}…)
              </span>
            ) : (
              <span style={{ color: "#FF4D4D", fontWeight: 700 }}>미설정</span>
            )}
          </div>

          {/* 입력 */}
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input
              type="password"
              placeholder="sk-ant-..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              style={{
                flex: 1,
                background: "#1E2216",
                border: "2px solid #333",
                color: "#E8FFE0",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: 12,
                padding: "6px 10px",
                outline: "none",
              }}
            />
            <button
              className="btn btn-sm"
              onClick={handleSave}
              disabled={saving || !input.trim()}
            >
              {saving ? <span className="spinner" /> : "저장"}
            </button>
          </div>

          {/* 삭제 */}
          {apiKey && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleDelete}
              disabled={saving}
              style={{ fontSize: 11, color: "#FF4D4D" }}
            >
              API 키 삭제
            </button>
          )}

          {msg && (
            <div
              className={`alert ${msg.type === "ok" ? "alert-success" : "alert-error"}`}
              style={{ marginTop: 10 }}
            >
              {msg.text}
            </div>
          )}
        </div>

        <div style={{ fontSize: 11, color: "#555", lineHeight: 1.6 }}>
          API 키는 <code style={{ color: "#888" }}>~/.vibelign/gui_config.json</code>에 저장됩니다.<br />
          <code style={{ color: "#888" }}>vib patch --ai</code>, <code style={{ color: "#888" }}>vib doctor --apply</code> 등 AI 기능에 사용됩니다.
        </div>

        {/* vib 경로 섹션 */}
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            VIB CLI 경로
          </div>
          <div style={{ fontSize: 12, marginBottom: 6 }}>
            상태:{" "}
            {vibPath ? (
              <span style={{ color: "#4DFF91", fontWeight: 700 }}>감지됨</span>
            ) : (
              <span style={{ color: "#FF4D4D", fontWeight: 700 }}>찾을 수 없음</span>
            )}
          </div>
          {vibPath ? (
            <div
              style={{
                background: "#1A1A1A",
                border: "1px solid #333",
                padding: "6px 10px",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: 11,
                color: "#7DFF6B",
                wordBreak: "break-all",
              }}
            >
              {vibPath}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: "#777", lineHeight: 1.6 }}>
              <code style={{ color: "#888" }}>pip install vibelign</code> 으로 설치 후 재시작하세요.<br />
              설치 가이드: <code style={{ color: "#888" }}>vib install</code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: SETTINGS_END ===
