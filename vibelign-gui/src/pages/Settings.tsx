// === ANCHOR: SETTINGS_START ===
import { useState } from "react";
import { saveApiKey, deleteApiKey } from "../lib/vib";

interface SettingsProps {
  apiKey: string | null;
  onApiKeyChange: (key: string | null) => void;
}

export default function Settings({ apiKey, onApiKeyChange }: SettingsProps) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

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
      </div>
    </div>
  );
}
// === ANCHOR: SETTINGS_END ===
