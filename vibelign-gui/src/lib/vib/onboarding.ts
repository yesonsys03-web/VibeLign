// === ANCHOR: ONBOARDING_START ===
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type { OnboardingProgressEvent, OnboardingSnapshot } from "./types";

// === ANCHOR: ONBOARDING_GETONBOARDINGSNAPSHOT_START ===
export async function getOnboardingSnapshot(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("get_onboarding_snapshot");
}
// === ANCHOR: ONBOARDING_GETONBOARDINGSNAPSHOT_END ===

// === ANCHOR: ONBOARDING_STARTNATIVEINSTALL_START ===
export async function startNativeInstall(pathKind: "native-powershell" | "native-cmd"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_native_install", { pathKind });
}
// === ANCHOR: ONBOARDING_STARTNATIVEINSTALL_END ===

// === ANCHOR: ONBOARDING_STARTWSLINSTALL_START ===
export async function startWslInstall(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_wsl_install");
}
// === ANCHOR: ONBOARDING_STARTWSLINSTALL_END ===

// === ANCHOR: ONBOARDING_RETRYONBOARDINGVERIFICATION_START ===
export async function retryOnboardingVerification(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("retry_verification");
}
// === ANCHOR: ONBOARDING_RETRYONBOARDINGVERIFICATION_END ===

// === ANCHOR: ONBOARDING_STARTONBOARDINGLOGINPROBE_START ===
export async function startOnboardingLoginProbe(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_login_probe");
}
// === ANCHOR: ONBOARDING_STARTONBOARDINGLOGINPROBE_END ===

// === ANCHOR: ONBOARDING_ADDCLAUDETOUSERPATH_START ===
export async function addClaudeToUserPath(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("add_claude_to_user_path");
}
// === ANCHOR: ONBOARDING_ADDCLAUDETOUSERPATH_END ===

// === ANCHOR: ONBOARDING_UNINSTALLCLAUDECODE_START ===
export async function uninstallClaudeCode(track?: "all" | "native" | "wsl"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("uninstall_claude_code", { track: track ?? "all" });
}
// === ANCHOR: ONBOARDING_UNINSTALLCLAUDECODE_END ===

// === ANCHOR: ONBOARDING_GETONBOARDINGLOGS_START ===
export async function getOnboardingLogs(): Promise<{ text: string }> {
  return invoke<{ text: string }>("get_onboarding_logs");
}
// === ANCHOR: ONBOARDING_GETONBOARDINGLOGS_END ===

// === ANCHOR: ONBOARDING_LISTENONBOARDINGPROGRESS_START ===
export async function listenOnboardingProgress(
  handler: (event: OnboardingProgressEvent) => void,
): Promise<UnlistenFn> {
  return listen<OnboardingProgressEvent>("onboarding_progress", (event) => handler(event.payload));
}
// === ANCHOR: ONBOARDING_LISTENONBOARDINGPROGRESS_END ===

// === ANCHOR: ONBOARDING_DETECTINSTALLEDTOOLS_START ===
export async function detectInstalledTools(): Promise<string[]> {
  return invoke<string[]>("detect_installed_tools");
}
// === ANCHOR: ONBOARDING_DETECTINSTALLEDTOOLS_END ===
// === ANCHOR: ONBOARDING_END ===
