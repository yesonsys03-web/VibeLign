// === ANCHOR: SETTINGS_START ===
import { useState, useEffect, useMemo } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { saveProviderApiKey, deleteProviderApiKey, getVibPath, getEnvKeyStatus, getAiEnhancement, setAiEnhancement, getAutoBackupOnCommit, setAutoBackupOnCommit } from "../lib/vib";

const PROVIDER_MODELS: Record<string, string[]> = {
  ANTHROPIC: ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
  OPENAI: ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
  GEMINI: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp-02-05"],
  GLM: ["glm-4-plus", "glm-4-flash", "glm-4-air"],
  MOONSHOT: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
};

const GUI_KEY_PROVIDERS: { id: string; label: string; placeholder: string; apiKeyUrl: string; costNote: string }[] = [
  { id: "ANTHROPIC", label: "Anthropic", placeholder: "sk-ant-...", apiKeyUrl: "https://console.anthropic.com/settings/keys", costNote: "유료 API 키가 필요해요." },
  { id: "OPENAI", label: "OpenAI", placeholder: "sk-...", apiKeyUrl: "https://platform.openai.com/settings/organization/api-keys", costNote: "유료 API 키가 필요해요." },
  { id: "GEMINI", label: "Google Gemini", placeholder: "API 키 문자열", apiKeyUrl: "https://aistudio.google.com/app/apikey", costNote: "무료로 시작 가능한 키를 받을 수 있어요." },
  { id: "GLM", label: "GLM", placeholder: "...", apiKeyUrl: "https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys", costNote: "유료 API 키가 필요할 수 있어요." },
  { id: "MOONSHOT", label: "Moonshot", placeholder: "...", apiKeyUrl: "https://platform.moonshot.ai/console/api-keys", costNote: "유료 API 키가 필요할 수 있어요." },
];

interface SettingsProps {
  apiKey: string | null;
  onApiKeyChange: (key: string | null) => void;
  providerKeys: Record<string, string>;
  onKeysUpdated: () => void | Promise<void>;
  projectDir?: string | null;
  notice?: string | null;
}

export default function Settings({ apiKey, onApiKeyChange, providerKeys, onKeysUpdated, projectDir, notice }: SettingsProps) {
  const [inputs, setInputs] = useState<Record<string, string>>({});
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
  const [aiEnhancement, setAiEnhancementState] = useState<boolean | null>(null);
  const [aiEnhancementSaving, setAiEnhancementSaving] = useState(false);
  const [autoBackupOnCommit, setAutoBackupOnCommitState] = useState<boolean | null>(null);
  const [autoBackupSaving, setAutoBackupSaving] = useState(false);

  const handleModelChange = (provider: string, model: string) => {
    const newModels = { ...models, [provider]: model };
    setModels(newModels);
    localStorage.setItem("vibelign_llm_models", JSON.stringify(newModels));
  };

  useEffect(() => {
    getVibPath().then(setVibPath).catch(() => setVibPath(null));
    getEnvKeyStatus().then(setEnvKeys).catch(() => {});
  }, []);

  useEffect(() => {
    if (!projectDir) {
      setAiEnhancementState(null);
      setAutoBackupOnCommitState(null);
      return;
    }
    getAiEnhancement(projectDir)
      .then(setAiEnhancementState)
      .catch(() => setAiEnhancementState(null));
    getAutoBackupOnCommit(projectDir)
      .then(setAutoBackupOnCommitState)
      .catch(() => setAutoBackupOnCommitState(null));
  }, [projectDir]);

  async function handleToggleAiEnhancement(next: boolean) {
    if (!projectDir) return;
    setAiEnhancementSaving(true);
    try {
      const applied = await setAiEnhancement(projectDir, next);
      setAiEnhancementState(applied);
    } catch (e) {
      setMsg({ type: "err", text: `AI 보강 설정 실패: ${e}` });
    } finally {
      setAiEnhancementSaving(false);
    }
  }

  async function handleToggleAutoBackup(next: boolean) {
    if (!projectDir) return;
    setAutoBackupSaving(true);
    try {
      const applied = await setAutoBackupOnCommit(projectDir, next);
      setAutoBackupOnCommitState(applied);
      setMsg({ type: "ok", text: applied ? "커밋 후 자동 백업을 켰어요." : "커밋 후 자동 백업을 껐어요." });
    } catch (e) {
      setMsg({ type: "err", text: `자동 백업 설정 실패: ${e}` });
    } finally {
      setAutoBackupSaving(false);
    }
  }

  function savedKey(provider: string): string {
    const v = providerKeys[provider]?.trim();
    if (v) return v;
    if (provider === "ANTHROPIC" && apiKey) return apiKey;
    return "";
  }

  /** CONFIG STATUS와 동일한 환경변수 키명 (예: GEMINI → GEMINI_API_KEY). */
  function envKeyNameForProvider(providerId: string): string {
    return `${providerId}_API_KEY`;
  }

  function hasEnvProviderKey(providerId: string): boolean {
    return Boolean(envKeys[envKeyNameForProvider(providerId)]);
  }

  const configuredSecretRows = useMemo(() => {
    return GUI_KEY_PROVIDERS.flatMap((p) => {
      const sk = savedKey(p.id);
      const env = hasEnvProviderKey(p.id);
      if (!sk && !env) return [];
      const sources: string[] = [];
      if (env) sources.push("환경 변수");
      if (sk) sources.push("GUI 저장");
      return [
        {
          id: p.id,
          label: p.label,
          envKey: envKeyNameForProvider(p.id),
          sources,
          stored: Boolean(sk),
        },
      ];
    });
  }, [providerKeys, apiKey, envKeys]);

  async function handleSaveProvider(provider: string) {
    const key = (inputs[provider] ?? "").trim();
    if (!key) return;
    setSaving(true);
    setMsg(null);
    try {
      await saveProviderApiKey(provider, key);
      setInputs((prev) => ({ ...prev, [provider]: "" }));
      if (provider === "ANTHROPIC") onApiKeyChange(key);
      await onKeysUpdated();
      setMsg({ type: "ok", text: `${provider} API 키를 저장했어요.` });
    } catch (e) {
      setMsg({ type: "err", text: String(e) });
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteProvider(provider: string) {
    setSaving(true);
    setMsg(null);
    try {
      await deleteProviderApiKey(provider);
      if (provider === "ANTHROPIC") onApiKeyChange(null);
      await onKeysUpdated();
      setMsg({ type: "ok", text: `${provider} API 키를 삭제했어요.` });
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
            const providerName = key.replace("_API_KEY", "");
            const envOk = !!envKeys[key];
            const guiOk = Boolean(savedKey(providerName));
            const ok = envOk || guiOk;
            const availableModels = PROVIDER_MODELS[providerName] || [];
            const selectedModel = models[providerName] || "";
            const sources: string[] = [];
            if (envOk) sources.push("환경 변수");
            if (guiOk) sources.push("GUI 저장");
            const statusText = guiOk
              ? `설정됨 (${sources.join(" · ")})`
              : envOk
                ? "외부 환경 변수에서 감지됨"
                : "없음";
            return (
              <div key={key} style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 5, fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>
                <span style={{ color: ok ? "#4DFF91" : "#FF4D4D", fontWeight: 700, flexShrink: 0 }}>{ok ? "●" : "○"}</span>
                <span style={{ color: ok ? "#E8FFE0" : "#555", width: 140, flexShrink: 0 }}>{key}</span>
                <span style={{ color: ok ? "#4DFF91" : "#444", flexShrink: 0 }}>{statusText}</span>
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

        {/* 설정된 API 키 요약 — 전체 값은 표시하지 않음 */}
        <div className="card" style={{ marginBottom: 20, background: "#1E2216", borderColor: "#333" }}>
          <div style={{ fontWeight: 700, fontSize: 11, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1, color: "#7DFF6B", fontFamily: "IBM Plex Mono, monospace" }}>
            AI KEY SOURCES (감지됨)
          </div>
          <div style={{ fontSize: 10, color: "#666", marginBottom: 10, lineHeight: 1.5 }}>
            GUI 저장 키와 앱 실행 환경 변수를 구분해서 보여줘요. 환경 변수는 Settings에서 삭제할 수 없고, 터미널/시스템 환경 설정에서 지워야 합니다.
          </div>
          {configuredSecretRows.length === 0 ? (
            <div style={{ fontSize: 11, color: "#777", fontFamily: "IBM Plex Mono, monospace" }}>
              설정된 항목이 없습니다. 아래에서 저장하거나 터미널 환경 변수를 설정하세요.
            </div>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {configuredSecretRows.map((row, idx) => (
                <li
                  key={row.id}
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "baseline",
                    gap: 8,
                    marginBottom: 8,
                    paddingBottom: 8,
                    borderBottom: idx < configuredSecretRows.length - 1 ? "1px solid #2a2a2a" : "none",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: 11,
                  }}
                >
                  <span style={{ color: "#4DFF91", fontWeight: 700, flexShrink: 0 }}>●</span>
                  <span style={{ color: "#E8FFE0", minWidth: 120, flexShrink: 0 }}>{row.label}</span>
                  <span style={{ color: "#888", flexShrink: 0 }}>{row.envKey}</span>
                  <span style={{ color: "#7DFF6B", flexShrink: 0 }}>{row.sources.join(" · ")}</span>
                  {row.stored && (
                    <span style={{ color: "#AAA", marginLeft: "auto" }} title="키 값은 화면에 표시하지 않습니다">
                      값 숨김
                    </span>
                  )}
                  {!row.stored && row.sources.includes("환경 변수") && (
                    <span style={{ color: "#AAA", marginLeft: "auto" }} title="Settings 저장소가 아니라 앱 실행 환경에서 들어온 키입니다">
                      외부 환경에서 감지됨
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* API 키 섹션 (제공자별) */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            API 키 (제공자별)
          </div>
          <div style={{ fontSize: 11, color: "#777", lineHeight: 1.6, marginBottom: 14 }}>
            API 키는 AI 회사에서 발급받는 이용권이에요. 대부분은 사용량에 따라 비용이 나올 수 있고,
            Google Gemini는 무료로 시작 가능한 키를 받을 수 있어요.
          </div>
          {GUI_KEY_PROVIDERS.map((p, idx) => {
            const sk = savedKey(p.id);
            const envOnly = !sk && hasEnvProviderKey(p.id);
            return (
              <div
                key={p.id}
                style={{
                  marginBottom: 18,
                  paddingBottom: 16,
                  borderBottom: idx < GUI_KEY_PROVIDERS.length - 1 ? "1px solid #2a2a2a" : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div style={{ fontWeight: 700, fontSize: 11, color: "#7DFF6B" }}>{p.label}</div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => openUrl(p.apiKeyUrl).catch(() => {})}
                    style={{ fontSize: 10, padding: "3px 8px" }}
                    title={`${p.label} API 키 발급 페이지 열기`}
                  >
                    키 받기 ↗
                  </button>
                </div>
                <div style={{ marginBottom: 8, fontSize: 11, color: p.id === "GEMINI" ? "#4D7CFF" : "#777", fontWeight: p.id === "GEMINI" ? 700 : 500 }}>
                  {p.costNote}
                </div>
                <div style={{ marginBottom: 8, fontSize: 12 }}>
                  상태:{" "}
                  {sk ? (
                    <span style={{ color: "#4DFF91", fontWeight: 700 }}>저장됨 (값 숨김)</span>
                  ) : envOnly ? (
                    <span style={{ color: "#4DFF91", fontWeight: 700 }}>외부 환경 변수에서 감지됨</span>
                  ) : (
                    <span style={{ color: "#FF4D4D", fontWeight: 700 }}>미설정</span>
                  )}
                </div>
                {envOnly && (
                  <div style={{ marginBottom: 8, fontSize: 10, color: "#888", lineHeight: 1.45 }}>
                    이 키는 GUI 저장소에 없어서 여기서 삭제할 수 없어요. 터미널 환경 변수나 시스템 환경 설정의 {envKeyNameForProvider(p.id)} 값을 제거해야 합니다.
                  </div>
                )}
                <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <input
                    type="password"
                    placeholder={p.placeholder}
                    value={inputs[p.id] ?? ""}
                    onChange={(e) => setInputs((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveProvider(p.id)}
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
                    onClick={() => handleSaveProvider(p.id)}
                    disabled={saving || !(inputs[p.id] ?? "").trim()}
                  >
                    {saving ? <span className="spinner" /> : "저장"}
                  </button>
                </div>
                {sk && (
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleDeleteProvider(p.id)}
                    disabled={saving}
                    style={{ fontSize: 11, color: "#FF4D4D" }}
                  >
                    {p.label} 키 삭제
                  </button>
                )}
              </div>
            );
          })}
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
          키는 사용자 설정 폴더의 <code style={{ color: "#888" }}>api_keys.json</code>에 저장됩니다. 레포에는 커밋하지 마세요.<br />
          <code style={{ color: "#888" }}>vib patch --ai</code>, <code style={{ color: "#888" }}>vib doctor --apply</code> 실행 시 GUI에 저장된 키가 해당 환경변수로 전달됩니다.
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

        {/* 커밋 후 자동 백업 토글 섹션 */}
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            커밋 후 자동 백업
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 10 }}>
            Git commit 이 끝날 때마다 VibeLign checkpoint를 자동으로 남깁니다. 복구 안전성을 높이려면 ON,
            저장본 증가를 줄이고 필요할 때만 <code style={{ color: "#888" }}>vib checkpoint</code>를 쓰려면 OFF로 두세요.
          </div>
          {!projectDir ? (
            <div style={{ fontSize: 11, color: "#777" }}>프로젝트를 먼저 선택하세요.</div>
          ) : autoBackupOnCommit === null ? (
            <div style={{ fontSize: 11, color: "#777" }}>상태 불러오는 중…</div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button
                className="btn btn-sm"
                disabled={autoBackupSaving}
                onClick={() => handleToggleAutoBackup(!autoBackupOnCommit)}
                style={{
                  background: autoBackupOnCommit ? "#4DFF91" : "#1A1A1A",
                  color: autoBackupOnCommit ? "#1A1A1A" : "#888",
                  border: "2px solid #1A1A1A",
                  fontWeight: 700,
                }}
              >
                {autoBackupSaving ? <span className="spinner" /> : autoBackupOnCommit ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 11, color: "#888", fontFamily: "IBM Plex Mono, monospace" }}>
                auto_backup_on_commit: {autoBackupOnCommit ? "true" : "false"}
              </span>
            </div>
          )}
        </div>

        {/* AI 앵커 보강 토글 섹션 */}
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            AI 앵커 intent 자동 보강
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 10 }}>
            <code style={{ color: "#888" }}>vib anchor --auto-intent</code> 및 Doctor apply 실행 시
            앵커 <b>20개 단위로 배치 묶어</b> AI에 호출합니다 (배치 4개 병렬). 내용이 안 바뀐 앵커는
            해시 캐시로 자동 건너뜁니다. 그래도 코드 많거나 첫 실행일 땐 수십 초 걸릴 수 있어
            기본은 OFF (코드 기반 aliases 만 생성). ON 이면 프로젝트 전역에서 자동 수행됩니다.
          </div>
          {!projectDir ? (
            <div style={{ fontSize: 11, color: "#777" }}>프로젝트를 먼저 선택하세요.</div>
          ) : aiEnhancement === null ? (
            <div style={{ fontSize: 11, color: "#777" }}>상태 불러오는 중…</div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button
                className="btn btn-sm"
                disabled={aiEnhancementSaving}
                onClick={() => handleToggleAiEnhancement(!aiEnhancement)}
                style={{
                  background: aiEnhancement ? "#4DFF91" : "#1A1A1A",
                  color: aiEnhancement ? "#1A1A1A" : "#888",
                  border: "2px solid #1A1A1A",
                  fontWeight: 700,
                }}
              >
                {aiEnhancementSaving ? <span className="spinner" /> : aiEnhancement ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 11, color: "#888", fontFamily: "IBM Plex Mono, monospace" }}>
                ai_enhancement: {aiEnhancement ? "true" : "false"}
              </span>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
// === ANCHOR: SETTINGS_END ===
