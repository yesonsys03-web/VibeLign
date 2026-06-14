import { invoke } from "@tauri-apps/api/core";

export type AuthKind = "none" | "login";

export interface ToolInstallerMeta {
  readonly id: "opencode" | "codex" | "agy";
  readonly displayName: string;
  readonly auth: AuthKind;
  readonly recommendedForBeginner: boolean;
}

export const TOOL_INSTALLERS: readonly ToolInstallerMeta[] = [
  { id: "opencode", displayName: "OpenCode (무료)", auth: "none", recommendedForBeginner: true },
  { id: "codex", displayName: "Codex", auth: "login", recommendedForBeginner: false },
  { id: "agy", displayName: "Antigravity", auth: "login", recommendedForBeginner: false },
];

export function getInstaller(id: string): ToolInstallerMeta | undefined {
  return TOOL_INSTALLERS.find((t) => t.id === id);
}

export interface ToolInstallResult {
  installed: boolean;
  exitCode: number | null;
  // 백엔드(install_tool)가 항상 채워 보낸다 — 옵셔널 아님(리뷰 정합).
  auth: AuthKind;
  authHint: string;
  manualUrl: string;
}

/** 자동설치가 실패했거나(installed=false) 미지원(exitCode=null)이면 수동 가이드로. */
export function shouldGuideManual(r: { installed: boolean; exitCode: number | null }): boolean {
  return !r.installed;
}

export function installTool(id: string): Promise<ToolInstallResult> {
  return invoke<ToolInstallResult>("install_tool", { id });
}
export function toolInstallStatus(id: string): Promise<boolean> {
  return invoke<boolean>("tool_install_status", { id });
}
