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
  opencode: "OpenCode",
} satisfies Record<ReportAssistProviderId, string>;

export function isReportAssistProviderId(value: string): value is ReportAssistProviderId {
  if (value === "local") return true;
  return aiProviderIds.some((id) => id === value);
}

export function normalizeReportAssistProviderId(value: string): ReportAssistProviderId {
  return isReportAssistProviderId(value) ? value : "local";
}

export function reportAssistProviderLabel(providerId: ReportAssistProviderId): string {
  return providerLabels[providerId];
}

export function firstInstalledAiProvider(installed: readonly string[]): ReportAssistProviderId | null {
  return aiProviderIds.find((id) => installed.includes(id)) ?? null;
}

export function reportAssistProviderOptions(installed: readonly string[]): readonly ReportAssistProviderOption[] {
  const installedAiOptions = aiProviderIds
    .filter((id) => installed.includes(id))
    .map((id) => ({ id, label: providerLabels[id] }));
  return [...installedAiOptions, { id: "local", label: providerLabels.local }];
}
