// === ANCHOR: REPORTASSISTPROVIDERS_START ===
import type { PlanningProviderId } from "../../lib/vib/planning-personas";

const aiProviderIds = ["claude", "codex", "agy", "opencode"] as const satisfies readonly PlanningProviderId[];

export type ReportAssistProviderId = "local" | PlanningProviderId;

export type ReportAssistProviderOption = {
  readonly id: ReportAssistProviderId;
  readonly label: string;
};

const providerLabels = {
  local: "로컬 보완",
  claude: "Claude Code",
  codex: "Codex",
  agy: "Antigravity",
  opencode: "OpenCode (DeepSeek)",
} satisfies Record<ReportAssistProviderId, string>;

// === ANCHOR: REPORTASSISTPROVIDERS_ISREPORTASSISTPROVIDERID_START ===
export function isReportAssistProviderId(value: string): value is ReportAssistProviderId {
  if (value === "local") return true;
  return aiProviderIds.some((id) => id === value);
}
// === ANCHOR: REPORTASSISTPROVIDERS_ISREPORTASSISTPROVIDERID_END ===

// === ANCHOR: REPORTASSISTPROVIDERS_NORMALIZEREPORTASSISTPROVIDERID_START ===
export function normalizeReportAssistProviderId(value: string): ReportAssistProviderId {
  return isReportAssistProviderId(value) ? value : "local";
}
// === ANCHOR: REPORTASSISTPROVIDERS_NORMALIZEREPORTASSISTPROVIDERID_END ===

// === ANCHOR: REPORTASSISTPROVIDERS_REPORTASSISTPROVIDERLABEL_START ===
export function reportAssistProviderLabel(providerId: ReportAssistProviderId): string {
  return providerLabels[providerId];
}
// === ANCHOR: REPORTASSISTPROVIDERS_REPORTASSISTPROVIDERLABEL_END ===

// === ANCHOR: REPORTASSISTPROVIDERS_FIRSTINSTALLEDAIPROVIDER_START ===
export function firstInstalledAiProvider(installed: readonly string[]): ReportAssistProviderId | null {
  return aiProviderIds.find((id) => installed.includes(id)) ?? null;
}
// === ANCHOR: REPORTASSISTPROVIDERS_FIRSTINSTALLEDAIPROVIDER_END ===

// === ANCHOR: REPORTASSISTPROVIDERS_REPORTASSISTPROVIDEROPTIONS_START ===
export function reportAssistProviderOptions(installed: readonly string[]): readonly ReportAssistProviderOption[] {
  const installedAiOptions = aiProviderIds
    .filter((id) => installed.includes(id))
    .map((id) => ({ id, label: providerLabels[id] }));
  return [...installedAiOptions, { id: "local", label: providerLabels.local }];
}
// === ANCHOR: REPORTASSISTPROVIDERS_REPORTASSISTPROVIDEROPTIONS_END ===
// === ANCHOR: REPORTASSISTPROVIDERS_END ===
