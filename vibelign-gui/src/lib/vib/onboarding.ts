import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type { OnboardingProgressEvent, OnboardingSnapshot } from "./types";

export async function getOnboardingSnapshot(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("get_onboarding_snapshot");
}

export async function startNativeInstall(pathKind: "native-powershell" | "native-cmd"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_native_install", { pathKind });
}

export async function startWslInstall(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_wsl_install");
}

export async function retryOnboardingVerification(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("retry_verification");
}

export async function startOnboardingLoginProbe(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("start_login_probe");
}

export async function addClaudeToUserPath(): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("add_claude_to_user_path");
}

export async function uninstallClaudeCode(track?: "all" | "native" | "wsl"): Promise<OnboardingSnapshot> {
  return invoke<OnboardingSnapshot>("uninstall_claude_code", { track: track ?? "all" });
}

export async function getOnboardingLogs(): Promise<{ text: string }> {
  return invoke<{ text: string }>("get_onboarding_logs");
}

export async function listenOnboardingProgress(
  handler: (event: OnboardingProgressEvent) => void,
): Promise<UnlistenFn> {
  return listen<OnboardingProgressEvent>("onboarding_progress", (event) => handler(event.payload));
}
