// === ANCHOR: APIKEYS_START ===
import { invoke } from "@tauri-apps/api/core";

/** GUI에 저장된 제공자 키 → `run_vib`용 환경변수 (레거시 Anthropic 단일 키 병합). */
// === ANCHOR: APIKEYS_BUILDGUIAIENV_START ===
export function buildGuiAiEnv(
  providerKeys: Record<string, string> | null | undefined,
  legacyAnthropic: string | null | undefined
): Record<string, string> | undefined {
  const map: Record<string, string> = {
    ANTHROPIC: "ANTHROPIC_API_KEY",
    OPENAI: "OPENAI_API_KEY",
    GEMINI: "GEMINI_API_KEY",
    GLM: "GLM_API_KEY",
    MOONSHOT: "MOONSHOT_API_KEY",
  };
  const env: Record<string, string> = {};
  if (providerKeys) {
    for (const [prov, envName] of Object.entries(map)) {
      const v = providerKeys[prov]?.trim();
      if (v) env[envName] = v;
    }
  }
  const leg = legacyAnthropic?.trim();
  if (leg && !env.ANTHROPIC_API_KEY) env.ANTHROPIC_API_KEY = leg;
  return Object.keys(env).length ? env : undefined;
}
// === ANCHOR: APIKEYS_BUILDGUIAIENV_END ===

// === ANCHOR: APIKEYS_SAVEAPIKEY_START ===
export async function saveApiKey(key: string): Promise<void> {
  return invoke<void>("save_api_key", { key });
}
// === ANCHOR: APIKEYS_SAVEAPIKEY_END ===

// === ANCHOR: APIKEYS_LOADAPIKEY_START ===
export async function loadApiKey(): Promise<string | null> {
  return invoke<string | null>("load_api_key");
}
// === ANCHOR: APIKEYS_LOADAPIKEY_END ===

// === ANCHOR: APIKEYS_DELETEAPIKEY_START ===
export async function deleteApiKey(): Promise<void> {
  return invoke<void>("delete_api_key");
}
// === ANCHOR: APIKEYS_DELETEAPIKEY_END ===

// === ANCHOR: APIKEYS_SAVEPROVIDERAPIKEY_START ===
export async function saveProviderApiKey(provider: string, key: string): Promise<void> {
  return invoke<void>("save_provider_api_key", { provider, key });
}
// === ANCHOR: APIKEYS_SAVEPROVIDERAPIKEY_END ===

// === ANCHOR: APIKEYS_DELETEPROVIDERAPIKEY_START ===
export async function deleteProviderApiKey(provider: string): Promise<void> {
  return invoke<void>("delete_provider_api_key", { provider });
}
// === ANCHOR: APIKEYS_DELETEPROVIDERAPIKEY_END ===

// === ANCHOR: APIKEYS_LOADPROVIDERAPIKEYS_START ===
export async function loadProviderApiKeys(): Promise<Record<string, string>> {
  return invoke<Record<string, string>>("load_provider_api_keys");
}
// === ANCHOR: APIKEYS_LOADPROVIDERAPIKEYS_END ===

// === ANCHOR: APIKEYS_GETENVKEYSTATUS_START ===
export async function getEnvKeyStatus(): Promise<Record<string, boolean>> {
  return invoke<Record<string, boolean>>("get_env_key_status");
}
// === ANCHOR: APIKEYS_GETENVKEYSTATUS_END ===
// === ANCHOR: APIKEYS_END ===
