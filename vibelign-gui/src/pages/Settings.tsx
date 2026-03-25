// === ANCHOR: SETTINGS_START ===
import { useState, useEffect } from "react";
import { saveApiKey, deleteApiKey, getVibPath } from "../lib/vib";

interface SettingsProps {
  apiKey: string | null;
  onApiKeyChange: (key: string | null) => void;
}

export default function Settings({ apiKey, onApiKeyChange }: SettingsProps) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [vibPath, setVibPath] = useState<string | null>(null);

  useEffect(() => {
    getVibPath().then(setVibPath).catch(() => setVibPath(null));
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
