// === ANCHOR: INSTALLERREGISTRY_START ===
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

// === ANCHOR: INSTALLERREGISTRY_GETINSTALLER_START ===
export function getInstaller(id: string): ToolInstallerMeta | undefined {
  return TOOL_INSTALLERS.find((t) => t.id === id);
}
// === ANCHOR: INSTALLERREGISTRY_GETINSTALLER_END ===

export interface ToolInstallResult {
  installed: boolean;
  exitCode: number | null;
  // 백엔드(install_tool)가 항상 채워 보낸다 — 옵셔널 아님(리뷰 정합).
  auth: AuthKind;
  authHint: string;
  manualUrl: string;
}

/** 자동설치가 실패했거나(installed=false) 미지원(exitCode=null)이면 수동 가이드로. */
// === ANCHOR: INSTALLERREGISTRY_SHOULDGUIDEMANUAL_START ===
export function shouldGuideManual(r: { installed: boolean; exitCode: number | null }): boolean {
  return !r.installed;
}
// === ANCHOR: INSTALLERREGISTRY_SHOULDGUIDEMANUAL_END ===

// === ANCHOR: INSTALLERREGISTRY_INSTALLTOOL_START ===
export function installTool(id: string): Promise<ToolInstallResult> {
  return invoke<ToolInstallResult>("install_tool", { id });
}
// === ANCHOR: INSTALLERREGISTRY_INSTALLTOOL_END ===
// === ANCHOR: INSTALLERREGISTRY_TOOLINSTALLSTATUS_START ===
export function toolInstallStatus(id: string): Promise<boolean> {
  return invoke<boolean>("tool_install_status", { id });
}
// === ANCHOR: INSTALLERREGISTRY_TOOLINSTALLSTATUS_END ===

export interface ToolUninstallResult {
  removed: boolean;
  exitCode: number | null;
  manualHint: string;
  manualUrl: string;
}

// === ANCHOR: INSTALLERREGISTRY_UNINSTALLTOOL_START ===
export function uninstallTool(id: string): Promise<ToolUninstallResult> {
  return invoke<ToolUninstallResult>("uninstall_tool", { id });
}
// === ANCHOR: INSTALLERREGISTRY_UNINSTALLTOOL_END ===

/** 제거가 실패했거나 명령이 없으면(removed=false) 수동 안내로. */
// === ANCHOR: INSTALLERREGISTRY_SHOULDGUIDEMANUALUNINSTALL_START ===
export function shouldGuideManualUninstall(r: { removed: boolean }): boolean {
  return !r.removed;
}
// === ANCHOR: INSTALLERREGISTRY_SHOULDGUIDEMANUALUNINSTALL_END ===
// === ANCHOR: INSTALLERREGISTRY_END ===
